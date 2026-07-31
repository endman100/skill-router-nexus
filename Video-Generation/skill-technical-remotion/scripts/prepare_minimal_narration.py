#!/usr/bin/env python3
"""Build or validate the canonical two-field narration JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PAUSE_MARKS = "，；：。！？"
CLOSING_MARKS = "」』”’）》】"
TRAILING_PAUSE_RE = re.compile(
    rf"[{re.escape(PAUSE_MARKS)}][{re.escape(CLOSING_MARKS)}]*$"
)


def compact_script(raw: str) -> str:
    """Remove layout-only blank lines while preserving spoken characters."""
    return "".join(line.strip() for line in raw.splitlines() if line.strip())


def split_pause_units(script: str) -> list[str]:
    """Split after deliberate pause punctuation and retain that punctuation."""
    pattern = re.compile(
        rf".*?[{re.escape(PAUSE_MARKS)}][{re.escape(CLOSING_MARKS)}]*|.+$",
        re.DOTALL,
    )
    return [match.group(0).strip() for match in pattern.finditer(script) if match.group(0).strip()]


def boundary_mark(text: str) -> str | None:
    match = TRAILING_PAUSE_RE.search(text)
    return match.group(0)[0] if match else None


def parse_page_ends(value: str) -> set[int]:
    if not value.strip():
        return set()
    page_ends: set[int] = set()
    for raw in value.split(","):
        try:
            unit = int(raw.strip())
        except ValueError as error:
            raise ValueError(f"invalid page-end unit: {raw!r}") from error
        if unit <= 0:
            raise ValueError("page-end units must be positive one-based indexes")
        page_ends.add(unit)
    return page_ends


def pause_for_unit(
    text: str,
    unit_index: int,
    unit_count: int,
    page_ends: set[int],
    args: argparse.Namespace,
) -> int:
    if unit_index == unit_count:
        return args.final_ms
    if unit_index in page_ends:
        return args.page_ms
    mark = boundary_mark(text)
    if mark == "，":
        return args.comma_ms
    if mark in "；：":
        return args.clause_ms
    if mark in "。！？":
        return args.sentence_ms
    raise ValueError(f"unit {unit_index} has no deliberate pause boundary: {text!r}")


def validate_narration(narration: Any, source: str) -> list[dict[str, Any]]:
    if not isinstance(narration, list) or not narration:
        raise ValueError("narration must be a non-empty JSON array")

    validated: list[dict[str, Any]] = []
    for index, record in enumerate(narration, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"unit {index} must be an object")
        if list(record) != ["text", "pause_after_ms"]:
            raise ValueError(
                f"unit {index} must contain exactly text then pause_after_ms; got {list(record)}"
            )
        text = record["text"]
        pause_ms = record["pause_after_ms"]
        if not isinstance(text, str) or not text or text != text.strip() or "\n" in text or "\r" in text:
            raise ValueError(f"unit {index}.text must be one non-empty trimmed line")
        if not isinstance(pause_ms, int) or isinstance(pause_ms, bool) or pause_ms <= 0:
            raise ValueError(f"unit {index}.pause_after_ms must be a positive integer")
        resplit = split_pause_units(text)
        if resplit != [text]:
            raise ValueError(
                f"unit {index} contains an internal deliberate pause and must be split: {text!r}"
            )
        if index < len(narration) and boundary_mark(text) is None:
            raise ValueError(f"unit {index} does not end at a deliberate pause: {text!r}")
        validated.append({"text": text, "pause_after_ms": pause_ms})

    reconstructed = "".join(record["text"] for record in validated)
    if reconstructed != source:
        mismatch = next(
            (i for i, (left, right) in enumerate(zip(reconstructed, source)) if left != right),
            min(len(reconstructed), len(source)),
        )
        raise ValueError(
            "narration text does not reconstruct the approved script exactly after removing "
            f"layout-only line breaks; first mismatch at character {mismatch}"
        )
    return validated


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--narration", required=True, type=Path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build the minimal narration JSON")
    add_common_arguments(build)
    build.add_argument("--page-end-units", default="")
    build.add_argument("--comma-ms", type=int, default=280)
    build.add_argument("--clause-ms", type=int, default=360)
    build.add_argument("--sentence-ms", type=int, default=420)
    build.add_argument("--page-ms", type=int, default=900)
    build.add_argument("--final-ms", type=int, default=700)

    validate = subparsers.add_parser("validate", help="validate an existing narration JSON")
    add_common_arguments(validate)

    args = parser.parse_args()
    script_path = args.script.resolve()
    narration_path = args.narration.resolve()
    source = compact_script(script_path.read_text(encoding="utf-8-sig"))
    if not source:
        raise ValueError("approved script is empty")

    if args.command == "build":
        page_ends = parse_page_ends(args.page_end_units)
        units = split_pause_units(source)
        invalid_page_ends = sorted(unit for unit in page_ends if unit >= len(units))
        if invalid_page_ends:
            raise ValueError(
                f"page-end units must precede the final unit {len(units)}: {invalid_page_ends}"
            )
        for name in ("comma_ms", "clause_ms", "sentence_ms", "page_ms", "final_ms"):
            if getattr(args, name) <= 0:
                raise ValueError(f"--{name.replace('_', '-')} must be positive")
        narration = [
            {
                "text": text,
                "pause_after_ms": pause_for_unit(
                    text, index, len(units), page_ends, args
                ),
            }
            for index, text in enumerate(units, start=1)
        ]
        validate_narration(narration, source)
        narration_path.parent.mkdir(parents=True, exist_ok=True)
        narration_path.write_text(
            json.dumps(narration, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        narration = json.loads(narration_path.read_text(encoding="utf-8-sig"))
        validate_narration(narration, source)

    source_sha = hashlib.sha256(script_path.read_bytes()).hexdigest()
    narration_sha = hashlib.sha256(narration_path.read_bytes()).hexdigest()
    print(f"[PASS] minimal narration units: {len(narration)}")
    print("[PASS] schema: exactly text, pause_after_ms")
    print("[PASS] reconstruction: approved script matches after layout-line removal")
    print(f"[PASS] source SHA-256: {source_sha}")
    print(f"[PASS] narration SHA-256: {narration_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
