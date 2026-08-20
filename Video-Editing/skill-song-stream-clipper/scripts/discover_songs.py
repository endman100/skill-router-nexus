from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from codex_runtime import (
    DEFAULT_CODEX_MODEL,
    DEFAULT_SERVICE_TIER,
    build_exec_command,
    find_codex,
)
from pipeline_utils import read_csv, seconds_to_timestamp, write_csv


WINDOW_FIELDS = [
    "window_no",
    "window_start_seconds",
    "window_end_seconds",
    "window_start_ts",
    "window_end_ts",
    "phrase_count",
    "first_phrase_index",
    "last_phrase_index",
    "asr_text",
]


def build_windows(
    rows: list[dict[str, str]],
    *,
    text_column: str,
    start_column: str,
    end_column: str,
    window_seconds: float,
) -> list[dict[str, Any]]:
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    maximum_end = max(float(row[end_column]) for row in rows)
    window_count = int(maximum_end // window_seconds) + 1
    windows: list[dict[str, Any]] = []
    for window_index in range(window_count):
        start = window_index * window_seconds
        end = start + window_seconds
        window_rows = [
            row
            for row in rows
            if float(row[start_column]) < end and float(row[end_column]) >= start
        ]
        if not window_rows:
            continue
        text = "\n".join(
            f"{row.get('start_ts') or seconds_to_timestamp(float(row[start_column]))} - "
            f"{row.get('end_ts') or seconds_to_timestamp(float(row[end_column]))}: "
            f"{row.get(text_column, '')}"
            for row in window_rows
        )
        windows.append(
            {
                "window_no": len(windows) + 1,
                "window_start_seconds": f"{start:.3f}",
                "window_end_seconds": f"{end:.3f}",
                "window_start_ts": seconds_to_timestamp(start),
                "window_end_ts": seconds_to_timestamp(end),
                "phrase_count": len(window_rows),
                "first_phrase_index": window_rows[0].get("index", ""),
                "last_phrase_index": window_rows[-1].get("index", ""),
                "asr_text": text,
            }
        )
    return windows


def build_prompt(batch_csv: Path, output_json: Path, batch_name: str) -> str:
    return f"""You are Codex running through codex exec. Do not call OpenAI API, another API, web search, YouTube comments, YouTube subtitles, chapters, descriptions, lyric websites, or music-recognition services.

Task: discover candidate song titles from fixed three-minute ASR windows.

Input CSV: {batch_csv}
Output JSON: {output_json}
Batch: {batch_name}

Rules:
1. Read every input row. A row is a fixed timeline window, not a pre-segmented song.
2. Use only sung lyric semantics in this CSV. Never use spoken song-name announcements, artist attribution, setup, metadata, or an ASR phrase that merely states a title.
3. If lyric evidence is weak, return no candidate rather than guessing. One window may have zero, one, or multiple candidates.
4. Write all Chinese fields in Traditional Chinese. Preserve English and Japanese writing systems.
5. Keep evidence summaries short. Do not print lyrics in the terminal response.

Write exactly one JSON object:
{{
  "batch_name": "{batch_name}",
  "candidate_songs": [
    {{
      "window_no": <integer copied from input>,
      "window_start_seconds": <number copied from input>,
      "window_end_seconds": <number copied from input>,
      "candidate_title": <string>,
      "candidate_artist": <string or "unknown">,
      "confidence": <number 0..1>,
      "evidence_summary": <short string>,
      "needs_review": <true or false>,
      "note": <short string>
    }}
  ]
}}

After writing the file, reply only with its path and candidate count.
"""


def validate_output(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing output"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"bad json: {exc}"
    candidates = payload.get("candidate_songs") if isinstance(payload, dict) else None
    if not isinstance(candidates, list):
        return False, "missing candidate_songs list"
    required = {
        "window_no",
        "window_start_seconds",
        "window_end_seconds",
        "candidate_title",
        "candidate_artist",
        "confidence",
        "evidence_summary",
        "needs_review",
        "note",
    }
    for item in candidates:
        if not isinstance(item, dict):
            return False, "candidate item is not an object"
        missing = required - set(item)
        if missing:
            return False, f"candidate missing keys: {sorted(missing)}"
        confidence = float(item["confidence"])
        if not 0.0 <= confidence <= 1.0:
            return False, "candidate confidence is outside 0..1"
    return True, "ok"


def prepare_batches(
    *,
    output_dir: Path,
    windows: list[dict[str, Any]],
    windows_per_batch: int,
) -> list[dict[str, str]]:
    if windows_per_batch < 1:
        raise ValueError("windows_per_batch must be positive")
    batch_dir = output_dir / "batches"
    prompt_dir = output_dir / "prompts"
    batch_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, str]] = []
    for batch_no, offset in enumerate(
        range(0, len(windows), windows_per_batch),
        start=1,
    ):
        rows = windows[offset : offset + windows_per_batch]
        name = (
            f"batch_{batch_no:03d}_windows_"
            f"{int(rows[0]['window_no']):04d}_{int(rows[-1]['window_no']):04d}"
        )
        batch_csv = batch_dir / f"{name}.csv"
        output_json = batch_dir / f"{name}.song_candidates.json"
        prompt_path = prompt_dir / f"{name}.prompt.txt"
        write_csv(batch_csv, rows, WINDOW_FIELDS)
        prompt_path.write_text(
            build_prompt(batch_csv.resolve(), output_json.resolve(), name),
            encoding="utf-8",
        )
        index.append(
            {
                "batch_no": str(batch_no),
                "batch_name": name,
                "windows": str(len(rows)),
                "batch_csv": str(batch_csv.resolve()),
                "prompt_path": str(prompt_path.resolve()),
                "output_json": str(output_json.resolve()),
            }
        )
    write_csv(
        output_dir / "batch_index.csv",
        index,
        [
            "batch_no",
            "batch_name",
            "windows",
            "batch_csv",
            "prompt_path",
            "output_json",
        ],
    )
    return index


