#!/usr/bin/env python3
"""Generate deterministic visual-analysis artifacts for a reference-video range."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Required binary not found: {name}")
    return path


def probe_video(ffprobe: str, video: Path) -> dict:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(video),
        ]
    )
    return json.loads(result.stdout)


def media_duration(probe: dict) -> float:
    value = probe.get("format", {}).get("duration")
    if value is None:
        raise SystemExit("ffprobe did not report a media duration")
    return float(value)


def tile_rows(duration: float, fps: float, columns: int) -> int:
    return max(1, math.ceil(math.ceil(duration * fps) / columns))


def render_sheet(
    ffmpeg: str,
    video: Path,
    output: Path,
    start: float,
    duration: float,
    fps: float,
    columns: int,
    scale_width: int,
) -> None:
    rows = tile_rows(duration, fps, columns)
    filter_graph = (
        f"fps={fps},scale={scale_width}:-2,"
        f"tile={columns}x{rows}:padding=8:margin=8:color=white"
    )
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(start),
            "-t",
            str(duration),
            "-i",
            str(video),
            "-vf",
            filter_graph,
            "-frames:v",
            "1",
            str(output),
        ],
        check=True,
    )


def extract_scene_frames(
    ffmpeg: str,
    video: Path,
    output_pattern: Path,
    start: float,
    duration: float,
    threshold: float,
) -> None:
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(start),
            "-t",
            str(duration),
            "-i",
            str(video),
            "-vf",
            f"select=gt(scene\\,{threshold})",
            "-fps_mode",
            "vfr",
            str(output_pattern),
        ],
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create probe data, contact sheets, and scene frames for a video range."
    )
    parser.add_argument("video", type=Path, help="Local reference video")
    parser.add_argument("--start", type=float, default=0.0, help="Start time in seconds")
    parser.add_argument(
        "--duration", type=float, default=35.0, help="Analysis duration in seconds"
    )
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=0.16,
        help="FFmpeg scene-change threshold",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video = args.video.expanduser().resolve()
    output = args.out.expanduser().resolve()

    if not video.is_file():
        raise SystemExit(f"Reference video not found: {video}")
    if args.start < 0 or args.duration <= 0:
        raise SystemExit("--start must be >= 0 and --duration must be > 0")
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise SystemExit(f"Output path must be an empty directory: {output}")

    ffmpeg = require_binary("ffmpeg")
    ffprobe = require_binary("ffprobe")
    probe = probe_video(ffprobe, video)
    total_duration = media_duration(probe)
    if args.start >= total_duration:
        raise SystemExit("--start is beyond the media duration")
    duration = min(args.duration, total_duration - args.start)

    frames_dir = output / "scene-frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    overview = output / "overview-1fps.jpg"
    opening = output / "opening-4fps.jpg"
    render_sheet(ffmpeg, video, overview, args.start, duration, 1.0, 5, 384)

    opening_duration = min(8.0, duration)
    render_sheet(ffmpeg, video, opening, args.start, opening_duration, 4.0, 8, 320)

    outputs = {
        "overview_contact_sheet": str(overview),
        "opening_contact_sheet": str(opening),
    }

    if duration > 8.0:
        remainder = output / "remainder-2fps.jpg"
        render_sheet(
            ffmpeg,
            video,
            remainder,
            args.start + 8.0,
            duration - 8.0,
            2.0,
            9,
            320,
        )
        outputs["remainder_contact_sheet"] = str(remainder)

    extract_scene_frames(
        ffmpeg,
        video,
        frames_dir / "scene-%03d.png",
        args.start,
        duration,
        args.scene_threshold,
    )

    manifest = {
        "video": str(video),
        "start": args.start,
        "duration": duration,
        "scene_threshold": args.scene_threshold,
        "probe": probe,
        "outputs": outputs,
        "scene_frames": [str(path) for path in sorted(frames_dir.glob("scene-*.png"))],
    }
    manifest_path = output / "analysis.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps({"ok": True, "manifest": str(manifest_path), **outputs}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        if exc.stderr:
            print(exc.stderr.strip(), file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
