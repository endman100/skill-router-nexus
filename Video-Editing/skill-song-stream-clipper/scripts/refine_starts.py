from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from pipeline_utils import read_csv, seconds_to_timestamp, write_csv


@dataclass(frozen=True)
class Span:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def music_runs(
    rows: Iterable[dict[str, str]],
    search: Span,
    threshold: float,
    max_gap_seconds: float,
    min_run_seconds: float,
) -> list[Span]:
    active = [
        Span(
            max(search.start, float(row["second_start"])),
            min(search.end, float(row["second_end"])),
        )
        for row in rows
        if str(row.get("avg_music_probability", "")).strip()
        and float(row["avg_music_probability"]) >= threshold
        and float(row["second_start"]) < search.end
        and float(row["second_end"]) > search.start
    ]
    merged: list[Span] = []
    for span in sorted(active, key=lambda item: item.start):
        if not merged or span.start - merged[-1].end > max_gap_seconds:
            merged.append(span)
        else:
            merged[-1] = Span(merged[-1].start, max(merged[-1].end, span.end))
    return [span for span in merged if span.duration >= min_run_seconds]


def choose_lyric_music_run(
    runs: list[Span],
    first_lyric: float,
    tolerance_seconds: float,
) -> Span | None:
    eligible = [
        run
        for run in runs
        if run.start < first_lyric and run.end >= first_lyric - tolerance_seconds
    ]
    if not eligible:
        return None

    def distance(run: Span) -> float:
        return 0.0 if run.start <= first_lyric <= run.end else first_lyric - run.end

    return min(eligible, key=lambda run: (distance(run), -run.duration, -run.end))


def merged_asr_spans(
    phrase_rows: Iterable[dict[str, str]],
    padding_seconds: float,
    duration_seconds: float,
) -> list[Span]:
    spans = sorted(
        (
            Span(
                max(0.0, float(row["start_seconds"]) - padding_seconds),
                min(duration_seconds, float(row["end_seconds"]) + padding_seconds),
            )
            for row in phrase_rows
        ),
        key=lambda span: (span.start, span.end),
    )
    merged: list[Span] = []
    for span in spans:
        if not merged or span.start > merged[-1].end:
            merged.append(span)
        else:
            merged[-1] = Span(merged[-1].start, max(merged[-1].end, span.end))
    return merged


def asr_gap_anchor(
    occupied_spans: Iterable[Span],
    music_onset: float,
    search_start: float,
    lookback_seconds: float,
) -> tuple[float, Span | None, float | None]:
    spans = list(occupied_spans)
    nearby = [
        span
        for span in spans
        if span.start < music_onset
        and span.end > max(search_start, music_onset - lookback_seconds)
    ]
    immediate = max(nearby, key=lambda span: (span.end, span.start)) if nearby else None
    anchor = immediate.start if immediate else music_onset
    previous_end = max(
        (span.end for span in spans if span.end <= anchor and span.end >= search_start),
        default=None,
    )
    return anchor, immediate, previous_end


def asr_safe_trough_search(
    *,
    anchor: float,
    search_start: float,
    previous_end: float | None,
    padding_seconds: float,
    max_anchor_distance_seconds: float,
) -> Span:
    lower = max(search_start, anchor - max_anchor_distance_seconds)
    if previous_end is not None:
        lower = max(lower, previous_end + padding_seconds)
    return Span(lower, max(lower, anchor))


def smooth_rms(
    rms: np.ndarray,
    bucket_seconds: float,
    smoothing_seconds: float,
) -> np.ndarray:
    width = max(1, int(round(smoothing_seconds / bucket_seconds)))
    if width == 1:
        return rms.astype(np.float64, copy=True)
    kernel = np.full(width, 1.0 / width, dtype=np.float64)
    return np.convolve(rms.astype(np.float64), kernel, mode="same")


