#!/usr/bin/env python3
"""Extract exact review frames from the rendered delivery MP4.

Use the delivered video as the evidence source instead of independently rendering
stills in a reused browser session. This prevents font- or browser-state drift from
making the QC evidence differ from the actual MP4.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_frame(
    records: dict[int, dict[str, Any]],
    frame: int,
    label: str,
    category: str,
    scene_id: str,
    cue: str | None = None,
) -> None:
    safe_frame = max(0, round(frame))
    record = records.setdefault(
        safe_frame,
        {
            "frame": safe_frame,
            "seconds": None,
            "labels": [],
            "categories": [],
            "scenes": [],
            "cues": [],
        },
    )
    record["labels"].append(label)
    record["categories"].append(category)
    record["scenes"].append(scene_id)
    if cue:
        record["cues"].append(cue)


def probe_video(path: Path) -> dict[str, Any]:
    payload = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "format=duration:stream=width,height,r_frame_rate",
                "-of",
                "json",
                str(path),
            ],
            text=True,
            encoding="utf-8",
        )
    )
    stream = payload["streams"][0]
    numerator, denominator = stream["r_frame_rate"].split("/", 1)
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": float(numerator) / float(denominator),
        "duration": float(payload["format"]["duration"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--timing", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--project-root", default=Path("."), type=Path)
    parser.add_argument("--fps", default=30, type=int)
    parser.add_argument("--width", default=540, type=int)
    parser.add_argument("--visual-lead-seconds", default=0.30, type=float)
    parser.add_argument("--after-frames", default=12, type=int)
    parser.add_argument("--batch-size", default=40, type=int)
    args = parser.parse_args()

    if not args.video.is_file():
        raise SystemExit(f"Video does not exist: {args.video}")
    if min(args.fps, args.width, args.after_frames, args.batch_size) < 1:
        raise SystemExit("fps, width, after-frames, and batch-size must be positive")
    if args.visual_lead_seconds < 0:
        raise SystemExit("visual-lead-seconds must be non-negative")

    video_info = probe_video(args.video)
    if abs(video_info["fps"] - args.fps) > 0.001:
        raise SystemExit(
            f"Video fps {video_info['fps']:.6f} does not match requested {args.fps}"
        )

    timing = json.loads(args.timing.read_text(encoding="utf-8"))
    scenes = timing.get("scenes")
    captions = timing.get("captions")
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("Timing JSON must contain a non-empty scenes array")
    if not isinstance(captions, list) or not captions:
        raise SystemExit("Timing JSON must contain a non-empty captions array")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for old_output in args.output_dir.iterdir():
        if old_output.is_file() and re.fullmatch(
            r"batch-\d{2}-\d{3}\.png", old_output.name
        ):
            old_output.unlink()

    records: dict[int, dict[str, Any]] = {}
    scenes_by_id: dict[str, dict[str, Any]] = {}
    for scene in scenes:
        scene_id = str(scene["id"])
        scenes_by_id[scene_id] = scene
        start = float(scene["start"])
        end = float(scene["end"])
        speech_start = float(scene.get("speechStart", scene.get("speech_start", start)))
        speech_end = float(scene.get("speechEnd", scene.get("speech_end", end)))
        hold = scene.get("completedPageHold", scene.get("completed_page_hold"))
        if not isinstance(hold, list) or len(hold) != 2:
            hold = [max(start, end - 0.2), end]

        entry_frame = round(start * args.fps) + 2
        midpoint_frame = round(((speech_start + speech_end) / 2) * args.fps)
        final_hold_frame = max(
            entry_frame, round(((float(hold[0]) + float(hold[1])) / 2) * args.fps)
        )
        add_frame(records, entry_frame, f"scene-{scene_id}-entry", "representative", scene_id)
        add_frame(records, midpoint_frame, f"scene-{scene_id}-mid", "representative", scene_id)
        add_frame(records, final_hold_frame, f"scene-{scene_id}-final-hold", "representative", scene_id)

        visual_cues = scene.get("visualCues", scene.get("visual_cues", {}))
        for name, seconds in visual_cues.items():
            cue_frame = round(float(seconds) * args.fps)
            add_frame(records, cue_frame - 1, f"scene-{scene_id}-{name}-visual-before", "visual-cue-boundary", scene_id, name)
            add_frame(records, cue_frame + 2, f"scene-{scene_id}-{name}-visual-after", "visual-cue-boundary", scene_id, name)

        for name, seconds in scene.get("cues", {}).items():
            if name == "page_enter":
                continue
            cue_frame = round(float(seconds) * args.fps)
            add_frame(records, cue_frame - 1, f"scene-{scene_id}-{name}-canonical-before", "canonical-cue-boundary", scene_id, name)
            add_frame(records, cue_frame + 2, f"scene-{scene_id}-{name}-canonical-after", "canonical-cue-boundary", scene_id, name)

    for caption in captions:
        sentence_id = str(caption.get("sentence_id", caption.get("id", "")))
        scene_id = str(caption.get("page_id", caption.get("scene_id", "")))
        if not sentence_id or scene_id not in scenes_by_id:
            raise SystemExit(f"Caption has an invalid sentence or scene ID: {caption}")
        scene = scenes_by_id[scene_id]
        explicit_visual_start = caption.get(
            "visual_start", caption.get("visualStart", caption.get("visual_time"))
        )
        if explicit_visual_start is None:
            animation_start = max(
                float(scene["start"]),
                float(caption["start"]) - args.visual_lead_seconds,
            )
        else:
            animation_start = float(explicit_visual_start)
        cue_frame = round(animation_start * args.fps)
        add_frame(
            records,
            cue_frame - 1,
            f"scene-{scene_id}-sentence-{sentence_id}-before",
            "sentence-animation-boundary",
            scene_id,
            sentence_id,
        )
        add_frame(
            records,
            cue_frame + args.after_frames,
            f"scene-{scene_id}-sentence-{sentence_id}-after",
            "sentence-animation-boundary",
            scene_id,
            sentence_id,
        )

    ordered = [records[frame] for frame in sorted(records)]
    for record in ordered:
        record["seconds"] = record["frame"] / args.fps
    if ordered[-1]["seconds"] >= video_info["duration"]:
        raise SystemExit("Requested review frame exceeds the delivered video duration")

    try:
        relative_dir = args.output_dir.resolve().relative_to(
            args.project_root.resolve()
        )
    except ValueError as error:
        raise SystemExit("output-dir must be inside project-root") from error

    extracted: list[Path] = []
    for batch_index, offset in enumerate(range(0, len(ordered), args.batch_size)):
        batch = ordered[offset : offset + args.batch_size]
        selection = "+".join(f"eq(n\\,{record['frame']})" for record in batch)
        output_pattern = args.output_dir / f"batch-{batch_index:02d}-%03d.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(args.video),
                "-vf",
                f"select={selection},scale={args.width}:-2:flags=lanczos",
                "-fps_mode",
                "vfr",
                str(output_pattern),
            ],
            check=True,
        )
        batch_outputs = [
            args.output_dir / f"batch-{batch_index:02d}-{item_index:03d}.png"
            for item_index in range(1, len(batch) + 1)
        ]
        missing = [path for path in batch_outputs if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing extracted frames: {missing}")
        extracted.extend(batch_outputs)

    for record, output in zip(ordered, extracted, strict=True):
        record["file"] = (relative_dir / output.name).as_posix()
        record["sha256"] = sha256(output)

    manifest = {
        "schema_version": 1,
        "composition": timing.get("composition", "delivery-video"),
        "evidence_source": "decoded-delivery-video-exact-frame-selection",
        "video": args.video.as_posix(),
        "video_sha256": sha256(args.video),
        "video_probe": video_info,
        "fps": args.fps,
        "visual_lead_seconds_fallback": args.visual_lead_seconds,
        "after_frames": args.after_frames,
        "audio_sha256": timing.get("audioSha256", timing.get("audio_sha256")),
        "timing_source": timing.get("timingSource", timing.get("timing_source")),
        "frame_count": len(ordered),
        "sentence_animation_count": len(captions),
        "records": ordered,
    }
    manifest_path = args.output_dir / "stills-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[PASS] decoded {len(ordered)} exact review frames from {args.video}")
    print(f"[PASS] manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
