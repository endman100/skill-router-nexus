#!/usr/bin/env python3
"""Validate the source-to-rule evidence graph bundled with this skill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def is_http_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate(index_path: Path) -> list[str]:
    errors: list[str] = []
    skill_root = index_path.parent.parent

    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read {index_path}: {exc}"]

    sources = data.get("sources")
    evidence = data.get("evidence")
    rules = data.get("rules")
    if not isinstance(sources, list):
        return ["sources must be a list"]
    if not isinstance(evidence, list):
        return ["evidence must be a list"]
    if not isinstance(rules, list):
        return ["rules must be a list"]

    source_by_id: dict[str, dict] = {}
    for item in sources:
        if not isinstance(item, dict):
            fail("each source must be an object", errors)
            continue
        source_id = item.get("id")
        if not isinstance(source_id, str) or not source_id:
            fail("source id must be a non-empty string", errors)
            continue
        if source_id in source_by_id:
            fail(f"duplicate source id: {source_id}", errors)
        source_by_id[source_id] = item
        if not is_http_url(item.get("url")):
            fail(f"source {source_id} has an invalid URL", errors)
        if not isinstance(item.get("title"), str) or not item["title"].strip():
            fail(f"source {source_id} is missing a title", errors)

    evidence_by_id: dict[str, dict] = {}
    for item in evidence:
        if not isinstance(item, dict):
            fail("each evidence item must be an object", errors)
            continue
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not evidence_id:
            fail("evidence id must be a non-empty string", errors)
            continue
        if evidence_id in evidence_by_id:
            fail(f"duplicate evidence id: {evidence_id}", errors)
        evidence_by_id[evidence_id] = item

        source_id = item.get("source_id")
        if source_id not in source_by_id:
            fail(f"evidence {evidence_id} references unknown source {source_id}", errors)
        seconds = item.get("seconds")
        if not isinstance(seconds, (int, float)) or seconds < 0:
            fail(f"evidence {evidence_id} has invalid seconds", errors)
        if not isinstance(item.get("timecode"), str) or not item["timecode"].strip():
            fail(f"evidence {evidence_id} is missing a timecode", errors)
        if not isinstance(item.get("observation"), str) or not item["observation"].strip():
            fail(f"evidence {evidence_id} is missing an observation", errors)

        image_value = item.get("image")
        if not isinstance(image_value, str) or not image_value:
            fail(f"evidence {evidence_id} is missing an image path", errors)
        else:
            image_path = (skill_root / image_value).resolve()
            try:
                image_path.relative_to(skill_root.resolve())
            except ValueError:
                fail(f"evidence {evidence_id} image escapes the skill folder", errors)
            if not image_path.is_file():
                fail(f"evidence {evidence_id} image does not exist: {image_value}", errors)

    rule_ids: set[str] = set()
    allowed_statuses = {"recurring", "target-specific", "inference"}
    for rule in rules:
        if not isinstance(rule, dict):
            fail("each rule must be an object", errors)
            continue
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            fail("rule id must be a non-empty string", errors)
            continue
        if rule_id in rule_ids:
            fail(f"duplicate rule id: {rule_id}", errors)
        rule_ids.add(rule_id)

        claim = rule.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            fail(f"rule {rule_id} is missing a claim", errors)
        status = rule.get("status")
        if status not in allowed_statuses:
            fail(f"rule {rule_id} has invalid status {status!r}", errors)
        ids = rule.get("evidence_ids")
        if not isinstance(ids, list) or not ids:
            fail(f"rule {rule_id} must cite at least one evidence item", errors)
            continue
        missing = [value for value in ids if value not in evidence_by_id]
        if missing:
            fail(f"rule {rule_id} references missing evidence: {', '.join(missing)}", errors)
            continue

        distinct_sources = {
            evidence_by_id[value].get("source_id") for value in ids if value in evidence_by_id
        }
        if status == "recurring" and len(distinct_sources) < 2:
            fail(
                f"recurring rule {rule_id} needs evidence from at least two source videos",
                errors,
            )
        if status == "inference" and not str(rule.get("limits", "")).strip():
            fail(f"inference rule {rule_id} must state its limits", errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "index",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "references" / "evidence-index.json",
    )
    args = parser.parse_args()
    errors = validate(args.index.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Evidence graph valid: {args.index.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
