#!/usr/bin/env python3
"""Fail when the skill contains external-source tracking material."""

from __future__ import annotations

import re
import sys
from pathlib import Path


TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".ts", ".tsx", ".js", ".jsx"}
FORBIDDEN_PATHS = {
    "assets/reference",
    "references/evidence-index.json",
    "references/reference-atlas.md",
    "references/source-ledger.md",
    "scripts/extract_reference_frames.py",
    "scripts/validate_evidence.py",
}
FORBIDDEN_TEXT = {
    "source-backed",
    "evidence_ids",
    "evidence-index",
    "reference-atlas",
    "source-ledger",
    "extract_reference_frames",
    "validate_evidence",
    "aR97E7aKEgg",
    "Gary Chen",
}
URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)
WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r"(?i)(?:^|[\"'`(])(?:[a-z]:[/\\])")


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    failures: list[str] = []

    for relative_path in sorted(FORBIDDEN_PATHS):
        if (skill_root / relative_path).exists():
            failures.append(f"forbidden path: {relative_path}")

    for path in skill_root.rglob("*"):
        if not path.is_file() or path == Path(__file__).resolve() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative_path = path.relative_to(skill_root).as_posix()
        text = path.read_text(encoding="utf-8")
        if URL_PATTERN.search(text):
            failures.append(f"external URL: {relative_path}")
        if WINDOWS_ABSOLUTE_PATH_PATTERN.search(text):
            failures.append(f"machine-specific absolute path: {relative_path}")
        if "0.000–17.470" in text or "5–30 second" in text:
            failures.append(f"obsolete shortened-reference rule: {relative_path}")
        lowered = text.lower()
        for marker in sorted(FORBIDDEN_TEXT):
            if marker.lower() in lowered:
                failures.append(f"tracking marker {marker!r}: {relative_path}")

    if failures:
        print("Portability validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Portability validation passed: no external-source tracking material found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
