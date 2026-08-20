from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from pipeline_utils import probe_duration, read_csv, seconds_to_timestamp, write_csv


POINT_OFFSETS = (-15, -10, -7, -5, -3, -2, -1, 0, 1, 2, 3, 5, 7, 10, 15)
STAT_WINDOWS = (2, 3, 5, 10, 20)
LOW_THRESHOLDS = (0.25, 0.35, 0.45, 0.55, 0.65)
ASR_WINDOWS = (2, 5, 10, 20)


def feature_names() -> tuple[str, ...]:
    names = ["candidate_offset_after_lyric", "song_duration", "available_search_span"]
    names.extend(f"music_probability_offset_{offset:+d}" for offset in POINT_OFFSETS)
    for window in STAT_WINDOWS:
        for side in ("before", "after"):
            names.extend(
                f"music_{stat}_{side}_{window}s"
                for stat in ("mean", "std", "min", "max")
            )
    for threshold in LOW_THRESHOLDS:
        names.extend(
            (
                f"low_run_before_threshold_{threshold:.2f}",
                f"low_run_after_threshold_{threshold:.2f}",
            )
        )
    names.extend(
        ("asr_overlapping", "seconds_since_previous_asr", "seconds_until_next_asr")
    )
    for window in ASR_WINDOWS:
        names.extend(
            (
                f"talk_coverage_{window}s",
                f"speech_coverage_{window}s",
                f"asr_phrase_count_{window}s",
            )
        )
    return tuple(names)


FEATURE_NAMES = feature_names()


@dataclass(frozen=True)
class Span:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(frozen=True)
class StableRun:
    start: float
    end: float
    mean_music_probability: float
    max_music_probability: float
    seconds: int

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(frozen=True)
class SpeechPhrase:
    start: float
    end: float
    is_talk: bool


class ProbabilityTimeline:
    def __init__(self, values: Sequence[float]) -> None:
        if not values:
            raise ValueError("Music probability timeline cannot be empty")
        self.values = np.asarray(values, dtype=np.float32)

    def at(self, seconds: float) -> float:
        index = min(len(self.values) - 1, max(0, math.floor(seconds)))
        return float(self.values[index])

    def stats(self, start: float, end: float) -> tuple[float, float, float, float]:
        low = max(0, math.floor(start))
        high = min(len(self.values), math.ceil(end))
        values = self.values[low:high]
        if not len(values):
            return (0.0, 0.0, 0.0, 0.0)
        return (
            float(values.mean()),
            float(values.std()),
            float(values.min()),
            float(values.max()),
        )


def merge_spans(spans: Iterable[Span]) -> list[Span]:
    ordered = sorted(
        (span for span in spans if span.end > span.start),
        key=lambda item: item.start,
    )
    merged: list[Span] = []
    for span in ordered:
        if not merged or span.start > merged[-1].end:
            merged.append(span)
        else:
            merged[-1] = Span(merged[-1].start, max(merged[-1].end, span.end))
    return merged


def subtract_spans(container: Span, blocked: Iterable[Span]) -> list[Span]:
    cursor = container.start
    safe: list[Span] = []
    for span in merge_spans(blocked):
        if span.end <= cursor or span.start >= container.end:
            continue
        clipped_start = max(container.start, span.start)
        clipped_end = min(container.end, span.end)
        if clipped_start > cursor:
            safe.append(Span(cursor, clipped_start))
        cursor = max(cursor, clipped_end)
        if cursor >= container.end:
            break
    if cursor < container.end:
        safe.append(Span(cursor, container.end))
    return [span for span in safe if span.duration > 0]


def token_blocks(
    word_rows: Iterable[dict[str, str]],
    padding_seconds: float,
    duration_seconds: float,
) -> list[Span]:
    return merge_spans(
        Span(
            max(0.0, float(row["start_seconds"]) - padding_seconds),
            min(duration_seconds, float(row["end_seconds"]) + padding_seconds),
        )
        for row in word_rows
    )


