from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Columns:
    interval: str
    title: str
    start: str
    end: str


@dataclass(frozen=True)
class ClipSpec:
    interval_no: int
    title: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start

    @classmethod
    def from_row(cls, row: dict[str, str], columns: Columns) -> "ClipSpec":
        try:
            spec = cls(
                interval_no=int(row[columns.interval]),
                title=row[columns.title].strip(),
                start=float(row[columns.start]),
                end=float(row[columns.end]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid interval row: {row}") from exc
        if not spec.title:
            raise ValueError(f"Empty title for interval {spec.interval_no}")
        if spec.start < 0 or spec.duration <= 0:
            raise ValueError(f"Invalid timing for interval {spec.interval_no}")
        return spec


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Cannot write an empty clip manifest")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def safe_filename(value: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip()
    safe = re.sub(r"\s+", "_", safe)
    safe = re.sub(r"_+", "_", safe)
    return safe.rstrip(". ") or "untitled"


def filename_timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}h{minutes:02d}m{whole_seconds:02d}s{millis:03d}"


def run_process(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe(path: Path) -> dict[str, Any]:
    result = run_process(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size",
            "-show_entries",
            "stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            str(path),
        ]
    )
    if result.returncode:
        return {"ok": False, "error": result.stdout[-2000:]}
    try:
        return {"ok": True, **json.loads(result.stdout)}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": str(exc)}


def source_duration(path: Path) -> float:
    media = probe(path)
    if not media.get("ok"):
        raise RuntimeError(f"ffprobe failed for source video: {media.get('error', '')}")
    streams = media.get("streams", [])
    types = {stream.get("codec_type") for stream in streams}
    if not {"audio", "video"}.issubset(types):
        raise ValueError("Source must contain both audio and video streams")
    return float(media["format"]["duration"])


def validate_specs(specs: list[ClipSpec], duration: float, tolerance: float) -> None:
    if not specs:
        raise ValueError("Intervals CSV contains no rows")
    numbers = [spec.interval_no for spec in specs]
    if len(numbers) != len(set(numbers)):
        raise ValueError("Duplicate interval_no values")
    for spec in specs:
        if spec.end > duration + tolerance:
            raise ValueError(
                f"Interval {spec.interval_no} ends at {spec.end:.3f}s, "
                f"after source duration {duration:.3f}s"
            )


def encoder_options(encoder: str) -> list[str]:
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "25", "-b:v", "0"]
    if encoder == "libx264":
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
    raise ValueError(f"Unsupported encoder: {encoder}")


def build_ffmpeg_command(
    *, video: Path, output: Path, spec: ClipSpec, encoder: str
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-ss",
        f"{spec.start:.3f}",
        "-i",
        str(video),
        "-t",
        f"{spec.duration:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        *encoder_options(encoder),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-avoid_negative_ts",
        "make_zero",
        str(output),
    ]


def output_path(output_dir: Path, spec: ClipSpec) -> Path:
    stem = (
        f"{spec.interval_no:02d}_{safe_filename(spec.title)}_"
        f"{filename_timestamp(spec.start)}_{filename_timestamp(spec.end)}"
    )
    return output_dir / f"{stem}.mp4"


