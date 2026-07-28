#!/usr/bin/env python3
"""Generate a timing and SFX plan for a black-background white-text opener."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PRESETS = {
    "micro": {
        "duration": 3.0,
        "beats": [
            ("black_hold", 0.0, 0.2),
            ("hero_reveal", 0.2, 0.9),
            ("first_change", 0.9, 1.7),
            ("final_hold", 1.7, 2.5),
            ("transition_out", 2.5, 3.0),
        ],
    },
    "standard": {
        "duration": 5.4,
        "beats": [
            ("black_hold", 0.0, 0.3),
            ("hero_reveal", 0.3, 1.2),
            ("hero_hold", 1.2, 2.2),
            ("replacement", 2.2, 3.4),
            ("final_hold", 3.4, 4.7),
            ("transition_out", 4.7, 5.4),
        ],
    },
    "slow": {
        "duration": 7.0,
        "beats": [
            ("black_hold", 0.0, 0.5),
            ("hero_reveal", 0.5, 1.6),
            ("hero_hold", 1.6, 3.0),
            ("replacement", 3.0, 4.7),
            ("final_hold", 4.7, 6.3),
            ("transition_out", 6.3, 7.0),
        ],
    },
}


TYPE_BEATS = {"hero_reveal", "first_change", "replacement", "final_hold"}
NO_CLICK_CHARS = {" ", "\n", "\t"}


def text_units(text: str) -> list[dict]:
    units = []
    visible_index = 0
    for raw_index, char in enumerate(text):
        units.append(
            {
                "raw_index": raw_index,
                "visible_index": visible_index,
                "char": char,
                "click": char not in NO_CLICK_CHARS,
            }
        )
        if char not in NO_CLICK_CHARS:
            visible_index += 1
    return units


def build_typing_events(text: str, start: float, end: float, cps: float, sfx_gain_db: float) -> tuple[dict, list[dict], list[dict], list[str]]:
    warnings = []
    units = text_units(text)
    clickable = [u for u in units if u["click"]]
    available = max(0.001, end - start)
    target_duration = len(clickable) / cps if clickable else 0.0
    if target_duration > available:
        actual_cps = len(clickable) / available
        warnings.append(
            f"Text requires {actual_cps:.2f} chars/s to fit; shorten copy if this exceeds 16 chars/s."
        )
    else:
        actual_cps = cps

    typed_count = 0
    events = []
    sfx_events = []
    for unit in units:
        if unit["click"]:
            event_time = start + typed_count / actual_cps if actual_cps else start
            typed_count += 1
        else:
            event_time = start + typed_count / actual_cps if actual_cps else start
        event_time = round(min(event_time, end), 3)
        event = {
            "time": event_time,
            "char": unit["char"],
            "raw_index": unit["raw_index"],
            "visible_index": unit["visible_index"],
            "visible_text": text[: unit["raw_index"] + 1],
        }
        events.append(event)
        if unit["click"]:
            # Deterministic micro-variation keeps clicks from sounding robotic.
            variation = ((unit["visible_index"] % 5) - 2) * 0.8
            pitch = 1.0 + ((unit["visible_index"] % 7) - 3) * 0.015
            sfx_events.append(
                {
                    "time": event_time,
                    "type": "typing_click",
                    "char": unit["char"],
                    "gain_db": round(sfx_gain_db + variation, 2),
                    "pitch": round(pitch, 3),
                }
            )

    typing = {
        "enabled": bool(text),
        "mode": "character_by_character",
        "requested_cps": cps,
        "actual_cps": round(actual_cps, 3) if text else 0,
        "start": start,
        "end": end,
        "typed_chars": len(clickable),
        "sfx": {
            "enabled": bool(text),
            "type": "typing_click",
            "event_count": len(sfx_events),
        },
    }
    return typing, events, sfx_events, warnings


def build_plan(args: argparse.Namespace) -> dict:
    preset = PRESETS[args.preset]
    replacements = args.replace or []
    final = args.final or (replacements[-1] if replacements else args.title)
    beats = []
    all_sfx_events = []
    warnings = []
    for name, start, end in preset["beats"]:
        text = ""
        motion = ""
        if name == "black_hold":
            motion = "pure black, no text"
        elif name == "hero_reveal":
            text = args.title
            motion = "type characters one by one with subtle new-character soften"
        elif name == "hero_hold":
            text = args.title
            motion = "hold readable phrase"
        elif name in {"first_change", "replacement"}:
            text = " -> ".join(replacements) if replacements else args.title
            motion = "clear or smear previous phrase, then type replacement characters"
        elif name == "final_hold":
            text = final
            motion = "type final phrase, then hold large white text"
        elif name == "transition_out":
            text = final
            motion = args.transition
        typing = {
            "enabled": False,
            "mode": "hold_or_transition",
            "sfx": {"enabled": False, "event_count": 0},
        }
        typing_events = []
        sfx_events = []
        if text and name in TYPE_BEATS:
            typing, typing_events, sfx_events, beat_warnings = build_typing_events(
                text,
                start,
                end,
                args.typing_cps,
                args.sfx_gain_db,
            )
            warnings.extend([f"{name}: {warning}" for warning in beat_warnings])
            if args.no_sfx:
                typing["sfx"] = {"enabled": False, "type": "typing_click", "event_count": 0}
                sfx_events = []
            all_sfx_events.extend(sfx_events)
        beats.append(
            {
                "name": name,
                "start": start,
                "end": end,
                "duration": round(end - start, 3),
                "text": text,
                "motion": motion,
                "typing": typing,
                "typing_events": typing_events,
                "sfx_events": sfx_events,
            }
        )

    return {
        "title": args.title,
        "replace": replacements,
        "final": final,
        "preset": args.preset,
        "duration": preset["duration"],
        "ratio": args.ratio,
        "style": {
            "background": "#000000",
            "text": "#ffffff",
            "font": "clean sans-serif",
            "avoid": ["colored flash", "busy gradient", "persistent neon-line background"],
        },
        "typing": {
            "default_mode": "character_by_character",
            "requested_cps": args.typing_cps,
            "sfx_enabled": not args.no_sfx,
            "sfx_type": "typing_click",
            "sfx_gain_db": args.sfx_gain_db,
        },
        "sfx_events": [] if args.no_sfx else all_sfx_events,
        "warnings": warnings,
        "beats": beats,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a typed black-white text opener timing plan.")
    parser.add_argument("--title", required=True, help="Primary opening phrase.")
    parser.add_argument("--replace", nargs="*", default=[], help="Optional replacement words or phrases.")
    parser.add_argument("--final", default="", help="Final hold phrase.")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="standard")
    parser.add_argument("--ratio", default="16:9")
    parser.add_argument("--transition", default="white velocity wipe into next scene")
    parser.add_argument("--typing-cps", type=float, default=14.0, help="Typing cadence in visible chars per second.")
    parser.add_argument("--no-sfx", action="store_true", help="Disable typing click SFX events.")
    parser.add_argument("--sfx-gain-db", type=float, default=-16.0, help="Base gain for typing click SFX events.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.typing_cps <= 0:
        raise SystemExit("--typing-cps must be positive")

    plan = build_plan(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "duration": plan["duration"], "beats": len(plan["beats"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