def stable_runs(
    per_second_rows: list[dict[str, Any]],
    search: Span,
    threshold: float,
    consecutive_seconds: int,
) -> list[StableRun]:
    eligible: list[tuple[int, float]] = []
    for row in per_second_rows:
        start = int(float(row["second_start"]))
        end = float(row["second_end"])
        text = str(row.get("avg_music_probability", ""))
        if not text or start < search.start or end > search.end:
            continue
        probability = float(text)
        if probability <= threshold:
            eligible.append((start, probability))
    runs: list[StableRun] = []
    current: list[tuple[int, float]] = []

    def flush() -> None:
        if len(current) < consecutive_seconds:
            return
        probabilities = [value for _, value in current]
        runs.append(
            StableRun(
                start=float(current[0][0]),
                end=float(current[-1][0] + 1),
                mean_music_probability=sum(probabilities) / len(probabilities),
                max_music_probability=max(probabilities),
                seconds=len(current),
            )
        )

    for item in eligible:
        if current and item[0] != current[-1][0] + 1:
            flush()
            current = []
        current.append(item)
    flush()
    return runs


def probability_near(per_second_rows: list[dict[str, Any]], seconds: float) -> float:
    index = min(max(0, int(math.floor(seconds))), len(per_second_rows) - 1)
    text = str(per_second_rows[index].get("avg_music_probability", ""))
    return float(text) if text else 1.0


def nearest_token_clearance(seconds: float, blocks: list[Span]) -> float:
    if not blocks:
        return math.inf
    distances: list[float] = []
    for block in blocks:
        if block.start <= seconds <= block.end:
            return 0.0
        distances.append(min(abs(seconds - block.start), abs(seconds - block.end)))
    return min(distances)


def choose_boundary(
    *,
    boundary: str,
    search: Span,
    per_second_rows: list[dict[str, Any]],
    blocks: list[Span],
    threshold: float,
    consecutive_seconds: int,
    plateau_margin_seconds: float,
    min_safe_gap_seconds: float,
) -> dict[str, Any]:
    if boundary not in {"start", "end"}:
        raise ValueError("boundary must be start or end")
    runs = stable_runs(per_second_rows, search, threshold, consecutive_seconds)
    ordered = sorted(
        runs,
        key=(
            (lambda run: (-run.end, -run.duration, run.max_music_probability))
            if boundary == "start"
            else (lambda run: (run.start, -run.duration, run.max_music_probability))
        ),
    )
    for run in ordered:
        interior = Span(
            run.start + plateau_margin_seconds,
            run.end - plateau_margin_seconds,
        )
        if interior.duration < min_safe_gap_seconds:
            continue
        safe = [
            gap
            for gap in subtract_spans(interior, blocks)
            if gap.duration >= min_safe_gap_seconds
        ]
        if not safe:
            continue
        safe.sort(
            key=(
                (lambda gap: (-gap.duration, gap.start))
                if boundary == "start"
                else (lambda gap: (-gap.duration, -gap.end))
            )
        )
        gap = safe[0]
        selected = (gap.start + gap.end) / 2.0
        threshold_margin = max(
            0.0,
            (threshold - run.max_music_probability) / max(threshold, 1e-9),
        )
        confidence = (
            65.0
            + 20.0 * threshold_margin
            + 10.0 * min(1.0, run.duration / 10.0)
            + 5.0 * min(1.0, gap.duration / 2.0)
        )
        return {
            "mode": "stable_non_music_token_safe",
            "selected": selected,
            "selected_probability": probability_near(per_second_rows, selected),
            "confidence": min(100.0, confidence),
            "run": run,
            "safe_gap": gap,
            "all_runs": runs,
            "token_clearance": nearest_token_clearance(selected, blocks),
        }
    all_safe = [
        gap
        for gap in subtract_spans(search, blocks)
        if gap.duration >= min_safe_gap_seconds
    ]
    if not all_safe:
        selected = search.start if boundary == "start" else search.end
        return {
            "mode": "asr_anchor_no_token_safe_gap",
            "selected": selected,
            "selected_probability": probability_near(per_second_rows, selected),
            "confidence": 0.0,
            "run": None,
            "safe_gap": None,
            "all_runs": runs,
            "token_clearance": nearest_token_clearance(selected, blocks),
        }
    anchor = search.end if boundary == "start" else search.start
    candidates = []
    for gap in all_safe:
        midpoint = (gap.start + gap.end) / 2.0
        candidates.append(
            (
                probability_near(per_second_rows, midpoint),
                abs(midpoint - anchor),
                midpoint,
                gap,
            )
        )
    probability, _, selected, gap = min(candidates, key=lambda item: (item[0], item[1]))
    return {
        "mode": "fallback_low_detection_token_safe",
        "selected": selected,
        "selected_probability": probability,
        "confidence": max(0.0, 35.0 * (1.0 - probability)),
        "run": None,
        "safe_gap": gap,
        "all_runs": runs,
        "token_clearance": nearest_token_clearance(selected, blocks),
    }