def cut_one(
    *,
    video: Path,
    output_dir: Path,
    spec: ClipSpec,
    requested_encoder: str,
    force: bool,
    tolerance: float,
) -> dict[str, Any]:
    output = output_path(output_dir, spec)
    log_path = output.with_suffix(".ffmpeg.log")
    encoder_order = (
        ["h264_nvenc", "libx264"] if requested_encoder == "auto" else [requested_encoder]
    )
    used_encoder = "existing"
    encode_ok = output.exists() and not force
    log_parts: list[str] = []

    if not encode_ok:
        for encoder in encoder_order:
            result = run_process(
                build_ffmpeg_command(
                    video=video,
                    output=output,
                    spec=spec,
                    encoder=encoder,
                )
            )
            log_parts.append(f"===== encoder={encoder} exit={result.returncode} =====\n{result.stdout}")
            if result.returncode == 0 and output.exists():
                used_encoder = encoder
                encode_ok = True
                break
        log_path.write_text("\n".join(log_parts), encoding="utf-8")

    media = probe(output) if encode_ok else {"ok": False}
    streams = media.get("streams", [])
    stream_types = {stream.get("codec_type") for stream in streams}
    actual_duration = (
        float(media.get("format", {}).get("duration", 0.0)) if media.get("ok") else 0.0
    )
    duration_error = abs(actual_duration - spec.duration)
    verified = bool(
        encode_ok
        and media.get("ok")
        and "video" in stream_types
        and "audio" in stream_types
        and duration_error <= tolerance
    )
    return {
        "interval_no": spec.interval_no,
        "title": spec.title,
        "start_seconds": f"{spec.start:.3f}",
        "end_seconds": f"{spec.end:.3f}",
        "expected_duration_seconds": f"{spec.duration:.3f}",
        "actual_duration_seconds": f"{actual_duration:.3f}",
        "duration_error_seconds": f"{duration_error:.3f}",
        "has_video": "video" in stream_types,
        "has_audio": "audio" in stream_types,
        "width": next(
            (
                stream.get("width", "")
                for stream in streams
                if stream.get("codec_type") == "video"
            ),
            "",
        ),
        "height": next(
            (
                stream.get("height", "")
                for stream in streams
                if stream.get("codec_type") == "video"
            ),
            "",
        ),
        "encoder": used_encoder,
        "status": "verified" if verified else "failed_verification",
        "path": str(output.resolve()),
        "log_path": str(log_path.resolve()),
    }


def write_gallery(output_dir: Path, manifest: list[dict[str, Any]]) -> None:
    lines = ["# Song stream clips", ""]
    for row in manifest:
        media_path = Path(row["path"]).as_posix()
        lines.extend(
            [
                f"## {int(row['interval_no']):02d}. {row['title']}",
                "",
                f"`{row['start_seconds']}` - `{row['end_seconds']}` | `{row['status']}`",
                "",
                f"![{row['title']}]({media_path})",
                "",
            ]
        )
    (output_dir / "review_gallery.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Frame-accurately cut and ffprobe-verify one MP4 per song interval."
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--intervals", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--interval-column", default="interval_no")
    parser.add_argument("--title-column", default="song_label")
    parser.add_argument("--start-column", default="cut_start_seconds")
    parser.add_argument("--end-column", default="cut_end_seconds")
    parser.add_argument("--encoder", choices=("auto", "h264_nvenc", "libx264"), default="auto")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--duration-tolerance", type=float, default=0.15)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for executable in ("ffmpeg", "ffprobe"):
        if not shutil.which(executable):
            raise FileNotFoundError(f"Required executable not found on PATH: {executable}")

    video = args.video.resolve()
    intervals = args.intervals.resolve()
    if not video.is_file():
        raise FileNotFoundError(video)
    if not intervals.is_file():
        raise FileNotFoundError(intervals)
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    if args.duration_tolerance < 0:
        raise ValueError("--duration-tolerance must be non-negative")

    columns = Columns(
        interval=args.interval_column,
        title=args.title_column,
        start=args.start_column,
        end=args.end_column,
    )
    specs = [ClipSpec.from_row(row, columns) for row in read_csv(intervals)]
    specs.sort(key=lambda spec: spec.interval_no)
    validate_specs(specs, source_duration(video), args.duration_tolerance)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                cut_one,
                video=video,
                output_dir=output_dir,
                spec=spec,
                requested_encoder=args.encoder,
                force=args.force,
                tolerance=args.duration_tolerance,
            ): spec
            for spec in specs
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            manifest.append(row)
            print(
                f"[{completed:02d}/{len(specs):02d}] {row['title']} "
                f"{row['actual_duration_seconds']}s {row['status']}",
                flush=True,
            )

    manifest.sort(key=lambda row: int(row["interval_no"]))
    write_csv(output_dir / "clip_manifest.csv", manifest)
    write_gallery(output_dir, manifest)
    verified_count = sum(row["status"] == "verified" for row in manifest)
    max_error = max(float(row["duration_error_seconds"]) for row in manifest)
    summary = {
        "requested": len(manifest),
        "verified": verified_count,
        "maximum_duration_error_seconds": max_error,
        "source_video": str(video),
        "intervals_csv": str(intervals),
        "output_dir": str(output_dir),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"verified={verified_count}/{len(manifest)} max_error={max_error:.3f}s")
    print(output_dir / "clip_manifest.csv")
    return 0 if verified_count == len(manifest) else 3


if __name__ == "__main__":
    raise SystemExit(main())
