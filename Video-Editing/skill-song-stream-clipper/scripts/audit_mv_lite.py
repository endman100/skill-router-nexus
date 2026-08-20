from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
from scipy import signal


SAMPLE_RATE = 8_000


def run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, check=True, capture_output=True)


def probe(path: Path) -> dict[str, object]:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,bit_rate:stream=index,codec_name,codec_type,width,height,avg_frame_rate,nb_frames,sample_rate,channels,duration",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(result.stdout.decode("utf-8"))


def sample_positions(duration: float) -> list[float]:
    positions = [min(8.0, duration * 0.10), duration * 0.50, max(0.0, duration - 12.0)]
    result: list[float] = []
    for value in sorted(
        min(max(0.0, item), max(0.0, duration - 2.0)) for item in positions
    ):
        if not result or value - result[-1] >= 1.0:
            result.append(value)
    while len(result) < 3:
        candidate = duration * (len(result) + 1) / 4.0
        result.append(min(candidate, max(0.0, duration - 2.0)))
        result.sort()
    return result[:3]


def decode_audio(path: Path, start: float, duration: float) -> np.ndarray:
    result = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start:.6f}",
            "-i",
            str(path),
            "-t",
            f"{duration:.6f}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-f",
            "f32le",
            "pipe:1",
        ]
    )
    return np.frombuffer(result.stdout, dtype="<f4").astype(np.float64)


def audio_alignment(
    source_audio: Path,
    output_video: Path,
    clip_start: float,
    relative_start: float,
    window_seconds: float = 8.0,
) -> dict[str, object]:
    reference = decode_audio(source_audio, clip_start + relative_start, window_seconds)
    rendered = decode_audio(output_video, relative_start, window_seconds)
    length = min(len(reference), len(rendered))
    reference = reference[:length] - reference[:length].mean()
    rendered = rendered[:length] - rendered[:length].mean()
    correlation = signal.correlate(rendered, reference, mode="full", method="fft")
    lags = signal.correlation_lags(len(rendered), len(reference), mode="full")
    maximum_lag = int(round(SAMPLE_RATE * 0.250))
    allowed = np.abs(lags) <= maximum_lag
    restricted = correlation[allowed]
    restricted_lags = lags[allowed]
    best_index = int(np.argmax(restricted))
    best_lag = int(restricted_lags[best_index])
    denominator = float(np.linalg.norm(reference) * np.linalg.norm(rendered))
    normalized = float(restricted[best_index] / denominator) if denominator else 0.0
    return {
        "relative_start_seconds": relative_start,
        "window_seconds": window_seconds,
        "lag_samples": best_lag,
        "lag_seconds": best_lag / SAMPLE_RATE,
        "absolute_lag_seconds": abs(best_lag / SAMPLE_RATE),
        "normalized_correlation": normalized,
    }


def subtitle_audit(path: Path, expected_duration: float) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    intervals = [
        (float(row["relative_start"]), float(row["relative_end"]), row["text"])
        for row in rows
    ]
    overlaps = [
        {"left": left[2], "right": right[2], "overlap_seconds": left[1] - right[0]}
        for left, right in zip(intervals, intervals[1:])
        if left[1] > right[0]
    ]
    invalid = [
        row
        for row in intervals
        if row[0] < 0 or row[1] <= row[0] or row[1] > expected_duration + 0.05
    ]
    return {
        "events": len(intervals),
        "overlap_count": len(overlaps),
        "overlaps": overlaps,
        "invalid_interval_count": len(invalid),
    }


def frame_motion_audit(path: Path, duration: float) -> dict[str, object]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open rendered video: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    rows: list[dict[str, object]] = []
    try:
        for start in sample_positions(duration):
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(round(start * fps)))
            rows.append(analyze_motion_window(capture, start, fps, duration=2.0))
    finally:
        capture.release()
    all_differences = [float(row["mean_abs_difference"]) for row in rows]
    return {
        "segments": rows,
        "total_duplicate_frames": sum(int(row["duplicate_frames"]) for row in rows),
        "all_sampled_frames_identical": max(all_differences, default=0.0) < 0.02,
    }


def analyze_motion_window(
    capture: cv2.VideoCapture, start: float, fps: float, duration: float
) -> dict[str, object]:
    previous: np.ndarray | None = None
    differences: list[float] = []
    duplicate_count = 0
    for _ in range(int(round(duration * fps))):
        ok, frame = capture.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (480, 270), interpolation=cv2.INTER_AREA)
        if previous is not None:
            difference = float(cv2.absdiff(previous, gray).mean())
            differences.append(difference)
            if difference < 0.015:
                duplicate_count += 1
        previous = gray
    return {
        "start_seconds": start,
        "frame_pairs": len(differences),
        "mean_abs_difference": float(np.mean(differences)) if differences else 0.0,
        "p05_abs_difference": float(np.percentile(differences, 5))
        if differences
        else 0.0,
        "duplicate_frames": duplicate_count,
    }


def black_frame_audit(path: Path) -> dict[str, object]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "info",
            "-i",
            str(path),
            "-vf",
            "blackdetect=d=0.100:pix_th=0.020",
            "-an",
            "-f",
            "null",
            "NUL",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    events = re.findall(r"black_start:[^\r\n]+", result.stderr)
    return {"black_event_count": len(events), "events": events}


