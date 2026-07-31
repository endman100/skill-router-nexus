#!/usr/bin/env python3
"""Derive production IDs, scene metadata, and TTS aliases from minimal narration."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


NARRATION_KEYS = ["text", "pause_after_ms"]
SCENE_KEYS = ["page_id", "chapter", "caption", "start_unit", "end_unit"]
OVERRIDE_KEYS = ["unit_index", "tts_text"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require_minimal_narration(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("narration must be a non-empty array")
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict) or list(item) != NARRATION_KEYS:
            raise ValueError(
                f"narration unit {index} must contain exactly {NARRATION_KEYS} in that order"
            )
        if not isinstance(item["text"], str) or not item["text"].strip():
            raise ValueError(f"narration unit {index}.text must be non-empty")
        pause = item["pause_after_ms"]
        if not isinstance(pause, int) or isinstance(pause, bool) or pause <= 0:
            raise ValueError(f"narration unit {index}.pause_after_ms must be a positive integer")
    return value


def require_scenes(value: Any, unit_count: int) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("scenes must be a non-empty array")
    expected_start = 1
    seen_pages: set[str] = set()
    for index, scene in enumerate(value, start=1):
        if not isinstance(scene, dict) or list(scene) != SCENE_KEYS:
            raise ValueError(f"scene {index} must contain exactly {SCENE_KEYS} in that order")
        page_id = scene["page_id"]
        if not isinstance(page_id, str) or not page_id or page_id in seen_pages:
            raise ValueError(f"scene {index}.page_id must be a unique non-empty string")
        seen_pages.add(page_id)
        for field in ("chapter", "caption"):
            if not isinstance(scene[field], str) or not scene[field].strip():
                raise ValueError(f"scene {index}.{field} must be a non-empty string")
        start = scene["start_unit"]
        end = scene["end_unit"]
        if not isinstance(start, int) or isinstance(start, bool):
            raise ValueError(f"scene {index}.start_unit must be an integer")
        if not isinstance(end, int) or isinstance(end, bool):
            raise ValueError(f"scene {index}.end_unit must be an integer")
        if start != expected_start or end < start or end > unit_count:
            raise ValueError(
                f"scene {index} must cover a contiguous range beginning at unit {expected_start}"
            )
        expected_start = end + 1
    if expected_start != unit_count + 1:
        raise ValueError(f"scenes must cover all {unit_count} narration units exactly once")
    return value


def require_overrides(value: Any, unit_count: int) -> dict[int, str]:
    if not isinstance(value, list):
        raise ValueError("pronunciation overrides must be an array")
    overrides: dict[int, str] = {}
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict) or list(item) != OVERRIDE_KEYS:
            raise ValueError(f"override {index} must contain exactly {OVERRIDE_KEYS} in that order")
        unit_index = item["unit_index"]
        tts_text = item["tts_text"]
        if (
            not isinstance(unit_index, int)
            or isinstance(unit_index, bool)
            or not 1 <= unit_index <= unit_count
            or unit_index in overrides
        ):
            raise ValueError(f"override {index}.unit_index is invalid or duplicated")
        if not isinstance(tts_text, str) or not tts_text.strip():
            raise ValueError(f"override {index}.tts_text must be a non-empty string")
        overrides[unit_index] = tts_text.strip()
    return overrides


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--narration", required=True, type=Path)
    parser.add_argument("--scenes", required=True, type=Path)
    parser.add_argument("--pronunciation-overrides", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    narration_path = args.narration.resolve()
    narration = require_minimal_narration(load_json(narration_path))
    scenes = require_scenes(load_json(args.scenes.resolve()), len(narration))
    overrides = require_overrides(
        load_json(args.pronunciation_overrides.resolve()), len(narration)
    )

    production: list[dict[str, Any]] = []
    unit_index = 1
    for scene in scenes:
        local_index = 1
        while unit_index <= scene["end_unit"]:
            source = narration[unit_index - 1]
            item: dict[str, Any] = {
                "id": f"{scene['page_id']}-{local_index:02d}",
                "page_id": scene["page_id"],
                "sentence_id": f"{local_index:02d}",
                "chapter": scene["chapter"],
                "caption": scene["caption"],
                "text": source["text"],
            }
            if unit_index in overrides:
                if overrides[unit_index] == source["text"]:
                    raise ValueError(f"override for unit {unit_index} does not change pronunciation")
                item["tts_text"] = overrides[unit_index]
            item["pause_after_ms"] = source["pause_after_ms"]
            production.append(item)
            unit_index += 1
            local_index += 1

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(production, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    source_hash = hashlib.sha256(narration_path.read_bytes()).hexdigest()
    output_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
    print(f"[PASS] materialized production units: {len(production)}")
    print(f"[PASS] scene coverage: {len(scenes)} scenes")
    print(f"[PASS] pronunciation overrides: {len(overrides)}")
    print(f"[PASS] narration SHA-256: {source_hash}")
    print(f"[PASS] production manifest SHA-256: {output_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