def run_batches(args: argparse.Namespace, index: list[dict[str, str]]) -> None:
    codex_exe = find_codex(args.codex_exe)
    log_dir = args.output_dir / "codex_exec_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for batch in index:
        output = Path(batch["output_json"])
        valid, reason = validate_output(output)
        if valid and not args.force:
            print(f"SKIP {batch['batch_name']}: valid output exists", flush=True)
            continue
        prompt = Path(batch["prompt_path"]).read_text(encoding="utf-8")
        stdout_path = log_dir / f"{batch['batch_name']}.stdout.txt"
        last_message = log_dir / f"{batch['batch_name']}.last_message.txt"
        command = build_exec_command(
            codex_exe=codex_exe,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            service_tier=args.service_tier,
            workdir=args.workdir,
            last_message_path=last_message,
        )
        print(f"RUN {batch['batch_name']}: {reason}", flush=True)
        with stdout_path.open("w", encoding="utf-8") as stdout:
            result = subprocess.run(
                command,
                input=prompt,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=stdout,
                stderr=subprocess.STDOUT,
                cwd=args.workdir,
                check=False,
            )
        valid, reason = validate_output(output)
        if result.returncode != 0 or not valid:
            failures.append(
                f"{batch['batch_name']}: exit={result.returncode}, validation={reason}"
            )
    if failures:
        raise RuntimeError("\n".join(failures))


def merge_outputs(output_dir: Path, index: list[dict[str, str]]) -> None:
    candidates: list[dict[str, Any]] = []
    for batch in index:
        payload = json.loads(Path(batch["output_json"]).read_text(encoding="utf-8"))
        for item in payload["candidate_songs"]:
            title = str(item.get("candidate_title", "")).strip()
            if title and title.lower() != "unknown":
                candidates.append({**item, "source_json": batch["output_json"]})
    candidate_fields = [
        "window_no",
        "window_start_seconds",
        "window_end_seconds",
        "candidate_title",
        "candidate_artist",
        "confidence",
        "evidence_summary",
        "needs_review",
        "note",
        "source_json",
    ]
    write_csv(
        output_dir / "window_song_candidates.csv",
        candidates,
        candidate_fields,
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[str(candidate["candidate_title"]).strip()].append(candidate)
    titles: list[dict[str, Any]] = []
    for title, rows in sorted(
        grouped.items(),
        key=lambda item: min(float(row["window_start_seconds"]) for row in item[1]),
    ):
        confidences = [float(row["confidence"]) for row in rows]
        artists = sorted(
            {
                str(row.get("candidate_artist", "")).strip()
                for row in rows
                if str(row.get("candidate_artist", "")).strip().lower()
                not in {"", "unknown"}
            }
        )
        titles.append(
            {
                "title_no": len(titles) + 1,
                "candidate_title": title,
                "candidate_artists": ";".join(artists) if artists else "unknown",
                "first_window_no": min(int(row["window_no"]) for row in rows),
                "last_window_no": max(int(row["window_no"]) for row in rows),
                "window_hits": len(rows),
                "max_confidence": f"{max(confidences):.3f}",
                "avg_confidence": f"{sum(confidences) / len(confidences):.3f}",
                "needs_review": any(bool(row.get("needs_review")) for row in rows),
            }
        )
    title_fields = [
        "title_no",
        "candidate_title",
        "candidate_artists",
        "first_window_no",
        "last_window_no",
        "window_hits",
        "max_confidence",
        "avg_confidence",
        "needs_review",
    ]
    write_csv(output_dir / "discovered_song_titles.csv", titles, title_fields)
    (output_dir / "labels.txt").write_text(
        "talk\n" + "\n".join(row["candidate_title"] for row in titles) + "\n",
        encoding="utf-8",
    )
    summary = {
        "candidate_rows": len(candidates),
        "discovered_titles": len(titles),
        "labels_file": str((output_dir / "labels.txt").resolve()),
        "evidence_policy": "sung lyrics only; no web, comments, metadata, or spoken title announcements",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover candidate song titles from fixed ASR windows through Codex CLI."
    )
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--start-column", default="start_seconds")
    parser.add_argument("--end-column", default="end_seconds")
    parser.add_argument("--window-seconds", type=float, default=180.0)
    parser.add_argument("--windows-per-batch", type=int, default=4)
    parser.add_argument("--codex-exe", default="")
    parser.add_argument("--model", default=DEFAULT_CODEX_MODEL)
    parser.add_argument("--service-tier", default=DEFAULT_SERVICE_TIER)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.input_csv = args.input_csv.resolve()
    args.output_dir = args.output_dir.resolve()
    args.workdir = args.workdir.resolve()
    rows = read_csv(args.input_csv)
    if not rows:
        raise ValueError(f"{args.input_csv} has no rows")
    required = {args.text_column, args.start_column, args.end_column}
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"Missing ASR columns: {missing}")
    windows = build_windows(
        rows,
        text_column=args.text_column,
        start_column=args.start_column,
        end_column=args.end_column,
        window_seconds=args.window_seconds,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.output_dir / "asr_windows_for_song_discovery.csv",
        windows,
        WINDOW_FIELDS,
    )
    index = prepare_batches(
        output_dir=args.output_dir,
        windows=windows,
        windows_per_batch=args.windows_per_batch,
    )
    if args.prepare_only:
        return 0
    run_batches(args, index)
    merge_outputs(args.output_dir, index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