def ranker_metadata_is_compatible(metadata: dict[str, Any]) -> tuple[bool, str]:
    if metadata.get("schema_version") != 1:
        return False, "unsupported feature schema version"
    if metadata.get("generalization_claim") is not True:
        return False, "ranker has no independent generalization evidence"
    features = metadata.get("strategy", {}).get("features")
    if features != list(FEATURE_NAMES):
        return False, "ranker feature list does not match production schema"
    return True, "compatible"


def build_candidate_times(
    *,
    raw_end: float,
    next_song_start: float,
    search_seconds: float,
    step_seconds: float,
) -> list[float]:
    first = math.floor((raw_end + 1e-9) / step_seconds) + 1
    last_time = min(next_song_start, raw_end + search_seconds)
    last = math.floor((last_time + 1e-9) / step_seconds)
    return [round(index * step_seconds, 6) for index in range(first, last + 1)]


def coverage(
    phrases: Sequence[SpeechPhrase],
    start: float,
    end: float,
    *,
    talk_only: bool,
) -> float:
    duration = end - start
    if duration <= 0:
        return 0.0
    overlap = sum(
        max(0.0, min(end, phrase.end) - max(start, phrase.start))
        for phrase in phrases
        if not talk_only or phrase.is_talk
    )
    return min(1.0, overlap / duration)


def build_feature_vector(
    *,
    raw_end: float,
    song_duration: float,
    search_span: float,
    candidate_time: float,
    probabilities: ProbabilityTimeline,
    phrases: Sequence[SpeechPhrase],
) -> list[float]:
    features: list[float] = [candidate_time - raw_end, song_duration, search_span]
    features.extend(
        probabilities.at(candidate_time + offset) for offset in POINT_OFFSETS
    )
    for window in STAT_WINDOWS:
        features.extend(probabilities.stats(candidate_time - window, candidate_time))
        features.extend(probabilities.stats(candidate_time, candidate_time + window))
    for threshold in LOW_THRESHOLDS:
        before = 0
        for offset in range(1, 31):
            if probabilities.at(candidate_time - offset) <= threshold:
                before += 1
            else:
                break
        after = 0
        for offset in range(30):
            if probabilities.at(candidate_time + offset) <= threshold:
                after += 1
            else:
                break
        features.extend((float(before), float(after)))
    overlapping = any(
        phrase.start <= candidate_time <= phrase.end for phrase in phrases
    )
    previous = [phrase.end for phrase in phrases if phrase.end <= candidate_time]
    following = [phrase.start for phrase in phrases if phrase.start >= candidate_time]
    features.extend(
        (
            float(overlapping),
            min(60.0, candidate_time - max(previous)) if previous else 60.0,
            min(60.0, min(following) - candidate_time) if following else 60.0,
        )
    )
    for window in ASR_WINDOWS:
        start = candidate_time - window
        end = candidate_time + window
        nearby = [
            phrase for phrase in phrases if phrase.start < end and phrase.end > start
        ]
        features.extend(
            (
                coverage(nearby, start, end, talk_only=True),
                coverage(nearby, start, end, talk_only=False),
                float(len(nearby)),
            )
        )
    if len(features) != len(FEATURE_NAMES):
        raise AssertionError("End-ranker feature schema mismatch")
    return features


