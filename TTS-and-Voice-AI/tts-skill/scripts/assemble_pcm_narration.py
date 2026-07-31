#!/usr/bin/env python3
"""Assemble pause-unit WAVs using canonical narration.json pause values."""

from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "references" / "fish-s2-default-voice.json"
NARRATION_KEYS = ["text", "pause_after_ms"]


def seconds_to_frames(seconds: float, sample_rate: int) -> int:
    return round(seconds * sample_rate)


def frames_to_seconds(frames: int, sample_rate: int) -> float:
    return frames / sample_rate


def silence_bytes(frames: int, channels: int, sample_width: int) -> bytes:
    return b"\x00" * frames * channels * sample_width


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lead_in(profile_path: Path) -> float:
    profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    policy = profile.get("pause_policy", {})
    if policy.get("production_pause_authority") != "narration.json[].pause_after_ms":
        raise ValueError("profile must declare narration.json[].pause_after_ms as pause authority")
    if policy.get("production_gap_defaults_allowed") is not False:
        raise ValueError("profile gap defaults must be disabled for production")
    value = policy.get("lead_in_seconds")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError("profile pause_policy.lead_in_seconds must be non-negative")
    return float(value)


def load_narration(path: Path) -> list[dict[str, Any]]:
    narration = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(narration, list) or not narration:
        raise ValueError("narration must be a non-empty array")
    for index, item in enumerate(narration, start=1):
        if not isinstance(item, dict) or list(item) != NARRATION_KEYS:
            raise ValueError(
                f"narration unit {index} must contain exactly {NARRATION_KEYS} in that order"
            )
        if not isinstance(item["text"], str) or not item["text"].strip():
            raise ValueError(f"narration unit {index}.text must be non-empty")
        pause_ms = item["pause_after_ms"]
        if not isinstance(pause_ms, int) or isinstance(pause_ms, bool) or pause_ms <= 0:
            raise ValueError(
                f"narration unit {index}.pause_after_ms must be a positive integer"
            )
    return narration