def timeline_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def contact_sheet(
    path: Path, timeline_path: Path, output_path: Path
) -> dict[str, object]:
    rows = timeline_rows(timeline_path)
    indices = np.linspace(0, len(rows) - 1, min(12, len(rows))).round().astype(int)
    selected = [rows[int(index)] for index in indices]
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open rendered video: {path}")
    cells: list[np.ndarray] = []
    try:
        for number, row in enumerate(selected, start=1):
            time_seconds = (
                float(row["relative_start"]) + float(row["relative_end"])
            ) / 2.0
            capture.set(cv2.CAP_PROP_POS_MSEC, time_seconds * 1000.0)
            ok, frame = capture.read()
            if not ok:
                continue
            cell = cv2.resize(frame, (480, 270), interpolation=cv2.INTER_AREA)
            cv2.rectangle(cell, (0, 0), (479, 31), (5, 10, 15), thickness=-1)
            label = f"#{number:02d}  {format_timestamp(time_seconds)}"
            cv2.putText(
                cell,
                label,
                (12, 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (245, 245, 245),
                1,
                cv2.LINE_AA,
            )
            cells.append(cell)
    finally:
        capture.release()
    if not cells:
        raise RuntimeError(f"No contact sheet frames were decoded from {path}")
    blank = np.full_like(cells[0], 18)
    cells.extend(blank.copy() for _ in range(12 - len(cells)))
    sheet = np.vstack(
        [np.hstack(cells[index : index + 4]) for index in range(0, 12, 4)]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), sheet):
        raise RuntimeError(f"Could not write contact sheet: {output_path}")
    return {
        "path": str(output_path),
        "frames": len(selected),
        "width": 1920,
        "height": 810,
    }


def format_timestamp(seconds: float) -> str:
    minutes, remainder = divmod(seconds, 60.0)
    return f"{int(minutes):02d}:{remainder:06.3f}"


def passes_core_gate(report: dict[str, object]) -> bool:
    checks = report["checks"]
    audio = report["audio_alignment"]
    subtitles = report["subtitles"]
    motion = report["motion"]
    black_frames = report["black_frames"]
    return all(
        [
            abs(float(checks["duration_error_seconds"])) <= 0.080,
            bool(checks["has_video"]),
            bool(checks["has_audio"]),
            bool(checks["resolution_ok"]),
            bool(checks["fps_ok"]),
            bool(checks["audio_rate_ok"]),
            not bool(checks["dynamic_zoom"]),
            checks["image_correction"] == "none",
            max(float(item["absolute_lag_seconds"]) for item in audio) <= 0.040,
            min(float(item["normalized_correlation"]) for item in audio) >= 0.970,
            int(subtitles["overlap_count"]) == 0,
            int(subtitles["invalid_interval_count"]) == 0,
            not bool(motion["all_sampled_frames_identical"]),
            int(black_frames["black_event_count"]) == 0,
        ]
    )


def audit_one(render_summary_path: Path, source_audio: Path) -> dict[str, object]:
    render_summary = json.loads(render_summary_path.read_text(encoding="utf-8"))
    video = Path(render_summary["output"])
    expected_duration = float(render_summary["duration_seconds"])
    payload = probe(video)
    video_stream = next(
        (item for item in payload["streams"] if item["codec_type"] == "video"), None
    )
    audio_stream = next(
        (item for item in payload["streams"] if item["codec_type"] == "audio"), None
    )
    actual_duration = float(payload["format"]["duration"])
    audio_checks = [
        audio_alignment(
            source_audio, video, float(render_summary["clip_start_seconds"]), position
        )
        for position in sample_positions(expected_duration)
    ]
    report: dict[str, object] = {
        "video": str(video),
        "probe": payload,
        "checks": {
            "duration_error_seconds": actual_duration - expected_duration,
            "has_video": video_stream is not None,
            "has_audio": audio_stream is not None,
            "resolution_ok": video_stream is not None
            and [int(video_stream["width"]), int(video_stream["height"])]
            == [1920, 1080],
            "fps_ok": video_stream is not None
            and video_stream["avg_frame_rate"] == "60/1",
            "audio_rate_ok": audio_stream is not None
            and int(audio_stream["sample_rate"]) == 48_000,
            "dynamic_zoom": bool(render_summary["dynamic_zoom"]),
            "image_correction": render_summary["image_correction"],
            "max_pan_delta_per_frame_source_pixels": render_summary[
                "max_pan_delta_per_frame_source_pixels"
            ],
            "max_pan_acceleration_source_pixels": render_summary[
                "max_pan_acceleration_source_pixels"
            ],
        },
        "audio_alignment": audio_checks,
        "subtitles": subtitle_audit(
            Path(render_summary["subtitle_timeline"]), expected_duration
        ),
        "motion": frame_motion_audit(video, expected_duration),
        "black_frames": black_frame_audit(video),
        "contact_sheet": contact_sheet(
            video,
            Path(render_summary["subtitle_timeline"]),
            video.parent / "qc" / "contact_sheet_12_lyrics.png",
        ),
    }
    report["status"] = "pass" if passes_core_gate(report) else "fail"
    output_path = video.parent / "qc" / "qc_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a batch of rendered MV-Lite videos."
    )
    parser.add_argument("--batch-summary", type=Path, required=True)
    parser.add_argument("--source-audio", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    batch_path = args.batch_summary.resolve()
    source_audio = args.source_audio.resolve()
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    reports = [
        audit_one(Path(item["output"]).parent / "render_summary.json", source_audio)
        for item in batch["outputs"]
    ]
    payload = {
        "requested": len(reports),
        "passed": sum(report["status"] == "pass" for report in reports),
        "failed": sum(report["status"] != "pass" for report in reports),
        "reports": reports,
    }
    output = (
        args.output.resolve()
        if args.output
        else batch_path.parent / "batch_qc_summary.json"
    )
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
