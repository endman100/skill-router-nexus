from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pipeline_utils import read_csv, seconds_to_timestamp, write_csv


def confidence(row: dict[str, str]) -> float:
    for key in ("label_confidence", "song_confidence", "confidence"):
        value = row.get(key)
        if value not in (None, ""):
            return float(value)
    return 0.0


def suppress_short_song_runs(
    rows: list[dict[str, str]],
    *,
    label_key: str,
    talk_label: str,
    start_column: str,
    end_column: str,
    min_song_run_duration_seconds: float,
    min_song_run_phrase_rows: int,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    filtered = [dict(row) for row in rows]
    rejected: list[dict[str, Any]] = []
    current_label: str | None = None
    offsets: list[int] = []

    def flush() -> None:
        if current_label in (None, talk_label) or not offsets:
            return
        run_rows = [filtered[offset] for offset in offsets]
        start = min(float(row[start_column]) for row in run_rows)
        end = max(float(row[end_column]) for row in run_rows)
        duration = end - start
        reasons: list[str] = []
        if duration < min_song_run_duration_seconds:
            reasons.append("duration_lt_min")
        if len(run_rows) < min_song_run_phrase_rows:
            reasons.append("phrase_rows_lt_min")
        if not reasons:
            return
        for offset in offsets:
            filtered[offset][label_key] = talk_label
        rejected.append(
            {
                "rejected_run_no": len(rejected) + 1,
                "original_song_label": current_label,
                "start_seconds": f"{start:.3f}",
                "end_seconds": f"{end:.3f}",
                "start_ts": seconds_to_timestamp(start),
                "end_ts": seconds_to_timestamp(end),
                "duration_seconds": f"{duration:.3f}",
                "first_phrase_index": run_rows[0].get("index", ""),
                "last_phrase_index": run_rows[-1].get("index", ""),
                "phrase_rows": len(run_rows),
                "rejected_reasons": ";".join(reasons),
                "new_label": talk_label,
            }
        )

    for offset, row in enumerate(filtered):
        label = str(row.get(label_key, "")).strip()
        if label != current_label:
            flush()
            current_label = label
            offsets = []
        offsets.append(offset)
    flush()
    return filtered, rejected


def build_strict_runs(
    rows: list[dict[str, str]],
    *,
    label_key: str,
    talk_label: str,
    start_column: str,
    end_column: str,
) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    current_label: str | None = None
    current_rows: list[dict[str, str]] = []

    def flush() -> None:
        if not current_rows or current_label in (None, talk_label):
            return
        start = min(float(row[start_column]) for row in current_rows)
        end = max(float(row[end_column]) for row in current_rows)
        confidences = [confidence(row) for row in current_rows]
        runs.append(
            {
                "strict_run_no": len(runs) + 1,
                "song_label": current_label,
                "start_seconds": f"{start:.3f}",
                "end_seconds": f"{end:.3f}",
                "start_ts": seconds_to_timestamp(start),
                "end_ts": seconds_to_timestamp(end),
                "duration_seconds": f"{end - start:.3f}",
                "first_phrase_index": current_rows[0].get("index", ""),
                "last_phrase_index": current_rows[-1].get("index", ""),
                "phrase_rows": len(current_rows),
                "mean_label_confidence": f"{sum(confidences) / len(confidences):.3f}",
                "min_label_confidence": f"{min(confidences):.3f}",
            }
        )

    for row in rows:
        label = str(row.get(label_key, "")).strip()
        if label != current_label:
            flush()
            current_label = label
            current_rows = []
        current_rows.append(row)
    flush()
    return runs


def music_gap_is_continuous(
    detection_rows: list[dict[str, str]],
    start_seconds: float,
    end_seconds: float,
    *,
    threshold: float,
    mean_threshold: float,
    max_interrupt_seconds: float,
) -> bool:
    if end_seconds <= start_seconds:
        return True
    weighted = 0.0
    covered = 0.0
    current_interrupt = 0.0
    longest_interrupt = 0.0
    for row in detection_rows:
        text = str(row.get("avg_music_probability", "")).strip()
        if not text:
            continue
        row_start = float(row["second_start"])
        row_end = float(row["second_end"])
        overlap = max(0.0, min(end_seconds, row_end) - max(start_seconds, row_start))
        if overlap <= 0:
            continue
        probability = float(text)
        weighted += overlap * probability
        covered += overlap
        if probability < threshold:
            current_interrupt += overlap
            longest_interrupt = max(longest_interrupt, current_interrupt)
        else:
            current_interrupt = 0.0
    duration = end_seconds - start_seconds
    if covered < duration - 0.05:
        return False
    return (
        weighted / covered >= mean_threshold
        and longest_interrupt <= max_interrupt_seconds
    )


def build_final_intervals(
    strict_runs: list[dict[str, Any]],
    *,
    detection_rows: list[dict[str, str]],
    same_label_pause_seconds: float,
    music_continuity_threshold: float,
    music_continuity_mean_threshold: float,
    max_music_interrupt_seconds: float,
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for run in strict_runs:
        if not groups:
            groups.append({"runs": [run], "merge_reasons": []})
            continue
        group = groups[-1]
        previous = group["runs"][-1]
        same_label = run["song_label"] == previous["song_label"]
        gap = float(run["start_seconds"]) - float(previous["end_seconds"])
        continuous_music = same_label and music_gap_is_continuous(
            detection_rows,
            float(previous["end_seconds"]),
            float(run["start_seconds"]),
            threshold=music_continuity_threshold,
            mean_threshold=music_continuity_mean_threshold,
            max_interrupt_seconds=max_music_interrupt_seconds,
        )
        short_pause = same_label and gap <= same_label_pause_seconds
        if continuous_music or short_pause:
            group["runs"].append(run)
            if continuous_music:
                group["merge_reasons"].append("same_title_continuous_music")
            if short_pause:
                group["merge_reasons"].append(
                    f"same_title_pause_le_{same_label_pause_seconds:g}s"
                )
        else:
            groups.append({"runs": [run], "merge_reasons": []})

    output: list[dict[str, Any]] = []
    for group in groups:
        runs = group["runs"]
        start = min(float(run["start_seconds"]) for run in runs)
        end = max(float(run["end_seconds"]) for run in runs)
        mean_confidences = [float(run["mean_label_confidence"]) for run in runs]
        output.append(
            {
                "interval_no": len(output) + 1,
                "song_label": runs[0]["song_label"],
                "merge_reasons": ";".join(dict.fromkeys(group["merge_reasons"])),
                "start_seconds": f"{start:.3f}",
                "end_seconds": f"{end:.3f}",
                "start_ts": seconds_to_timestamp(start),
                "end_ts": seconds_to_timestamp(end),
                "duration_seconds": f"{end - start:.3f}",
                "strict_run_numbers": ";".join(
                    str(run["strict_run_no"]) for run in runs
                ),
                "strict_runs_merged": len(runs),
                "first_phrase_index": runs[0]["first_phrase_index"],
                "last_phrase_index": runs[-1]["last_phrase_index"],
                "phrase_rows": sum(int(run["phrase_rows"]) for run in runs),
                "mean_label_confidence": (
                    f"{sum(mean_confidences) / len(mean_confidences):.3f}"
                ),
                "min_label_confidence": (
                    f"{min(float(run['min_label_confidence']) for run in runs):.3f}"
                ),
            }
        )
    return output


def interval_music_probability(
    detection_rows: list[dict[str, str]],
    start_seconds: float,
    end_seconds: float,
) -> tuple[float, float]:
    weighted = 0.0
    covered = 0.0
    for row in detection_rows:
        text = str(row.get("avg_music_probability", "")).strip()
        if not text:
            continue
        row_start = float(row["second_start"])
        row_end = float(row["second_end"])
        overlap = max(0.0, min(end_seconds, row_end) - max(start_seconds, row_start))
        if overlap > 0:
            weighted += overlap * float(text)
            covered += overlap
    if covered <= 0:
        raise ValueError(
            f"No MusicDetection coverage for {start_seconds:.3f}-{end_seconds:.3f}"
        )
    return weighted / covered, covered


def filter_intervals_by_music_probability(
    intervals: list[dict[str, Any]],
    detection_rows: list[dict[str, str]],
    *,
    min_mean_music_probability: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for interval in intervals:
        candidate = dict(interval)
        start = float(interval["start_seconds"])
        end = float(interval["end_seconds"])
        mean_probability, covered = interval_music_probability(
            detection_rows,
            start,
            end,
        )
        duration = end - start
        candidate.update(
            {
                "candidate_interval_no": interval["interval_no"],
                "mean_music_probability": f"{mean_probability:.6f}",
                "music_probability_coverage_seconds": f"{covered:.3f}",
                "music_probability_coverage_ratio": f"{covered / duration:.6f}",
            }
        )
        candidates.append(candidate)
        coverage_complete = covered >= duration - 0.05
        if coverage_complete and mean_probability >= min_mean_music_probability:
            accepted = dict(candidate)
            accepted["interval_no"] = len(kept) + 1
            kept.append(accepted)
        else:
            reason = (
                "music_probability_coverage_incomplete"
                if not coverage_complete
                else "mean_music_probability_lt_min"
            )
            rejected.append(
                {
                    **candidate,
                    "rejected_interval_no": len(rejected) + 1,
                    "rejected_reason": reason,
                    "min_mean_music_probability": f"{min_mean_music_probability:.6f}",
                }
            )
    return kept, rejected, candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build song intervals from talk-or-title phrase labels."
    )
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--music-detection-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--label-key", default="song_label")
    parser.add_argument("--talk-label", default="talk")
    parser.add_argument("--start-column", default="start_seconds")
    parser.add_argument("--end-column", default="end_seconds")
    parser.add_argument("--same-label-pause-seconds", type=float, default=15.0)
    parser.add_argument("--music-continuity-threshold", type=float, default=0.5)
    parser.add_argument("--music-continuity-mean-threshold", type=float, default=0.6)
    parser.add_argument("--max-music-interrupt-seconds", type=float, default=2.0)
    parser.add_argument("--min-song-run-duration-seconds", type=float, default=30.0)
    parser.add_argument("--min-song-run-phrase-rows", type=int, default=3)
    parser.add_argument("--min-mean-music-probability", type=float, default=0.6)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.input_csv.resolve())
    detection = read_csv(args.music_detection_csv.resolve())
    if not rows or not detection:
        raise ValueError("Labeled phrases and MusicDetection must both contain rows")
    required = {args.label_key, args.start_column, args.end_column}
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"Missing labeled phrase columns: {missing}")
    labels = {str(row[args.label_key]).strip() for row in rows}
    forbidden = sorted(
        label
        for label in labels
        if label.casefold() in {"lyric", "setup", "unknown_song"}
    )
    if forbidden:
        raise ValueError(f"Forbidden labels: {forbidden}")
    ordered = sorted(
        rows,
        key=lambda row: (float(row[args.start_column]), float(row[args.end_column])),
    )
    filtered, rejected_runs = suppress_short_song_runs(
        ordered,
        label_key=args.label_key,
        talk_label=args.talk_label,
        start_column=args.start_column,
        end_column=args.end_column,
        min_song_run_duration_seconds=args.min_song_run_duration_seconds,
        min_song_run_phrase_rows=args.min_song_run_phrase_rows,
    )
    strict_runs = build_strict_runs(
        filtered,
        label_key=args.label_key,
        talk_label=args.talk_label,
        start_column=args.start_column,
        end_column=args.end_column,
    )
    candidates = build_final_intervals(
        strict_runs,
        detection_rows=detection,
        same_label_pause_seconds=args.same_label_pause_seconds,
        music_continuity_threshold=args.music_continuity_threshold,
        music_continuity_mean_threshold=args.music_continuity_mean_threshold,
        max_music_interrupt_seconds=args.max_music_interrupt_seconds,
    )
    intervals, rejected_music, audited = filter_intervals_by_music_probability(
        candidates,
        detection,
        min_mean_music_probability=args.min_mean_music_probability,
    )
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    filtered_fields = list(filtered[0])
    strict_fields = [
        "strict_run_no",
        "song_label",
        "start_seconds",
        "end_seconds",
        "start_ts",
        "end_ts",
        "duration_seconds",
        "first_phrase_index",
        "last_phrase_index",
        "phrase_rows",
        "mean_label_confidence",
        "min_label_confidence",
    ]
    rejected_run_fields = [
        "rejected_run_no",
        "original_song_label",
        "start_seconds",
        "end_seconds",
        "start_ts",
        "end_ts",
        "duration_seconds",
        "first_phrase_index",
        "last_phrase_index",
        "phrase_rows",
        "rejected_reasons",
        "new_label",
    ]
    interval_fields = [
        "interval_no",
        "candidate_interval_no",
        "song_label",
        "merge_reasons",
        "start_seconds",
        "end_seconds",
        "start_ts",
        "end_ts",
        "duration_seconds",
        "strict_run_numbers",
        "strict_runs_merged",
        "first_phrase_index",
        "last_phrase_index",
        "phrase_rows",
        "mean_label_confidence",
        "min_label_confidence",
        "mean_music_probability",
        "music_probability_coverage_seconds",
        "music_probability_coverage_ratio",
    ]
    write_csv(output / "filtered_labeled_phrases.csv", filtered, filtered_fields)
    write_csv(
        output / "rejected_short_song_runs.csv", rejected_runs, rejected_run_fields
    )
    write_csv(output / "strict_song_runs.csv", strict_runs, strict_fields)
    write_csv(output / "candidate_song_intervals.csv", audited, interval_fields)
    write_csv(
        output / "rejected_low_music_intervals.csv",
        rejected_music,
        [
            "rejected_interval_no",
            *interval_fields,
            "rejected_reason",
            "min_mean_music_probability",
        ],
    )
    write_csv(output / "song_intervals.csv", intervals, interval_fields)
    summary = {
        "phrase_rows": len(rows),
        "rejected_short_song_runs": len(rejected_runs),
        "strict_song_runs": len(strict_runs),
        "candidate_song_intervals": len(candidates),
        "rejected_low_music_intervals": len(rejected_music),
        "song_intervals": len(intervals),
        "parameters": {
            "same_label_pause_seconds": args.same_label_pause_seconds,
            "music_continuity_threshold": args.music_continuity_threshold,
            "music_continuity_mean_threshold": args.music_continuity_mean_threshold,
            "max_music_interrupt_seconds": args.max_music_interrupt_seconds,
            "min_song_run_duration_seconds": args.min_song_run_duration_seconds,
            "min_song_run_phrase_rows": args.min_song_run_phrase_rows,
            "min_mean_music_probability": args.min_mean_music_probability,
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