def ranker_choice(
    *,
    model: Any,
    raw_end: float,
    song_duration: float,
    next_start: float,
    search_seconds: float,
    step_seconds: float,
    probabilities: ProbabilityTimeline,
    phrases: list[SpeechPhrase],
) -> dict[str, Any]:
    candidates = build_candidate_times(
        raw_end=raw_end,
        next_song_start=next_start,
        search_seconds=search_seconds,
        step_seconds=step_seconds,
    )
    if not candidates:
        raise ValueError("Ranker search produced no candidate times")
    search_span = min(next_start, raw_end + search_seconds) - raw_end
    features = np.asarray(
        [
            build_feature_vector(
                raw_end=raw_end,
                song_duration=song_duration,
                search_span=search_span,
                candidate_time=candidate,
                probabilities=probabilities,
                phrases=phrases,
            )
            for candidate in candidates
        ],
        dtype=np.float32,
    )
    scores = model.predict_proba(features)[:, 1]
    selected_index = max(
        range(len(candidates)),
        key=lambda index: (float(scores[index]), -index),
    )
    return {
        "mode": "compatible_prebuilt_music_asr_ranker",
        "selected": candidates[selected_index],
        "confidence": 100.0 * float(scores[selected_index]),
        "ranker_score": float(scores[selected_index]),
        "candidate_count": len(candidates),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refine song ends with a compatible ranker or deterministic ASR plus MusicDetection."
    )
    parser.add_argument("--intervals-csv", type=Path, required=True)
    parser.add_argument("--phrases-csv", type=Path, required=True)
    parser.add_argument("--words-csv", type=Path, required=True)
    parser.add_argument("--detection-csv", type=Path, required=True)
    parser.add_argument("--source-video", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--deterministic-search-seconds", type=float, default=30.0)
    parser.add_argument("--ranker-search-seconds", type=float, default=90.0)
    parser.add_argument("--candidate-step-seconds", type=float, default=0.25)
    parser.add_argument("--non-music-threshold", type=float, default=0.35)
    parser.add_argument("--stable-non-music-seconds", type=int, default=2)
    parser.add_argument("--token-padding-seconds", type=float, default=0.30)
    parser.add_argument("--plateau-margin-seconds", type=float, default=0.50)
    parser.add_argument("--min-safe-gap-seconds", type=float, default=0.60)
    parser.add_argument("--ranker-model", type=Path)
    parser.add_argument("--ranker-metadata", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    intervals = read_csv(args.intervals_csv.resolve())
    phrase_rows = read_csv(args.phrases_csv.resolve())
    word_rows = read_csv(args.words_csv.resolve())
    probability_rows = read_csv(args.detection_csv.resolve())
    if not intervals or not phrase_rows or not word_rows or not probability_rows:
        raise ValueError("All end-boundary inputs must contain rows")
    duration = probe_duration(args.source_video.resolve())
    blocks = token_blocks(word_rows, args.token_padding_seconds, duration)
    probabilities = ProbabilityTimeline(
        [float(row["avg_music_probability"]) for row in probability_rows]
    )
    phrases = [
        SpeechPhrase(
            start=float(row["start_seconds"]),
            end=float(row["end_seconds"]),
            is_talk=str(row.get("song_label", "")).strip() == "talk",
        )
        for row in phrase_rows
    ]
    model = None
    ranker_metadata: dict[str, Any] | None = None
    if bool(args.ranker_model) != bool(args.ranker_metadata):
        raise ValueError("Provide both --ranker-model and --ranker-metadata")
    if args.ranker_model and args.ranker_metadata:
        ranker_metadata = json.loads(
            args.ranker_metadata.resolve().read_text(encoding="utf-8")
        )
        compatible, reason = ranker_metadata_is_compatible(ranker_metadata)
        if not compatible:
            raise ValueError(f"Ranker rejected: {reason}")
        try:
            import joblib
        except ImportError as exc:
            raise RuntimeError("joblib is required for ranker inference") from exc
        model = joblib.load(args.ranker_model.resolve())

    choices: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    for offset, interval in enumerate(intervals):
        raw_end = float(
            interval.get("raw_lyric_end_seconds") or interval["end_seconds"]
        )
        next_start = (
            float(
                intervals[offset + 1].get("raw_lyric_start_seconds")
                or intervals[offset + 1]["start_seconds"]
            )
            if offset + 1 < len(intervals)
            else duration
        )
        if model is not None:
            choice = ranker_choice(
                model=model,
                raw_end=raw_end,
                song_duration=float(interval["duration_seconds"]),
                next_start=next_start,
                search_seconds=args.ranker_search_seconds,
                step_seconds=args.candidate_step_seconds,
                probabilities=probabilities,
                phrases=phrases,
            )
            search = Span(
                raw_end,
                min(next_start, raw_end + args.ranker_search_seconds, duration),
            )
        else:
            search = Span(
                raw_end,
                min(
                    next_start,
                    raw_end + args.deterministic_search_seconds,
                    duration,
                ),
            )
            choice = choose_boundary(
                boundary="end",
                search=search,
                per_second_rows=probability_rows,
                blocks=blocks,
                threshold=args.non_music_threshold,
                consecutive_seconds=args.stable_non_music_seconds,
                plateau_margin_seconds=args.plateau_margin_seconds,
                min_safe_gap_seconds=args.min_safe_gap_seconds,
            )
        cut_end = float(choice["selected"])
        cut_start = float(interval["cut_start_seconds"])
        if cut_end <= max(cut_start, raw_end):
            raise ValueError(f"Invalid end for interval {interval['interval_no']}")
        start_confidence = float(interval.get("start_confidence") or 0.0)
        end_confidence = float(choice["confidence"])
        output_rows.append(
            {
                **interval,
                "cut_end_seconds": f"{cut_end:.3f}",
                "cut_end_ts": seconds_to_timestamp(cut_end),
                "cut_duration_seconds": f"{cut_end - cut_start:.3f}",
                "end_method": choice["mode"],
                "end_mode": choice["mode"],
                "end_confidence": f"{end_confidence:.2f}",
                "boundary_confidence": f"{min(start_confidence, end_confidence):.2f}",
            }
        )
        choices.append(
            {
                "interval_no": interval["interval_no"],
                "song_label": interval["song_label"],
                "raw_lyric_end_seconds": f"{raw_end:.3f}",
                "search_start_seconds": f"{search.start:.3f}",
                "search_end_seconds": f"{search.end:.3f}",
                "cut_end_seconds": f"{cut_end:.3f}",
                "cut_end_ts": seconds_to_timestamp(cut_end),
                "mode": choice["mode"],
                "confidence": f"{end_confidence:.2f}",
                "ranker_score": (
                    f"{float(choice['ranker_score']):.8f}"
                    if "ranker_score" in choice
                    else ""
                ),
                "selected_music_probability": (
                    f"{float(choice['selected_probability']):.6f}"
                    if "selected_probability" in choice
                    else ""
                ),
                "token_clearance_seconds": (
                    f"{float(choice['token_clearance']):.3f}"
                    if "token_clearance" in choice
                    else ""
                ),
            }
        )
    output = args.output_dir.resolve()
    write_csv(output / "song_cut_intervals.csv", output_rows, list(output_rows[0]))
    write_csv(output / "end_boundary_choices.csv", choices, list(choices[0]))
    low_confidence = [row for row in choices if float(row["confidence"]) < 75.0]
    write_csv(
        output / "low_confidence_end_boundaries.csv",
        low_confidence,
        list(choices[0]),
    )
    summary = {
        "interval_count": len(output_rows),
        "ranker_used": model is not None,
        "ranker_metadata": ranker_metadata,
        "low_confidence_end_count": len(low_confidence),
        "deterministic_fallback_count": sum(
            row["mode"] != "compatible_prebuilt_music_asr_ranker" for row in choices
        ),
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