def choose_local_volume_trough(
    smoothed_rms: np.ndarray,
    bucket_seconds: float,
    search: Span,
    percentile: float,
) -> dict[str, Any]:
    start_index = max(1, int(math.ceil(search.start / bucket_seconds)))
    end_index = min(
        len(smoothed_rms) - 2,
        int(math.floor(search.end / bucket_seconds)),
    )
    if end_index < start_index:
        return {
            "selected": max(0.0, search.start),
            "rms": math.nan,
            "percentile_value": math.nan,
            "mode": "empty",
        }
    values = smoothed_rms[start_index : end_index + 1]
    percentile_value = float(np.percentile(values, percentile))
    candidates = [
        index
        for index in range(start_index, end_index + 1)
        if smoothed_rms[index] <= smoothed_rms[index - 1]
        and smoothed_rms[index] <= smoothed_rms[index + 1]
        and smoothed_rms[index] <= percentile_value
    ]
    if candidates:
        selected_index = candidates[-1]
        mode = "nearest_low_local_trough"
    else:
        selected_index = start_index + int(np.argmin(values))
        mode = "window_minimum_fallback"
    return {
        "selected": (selected_index + 0.5) * bucket_seconds,
        "rms": float(smoothed_rms[selected_index]),
        "percentile_value": percentile_value,
        "mode": mode,
    }


