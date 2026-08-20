from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGES = (
    "media_preparation",
    "asr",
    "music_detection",
    "song_discovery",
    "phrase_labeling",
    "interval_construction",
    "start_refinement",
    "end_refinement",
    "precision_cutting",
    "clip_verification",
)

DEFAULTS: dict[str, Any] = {
    "media_preparation": {
        "audio_sample_rate": 16000,
        "audio_channels": 1,
        "waveform_bucket_seconds": 0.02,
        "master_mode": "link_with_copy_fallback",
    },
    "asr": {
        "router": "asr-router",
        "profile": "word_timestamps",
        "preferred_provider": "qwen3",
        "fallback_allowed": False,
    },
    "music_detection": {
        "model": "lab260/MusicDetection",
        "window_seconds": 3.0,
        "hop_seconds": 1.0,
        "threshold": 0.5,
    },
    "codex": {
        "model": "gpt-5.6-terra",
        "service_tier": "default",
        "song_discovery_reasoning": "high",
        "phrase_labeling_reasoning": "medium",
        "song_discovery_window_seconds": 180.0,
        "windows_per_batch": 4,
        "phrase_batch_size": 80,
    },
    "intervals": {
        "same_label_pause_seconds": 15.0,
        "music_continuity_threshold": 0.5,
        "music_continuity_mean_threshold": 0.6,
        "max_music_interrupt_seconds": 2.0,
        "min_song_duration_seconds": 30.0,
        "min_song_phrase_rows": 3,
        "min_mean_music_probability": 0.6,
    },
    "start_boundary": {
        "search_seconds": 60.0,
        "music_threshold": 0.5,
        "max_music_gap_seconds": 2.0,
        "min_music_run_seconds": 4.0,
        "lyric_tolerance_seconds": 5.0,
        "asr_lookback_seconds": 15.0,
        "asr_cluster_gap_seconds": 3.0,
        "asr_padding_seconds": 0.3,
        "max_anchor_distance_seconds": 5.0,
        "rms_smoothing_seconds": 0.4,
        "low_volume_percentile": 35.0,
    },
    "end_boundary": {
        "deterministic_search_seconds": 30.0,
        "stable_non_music_seconds": 2.0,
        "ranker_search_seconds": 90.0,
        "candidate_step_seconds": 0.25,
        "ranker_requires_generalization_evidence": True,
    },
    "cutting": {
        "encoder": "auto",
        "duration_tolerance_seconds": 0.15,
        "upscale_allowed": False,
    },
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def initialize(path: Path, source: str) -> dict[str, Any]:
    timestamp = now()
    payload = {
        "schema_version": 1,
        "workflow": "skill-song-stream-clipper",
        "created_at": timestamp,
        "updated_at": timestamp,
        "source": source,
        "evidence_policy": {
            "youtube_comments_allowed": False,
            "youtube_chapters_allowed": False,
            "youtube_description_allowed_for_recognition": False,
            "song_titles_from_sung_lyrics_only": True,
        },
        "defaults": DEFAULTS,
        "stages": {
            stage: {
                "status": "pending",
                "commands": [],
                "inputs": [],
                "outputs": [],
                "notes": [],
                "updated_at": timestamp,
            }
            for stage in STAGES
        },
    }
    write_manifest(path, payload)
    return payload


def unique_extend(target: list[str], values: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def record(
    path: Path,
    stage: str,
    status: str,
    commands: list[str],
    inputs: list[str],
    outputs: list[str],
    notes: list[str],
) -> dict[str, Any]:
    payload = read_manifest(path)
    if stage not in payload.get("stages", {}):
        raise ValueError(f"Unknown stage: {stage}")
    entry = payload["stages"][stage]
    entry["status"] = status
    unique_extend(entry["commands"], commands)
    unique_extend(entry["inputs"], inputs)
    unique_extend(entry["outputs"], outputs)
    unique_extend(entry["notes"], notes)
    entry["updated_at"] = now()
    payload["updated_at"] = entry["updated_at"]
    write_manifest(path, payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and update a song-stream clipping run manifest."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--manifest", type=Path, required=True)
    init_parser.add_argument("--source", required=True)
    init_parser.add_argument("--force", action="store_true")

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--manifest", type=Path, required=True)
    record_parser.add_argument("--stage", choices=STAGES, required=True)
    record_parser.add_argument(
        "--status",
        choices=("pending", "running", "completed", "failed", "skipped"),
        required=True,
    )
    record_parser.add_argument("--command", action="append", default=[])
    record_parser.add_argument("--input", action="append", default=[])
    record_parser.add_argument("--output", action="append", default=[])
    record_parser.add_argument("--note", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    path = args.manifest.resolve()
    if args.action == "init":
        if path.exists() and not args.force:
            raise FileExistsError(f"Manifest already exists: {path}")
        initialize(path, args.source)
    else:
        if not path.is_file():
            raise FileNotFoundError(path)
        record(
            path,
            args.stage,
            args.status,
            args.command,
            args.input,
            args.output,
            args.note,
        )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
