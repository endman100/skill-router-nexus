from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED = (
    "qwen3_full_asr_phrases.csv",
    "qwen3_full_asr_words.csv",
    "qwen3_asr_run_summary.json",
)


def count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate artifacts already produced through asr-router"
    )
    parser.add_argument("--asr-dir", type=Path, required=True)
    args = parser.parse_args()
    asr_dir = args.asr_dir.expanduser().resolve()
    missing = [name for name in REQUIRED if not (asr_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "invoke asr-router with preferred_provider=qwen3 first; missing: "
            + ", ".join(missing)
        )
    phrases = count_rows(asr_dir / REQUIRED[0])
    words = count_rows(asr_dir / REQUIRED[1])
    summary = json.loads((asr_dir / REQUIRED[2]).read_text(encoding="utf-8"))
    if phrases <= 0 or words <= 0:
        raise ValueError("Router Qwen artifacts contain no phrase or word rows")
    if not summary.get("asr_model") or not summary.get("aligner_model"):
        raise ValueError("Router Qwen summary is missing model provenance")
    print(json.dumps({"phrases": phrases, "words": words}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