def load_pacing_overrides(
    path: Path | None, unit_count: int
) -> tuple[dict[int, int], dict[int, str], dict[str, Any] | None]:
    if path is None:
        return {}, {}, None
    resolved_path = path.resolve()
    data = json.loads(resolved_path.read_text(encoding="utf-8-sig"))
    if data.get("schema_version") != 1 or data.get("policy") != "minimum-plus-editorial-extra":
        raise ValueError(
            "pacing overrides must use schema 1 and minimum-plus-editorial-extra"
        )
    maximum = data.get("max_extra_pause_ms", 1200)
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0:
        raise ValueError("max_extra_pause_ms must be a non-negative integer")
    extras: dict[int, int] = {}
    reasons: dict[int, str] = {}
    for record in data.get("units", []):
        if not isinstance(record, dict) or list(record) != [
            "unit_index",
            "extra_pause_ms",
            "reason",
        ]:
            raise ValueError(
                "each pacing override must contain unit_index, extra_pause_ms, reason"
            )
        unit_index = record["unit_index"]
        extra_pause_ms = record["extra_pause_ms"]
        reason = record["reason"]
        if (
            not isinstance(unit_index, int)
            or isinstance(unit_index, bool)
            or not 1 <= unit_index <= unit_count
            or unit_index in extras
        ):
            raise ValueError(f"invalid or duplicate pacing unit_index: {unit_index}")
        if (
            not isinstance(extra_pause_ms, int)
            or isinstance(extra_pause_ms, bool)
            or not 0 <= extra_pause_ms <= maximum
        ):
            raise ValueError(f"invalid extra_pause_ms for unit {unit_index}")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"unit {unit_index} requires a pacing reason")
        extras[unit_index] = extra_pause_ms
        reasons[unit_index] = reason
    return (
        extras,
        reasons,
        {
            "path": str(resolved_path),
            "sha256": file_sha256(resolved_path),
            "policy": data["policy"],
            "max_extra_pause_ms": maximum,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Join pause-unit PCM WAVs using narration.json as the only pause authority."
    )
    parser.add_argument("--narration", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timing-output", required=True, type=Path)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument(
        "--pacing-overrides",
        type=Path,
        help="Optional non-negative editorial pause additions above canonical minima",
    )
    args = parser.parse_args()

    narration_path = args.narration.resolve()
    manifest_path = args.manifest.resolve()
    profile_path = args.profile.resolve()
    output_path = args.output.resolve()
    timing_path = args.timing_output.resolve()
    narration = load_narration(narration_path)
    extras, reasons, pacing_metadata = load_pacing_overrides(
        args.pacing_overrides, len(narration)
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    segments = manifest.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("manifest.segments must be a non-empty array")
    if len(segments) != len(narration):
        raise ValueError(
            f"manifest has {len(segments)} segments but narration has {len(narration)} units"
        )

    sample_rate = 44100
    channels = 1
    sample_width = 2
    resolved: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for position, record in enumerate(segments, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"segment {position} must be an object")
        if "pause_after_ms" in record:
            raise ValueError(
                f"segment {position} duplicates pause_after_ms; keep pauses only in narration.json"
            )
        segment_id = record.get("id")
        unit_index = record.get("unit_index")
        relative_path = record.get("path")
        page_id = record.get("page_id")
        if not isinstance(segment_id, str) or not segment_id or segment_id in seen_ids:
            raise ValueError(f"segment {position}.id is missing or duplicated")
        if unit_index != position:
            raise ValueError(
                f"segment {segment_id}.unit_index must be contiguous and equal {position}"
            )
        if not isinstance(relative_path, str) or not relative_path:
            raise ValueError(f"segment {segment_id}.path is missing")
        if page_id is not None and (not isinstance(page_id, str) or not page_id):
            raise ValueError(f"segment {segment_id}.page_id must be a non-empty string")
        seen_ids.add(segment_id)

        source = (manifest_path.parent / relative_path).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"segment WAV is missing: {source}")
        with wave.open(str(source), "rb") as wav:
            if wav.getnchannels() != channels:
                raise ValueError(f"{segment_id} must be mono")
            if wav.getframerate() != sample_rate:
                raise ValueError(f"{segment_id} must be 44.1 kHz")
            if wav.getsampwidth() != sample_width:
                raise ValueError(f"{segment_id} must be 16-bit PCM")
            if wav.getcomptype() != "NONE":
                raise ValueError(f"{segment_id} must be uncompressed PCM")
            frame_count = wav.getnframes()
            frames = wav.readframes(frame_count)
        resolved.append(
            {
                "id": segment_id,
                "unit_index": unit_index,
                "page_id": page_id,
                "source": source,
                "frame_count": frame_count,
                "frames": frames,
                "required_pause_after_ms": narration[position - 1]["pause_after_ms"],
                "extra_pause_ms": extras.get(position, 0),
                "effective_pause_after_ms": narration[position - 1]["pause_after_ms"]
                + extras.get(position, 0),
                "pacing_reason": reasons.get(position),
            }
        )

    lead_in_seconds = load_lead_in(profile_path)
    lead_frames = seconds_to_frames(lead_in_seconds, sample_rate)
    current_frame = 0
    timing_segments: list[dict[str, Any]] = []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timing_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(output_path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(sample_width)
        output.setframerate(sample_rate)
        output.writeframes(silence_bytes(lead_frames, channels, sample_width))
        current_frame += lead_frames

        for index, segment in enumerate(resolved):
            start_frame = current_frame
            output.writeframes(segment["frames"])
            current_frame += segment["frame_count"]
            end_frame = current_frame

            next_segment = resolved[index + 1] if index + 1 < len(resolved) else None
            if next_segment is None:
                pause_kind = "tail"
            elif segment["page_id"] and next_segment["page_id"] != segment["page_id"]:
                pause_kind = "page"
            else:
                pause_kind = "pause"
            pause_frames = round(
                segment["effective_pause_after_ms"] * sample_rate / 1000
            )
            pause_start_frame = current_frame
            output.writeframes(silence_bytes(pause_frames, channels, sample_width))
            current_frame += pause_frames
            pause_end_frame = current_frame

            timing_record: dict[str, Any] = {
                "id": segment["id"],
                "unit_index": segment["unit_index"],
                "source": str(segment["source"]),
                "start_seconds": frames_to_seconds(start_frame, sample_rate),
                "end_seconds": frames_to_seconds(end_frame, sample_rate),
                "pause_after": {
                    "kind": pause_kind,
                    "source_pause_after_ms": segment["required_pause_after_ms"],
                    "required_pause_after_ms": segment["required_pause_after_ms"],
                    "extra_pause_ms": segment["extra_pause_ms"],
                    "effective_pause_after_ms": segment["effective_pause_after_ms"],
                    "pacing_reason": segment["pacing_reason"],
                    "start_seconds": frames_to_seconds(pause_start_frame, sample_rate),
                    "end_seconds": frames_to_seconds(pause_end_frame, sample_rate),
                    "duration_seconds": frames_to_seconds(pause_frames, sample_rate),
                },
            }
            if segment["page_id"]:
                timing_record["page_id"] = segment["page_id"]
            timing_segments.append(timing_record)

    output_hash = file_sha256(output_path)
    timing = {
        "schema_version": 2,
        "source_narration": str(narration_path),
        "source_narration_sha256": file_sha256(narration_path),
        "source_manifest": str(manifest_path),
        "profile": str(profile_path),
        "output_audio": str(output_path),
        "output_sha256": output_hash,
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "duration_seconds": frames_to_seconds(current_frame, sample_rate),
        "lead_in": {
            "start_seconds": 0.0,
            "end_seconds": frames_to_seconds(lead_frames, sample_rate),
            "duration_seconds": frames_to_seconds(lead_frames, sample_rate),
        },
        "pause_policy": {
            "source_field": "narration.json[].pause_after_ms-minimum-plus-pacing-overrides",
            "profile_gap_defaults_used": False,
            "pacing_overrides": pacing_metadata,
            "total_extra_pause_ms": sum(extras.values()),
        },
        "segments": timing_segments,
    }
    timing_path.write_text(
        json.dumps(timing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[PASS] assembled {len(timing_segments)} pause-unit segments")
    print("[PASS] pause authority: narration.json[].pause_after_ms minimum plus editorial extras")
    print("[PASS] profile gap defaults used: false")
    print(f"[PASS] duration: {timing['duration_seconds']:.6f}s")
    print(f"[PASS] SHA-256: {output_hash}")
    print(f"[PASS] timing: {timing_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