def load_waveform(path: Path) -> tuple[float, np.ndarray]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    bucket_seconds = float(payload["bucket_seconds"])
    rms = np.asarray(payload["rms"], dtype=np.float64)
    if not payload.get("normalized", False):
        divisor = float(payload.get("quantization_max", 32767.0))
        rms = rms / divisor
    if rms.size < 3:
        raise ValueError("Waveform must contain at least three RMS buckets")
    return bucket_seconds, rms


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refine song starts from lyrics, music onset, ASR occupancy, and a local RMS trough."
    )
    parser.add_argument("--intervals-csv", type=Path, required=True)
    parser.add_argument("--phrases-csv", type=Path, required=True)
    parser.add_argument("--detection-csv", type=Path, required=True)
    parser.add_argument("--waveform-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--search-seconds", type=float, default=60.0)
    parser.add_argument("--music-threshold", type=float, default=0.5)
    parser.add_argument("--max-music-gap-seconds", type=float, default=2.0)
    parser.add_argument("--min-music-run-seconds", type=float, default=4.0)
    parser.add_argument("--lyric-run-tolerance-seconds", type=float, default=5.0)
    parser.add_argument("--asr-lookback-seconds", type=float, default=15.0)
    parser.add_argument("--asr-padding-seconds", type=float, default=0.3)
    parser.add_argument("--max-anchor-distance-seconds", type=float, default=5.0)
    parser.add_argument("--rms-smoothing-seconds", type=float, default=0.4)
    parser.add_argument("--low-volume-percentile", type=float, default=35.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    intervals = read_csv(args.intervals_csv.resolve())
    phrases = read_csv(args.phrases_csv.resolve())
    detection = read_csv(args.detection_csv.resolve())
    if not intervals or not phrases or not detection:
        raise ValueError("Intervals, phrases, and detection inputs must contain rows")
    bucket_seconds, rms = load_waveform(args.waveform_json.resolve())
    smoothed = smooth_rms(rms, bucket_seconds, args.rms_smoothing_seconds)
    duration = len(rms) * bucket_seconds
    occupied = merged_asr_spans(phrases, args.asr_padding_seconds, duration)
    output_rows: list[dict[str, Any]] = []
    choices: list[dict[str, Any]] = []
    for interval in intervals:
        song_label = str(interval["song_label"])
        first_lyric = float(interval["start_seconds"])
        raw_end = float(interval["end_seconds"])
        search_start = max(0.0, first_lyric - args.search_seconds)
        search = Span(
            search_start,
            min(first_lyric + args.lyric_run_tolerance_seconds, duration),
        )
        runs = music_runs(
            detection,
            search,
            args.music_threshold,
            args.max_music_gap_seconds,
            args.min_music_run_seconds,
        )
        selected_run = choose_lyric_music_run(
            runs,
            first_lyric,
            args.lyric_run_tolerance_seconds,
        )
        onset_observed = bool(selected_run and selected_run.start > search_start + 0.5)
        music_onset = (
            selected_run.start if onset_observed and selected_run else first_lyric
        )
        history_start = max(0.0, search_start - args.max_anchor_distance_seconds)
        anchor, immediate_asr, previous_asr_end = asr_gap_anchor(
            occupied,
            music_onset,
            history_start,
            args.asr_lookback_seconds,
        )
        anchor = max(0.0, min(anchor, music_onset, first_lyric) - 0.02)
        trough_search = asr_safe_trough_search(
            anchor=anchor,
            search_start=max(0.0, anchor - args.max_anchor_distance_seconds),
            previous_end=previous_asr_end,
            padding_seconds=0.02,
            max_anchor_distance_seconds=args.max_anchor_distance_seconds,
        )
        trough = choose_local_volume_trough(
            smoothed,
            bucket_seconds,
            trough_search,
            args.low_volume_percentile,
        )
        cut_start = max(
            0.0,
            min(
                float(trough["selected"]),
                anchor,
                music_onset - 0.001,
                first_lyric - 0.001,
            ),
        )
        if not cut_start < first_lyric:
            raise ValueError(f"Start is not before first lyric: {song_label}")
        if onset_observed and not cut_start < music_onset:
            raise ValueError(f"Start is not before music onset: {song_label}")
        overlap = [
            phrase
            for phrase in phrases
            if float(phrase["start_seconds"]) - args.asr_padding_seconds
            <= cut_start
            <= float(phrase["end_seconds"]) + args.asr_padding_seconds
        ]
        if overlap:
            raise ValueError(
                f"Start overlaps ASR: {song_label} at {seconds_to_timestamp(cut_start)}"
            )
        confidence = (
            90.0
            if onset_observed and trough["mode"] == "nearest_low_local_trough"
            else 55.0
        )
        output_rows.append(
            {
                **interval,
                "raw_lyric_start_seconds": f"{first_lyric:.3f}",
                "raw_lyric_end_seconds": f"{raw_end:.3f}",
                "cut_start_seconds": f"{cut_start:.3f}",
                "cut_start_ts": seconds_to_timestamp(cut_start),
                "start_method": "music_onset_asr_local_rms_trough",
                "start_mode": trough["mode"],
                "start_confidence": f"{confidence:.2f}",
            }
        )
        choices.append(
            {
                "interval_no": interval["interval_no"],
                "song_label": song_label,
                "first_lyric_seconds": f"{first_lyric:.3f}",
                "music_onset_seconds": f"{music_onset:.3f}",
                "music_run_found": onset_observed,
                "pre_music_asr_start_seconds": (
                    f"{immediate_asr.start:.3f}" if immediate_asr else ""
                ),
                "previous_asr_end_seconds": (
                    f"{previous_asr_end:.3f}" if previous_asr_end is not None else ""
                ),
                "trough_search_start_seconds": f"{trough_search.start:.3f}",
                "trough_search_end_seconds": f"{trough_search.end:.3f}",
                "cut_start_seconds": f"{cut_start:.3f}",
                "smoothed_rms": f"{float(trough['rms']):.8f}",
                "low_percentile_rms": f"{float(trough['percentile_value']):.8f}",
                "mode": trough["mode"],
            }
        )
    output = args.output_dir.resolve()
    write_csv(
        output / "song_intervals_with_starts.csv",
        output_rows,
        list(output_rows[0]),
    )
    write_csv(
        output / "start_boundary_choices.csv",
        choices,
        list(choices[0]),
    )
    summary = {
        "interval_count": len(output_rows),
        "music_run_found_count": sum(bool(row["music_run_found"]) for row in choices),
        "local_trough_count": sum(
            row["mode"] == "nearest_low_local_trough" for row in choices
        ),
        "parameters": vars(args),
    }
    summary["parameters"] = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in summary["parameters"].items()
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
