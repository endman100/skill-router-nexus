#!/usr/bin/env python3
"""Build deterministic per-scene filmstrips from a rendered review MP4."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--timing", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--fps", default=2, type=int)
    parser.add_argument("--columns", default=6, type=int)
    parser.add_argument("--tile-width", default=180, type=int)
    parser.add_argument("--tile-height", default=320, type=int)
    args = parser.parse_args()

    if args.fps < 2:
        raise SystemExit("Review sampling must be at least 2 fps")
    if min(args.columns, args.tile_width, args.tile_height) < 1:
        raise SystemExit("columns and tile dimensions must be positive")
    if not args.video.is_file():
        raise SystemExit(f"Video does not exist: {args.video}")

    timing = json.loads(args.timing.read_text(encoding="utf-8"))
    scenes = timing.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("Timing JSON must contain a non-empty scenes array")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for scene in scenes:
        scene_id = str(scene["id"])
        start = float(scene["start"])
        end = float(scene["end"])
        duration = end - start
        if duration <= 0:
            raise SystemExit(f"Scene {scene_id} has a non-positive duration")

        expected_frames = max(1, math.ceil(duration * args.fps))
        rows = math.ceil(expected_frames / args.columns)
        output = args.output_dir / f"scene-{scene_id}-{args.fps}fps.jpg"
        filtergraph = (
            f"fps={args.fps},"
            f"scale={args.tile_width}:{args.tile_height}:flags=lanczos,"
            f"tile={args.columns}x{rows}:padding=3:margin=3"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{start:.6f}",
                "-t",
                f"{duration:.6f}",
                "-i",
                str(args.video),
                "-vf",
                filtergraph,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(output),
            ],
            check=True,
        )
        records.append(
            {
                "scene_id": scene_id,
                "range_seconds": [start, end],
                "sample_rate_fps": args.fps,
                "expected_sample_count": expected_frames,
                "grid": {"columns": args.columns, "rows": rows},
                "path": output.as_posix(),
                "sha256": sha256(output),
            }
        )
        print(f"[PASS] scene {scene_id}: {expected_frames} samples -> {output}")

    manifest = {
        "schema_version": 1,
        "review_method": "decoded-contiguous-scene-filmstrips",
        "video": args.video.as_posix(),
        "video_sha256": sha256(args.video),
        "sample_rate_fps": args.fps,
        "coverage_seconds": [float(scenes[0]["start"]), float(scenes[-1]["end"])],
        "filmstrips": records,
    }
    manifest_path = args.output_dir / "filmstrip-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[PASS] manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
