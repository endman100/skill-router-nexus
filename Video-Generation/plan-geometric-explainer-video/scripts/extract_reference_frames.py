#!/usr/bin/env python3
"""Extract source frames described by a small JSON manifest using FFmpeg."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def safe_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"output must be a safe relative path: {value}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract exact source frames from a timestamp manifest."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--quality", type=int, default=2)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ERROR: ffmpeg is not available on PATH", file=sys.stderr)
        return 2

    try:
        entries = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read manifest: {exc}", file=sys.stderr)
        return 2
    if not isinstance(entries, list):
        print("ERROR: manifest must be a JSON list", file=sys.stderr)
        return 2

    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    failures = 0

    for index, item in enumerate(entries, start=1):
        try:
            video = Path(item["video"]).resolve()
            seconds = float(item["seconds"])
            relative_output = safe_relative_path(item["output"])
        except (KeyError, TypeError, ValueError) as exc:
            print(f"ERROR: entry {index}: {exc}", file=sys.stderr)
            failures += 1
            continue
        if seconds < 0 or not video.is_file():
            print(f"ERROR: entry {index} has invalid video or timestamp", file=sys.stderr)
            failures += 1
            continue

        output = (output_root / relative_output).resolve()
        try:
            output.relative_to(output_root)
        except ValueError:
            print(f"ERROR: entry {index} output escapes output dir", file=sys.stderr)
            failures += 1
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and not args.overwrite:
            print(f"SKIP: {output}")
            continue

        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y" if args.overwrite else "-n",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-vf",
            f"scale={args.width}:-2:flags=lanczos",
            "-q:v",
            str(args.quality),
            str(output),
        ]
        result = subprocess.run(command, check=False)
        if result.returncode:
            print(f"ERROR: ffmpeg failed for entry {index}", file=sys.stderr)
            failures += 1
        else:
            print(f"OK: {output}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
