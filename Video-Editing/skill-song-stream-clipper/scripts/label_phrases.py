from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from codex_runtime import (
    DEFAULT_CODEX_MODEL,
    DEFAULT_SERVICE_TIER,
    build_exec_command,
    find_codex,
)
from pipeline_utils import read_csv, write_csv


FORBIDDEN_LABELS = {"lyric", "setup", "unknown_song", "unknown song"}


def read_allowed_labels(path: Path) -> list[str]:
    labels = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    deduped = list(dict.fromkeys(labels))
    forbidden = sorted(
        label for label in deduped if label.casefold() in FORBIDDEN_LABELS
    )
    if forbidden:
        raise ValueError(f"labels file contains forbidden labels: {forbidden}")
    if "talk" not in deduped:
        raise ValueError("labels file must contain talk")
    concrete = [label for label in deduped if label != "talk"]
    if not concrete:
        raise ValueError("labels file must contain at least one concrete song title")
    return ["talk", *concrete]


def build_prompt(
    *,
    batch_csv: Path,
    output_jsonl: Path,
    batch_name: str,
    labels: list[str],
    id_column: str,
    text_column: str,
    start_column: str,
    end_column: str,
    label_key: str,
) -> str:
    label_lines = "\n".join(f"- {label}" for label in labels)
    return f"""You are Codex running through codex exec. Do not call OpenAI API, another API, web search, YouTube comments, YouTube subtitles, chapters, descriptions, lyric websites, or music-recognition services.

Task: label and conservatively repair every ASR phrase.

Input CSV: {batch_csv}
Output JSONL: {output_jsonl}
Batch: {batch_name}

Allowed labels:
{label_lines}

Rules:
1. Read every row and write exactly one JSON object per row in unchanged order. Do not omit, add, combine, or sample rows.
2. Use exactly one allowed label. A sung lyric gets its concrete song title; every non-lyric event is talk.
3. Announcements, setup, conversation, laughter, humming without identifiable lyrics, instrumental passages, and uncertainty are talk.
4. Use only the current CSV, neighboring rows in this batch, and the supplied candidate list. Do not infer a title from a spoken title announcement.
5. Repair obvious ASR errors in sung rows using semantic context, but never invent an unsupported missing line and never alter timestamps.
6. Write all Chinese output in Traditional Chinese. Preserve English and Japanese writing systems.
7. Do not print phrase or lyric text in the terminal response.

Each JSON object must contain:
{{
  "{id_column}": <copied from input>,
  "{start_column}": <copied number>,
  "{end_column}": <copied number>,
  "original_text": <copied from {text_column}>,
  "repaired_text": <conservatively repaired text>,
  "{label_key}": <one exact allowed label>,
  "confidence": <number 0..1>,
  "language_guess": "zh|ja|en|mixed|unknown",
  "note": <short string>
}}

After writing the file, reply only with its path and row count.
"""


def validate_jsonl(
    *,
    path: Path,
    input_rows: list[dict[str, str]],
    labels: set[str],
    id_column: str,
    label_key: str,
) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing output"
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if len(lines) != len(input_rows):
        return False, f"row count {len(lines)} != {len(input_rows)}"
    decoded: list[dict[str, Any]] = []
    for offset, line in enumerate(lines):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            return False, f"bad json at line {offset + 1}: {exc}"
        decoded.append(item)
        expected_id = str(input_rows[offset][id_column])
        if str(item.get(id_column, "")) != expected_id:
            return False, f"bad row order at line {offset + 1}"
        label = str(item.get(label_key, "")).strip()
        if label not in labels:
            return False, f"bad label at line {offset + 1}: {label!r}"
    for offset, item in enumerate(decoded):
        for key in ("repaired_text", "confidence", "language_guess", "note"):
            if key not in item:
                return False, f"missing {key} at line {offset + 1}"
        confidence = float(item["confidence"])
        if not 0.0 <= confidence <= 1.0:
            return False, f"confidence outside 0..1 at line {offset + 1}"
    return True, "ok"


def prepare_batches(
    *,
    rows: list[dict[str, str]],
    labels: list[str],
    output_dir: Path,
    batch_size: int,
    id_column: str,
    text_column: str,
    start_column: str,
    end_column: str,
    label_key: str,
) -> list[dict[str, str]]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    batch_dir = output_dir / "batches"
    prompt_dir = output_dir / "prompts"
    batch_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    index: list[dict[str, str]] = []
    for batch_no, offset in enumerate(range(0, len(rows), batch_size), start=1):
        batch_rows = rows[offset : offset + batch_size]
        name = (
            f"batch_{batch_no:03d}_rows_{offset:04d}_{offset + len(batch_rows) - 1:04d}"
        )
        batch_csv = batch_dir / f"{name}.csv"
        output_jsonl = batch_dir / f"{name}.labels.jsonl"
        prompt_path = prompt_dir / f"{name}.prompt.txt"
        write_csv(batch_csv, batch_rows, fields)
        prompt_path.write_text(
            build_prompt(
                batch_csv=batch_csv.resolve(),
                output_jsonl=output_jsonl.resolve(),
                batch_name=name,
                labels=labels,
                id_column=id_column,
                text_column=text_column,
                start_column=start_column,
                end_column=end_column,
                label_key=label_key,
            ),
            encoding="utf-8",
        )
        index.append(
            {
                "batch_no": str(batch_no),
                "batch_name": name,
                "rows": str(len(batch_rows)),
                "batch_csv": str(batch_csv.resolve()),
                "prompt_path": str(prompt_path.resolve()),
                "output_jsonl": str(output_jsonl.resolve()),
            }
        )
    write_csv(
        output_dir / "batch_index.csv",
        index,
        [
            "batch_no",
            "batch_name",
            "rows",
            "batch_csv",
            "prompt_path",
            "output_jsonl",
        ],
    )
    (output_dir / "labels.txt").write_text(
        "\n".join(labels) + "\n",
        encoding="utf-8",
    )
    return index


def run_batches(
    *,
    index: list[dict[str, str]],
    labels: set[str],
    args: argparse.Namespace,
) -> None:
    codex_exe = find_codex(args.codex_exe)
    log_dir = args.output_dir / "codex_exec_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for batch in index:
        input_rows = read_csv(Path(batch["batch_csv"]))
        output = Path(batch["output_jsonl"])
        valid, reason = validate_jsonl(
            path=output,
            input_rows=input_rows,
            labels=labels,
            id_column=args.id_column,
            label_key=args.label_key,
        )
        if valid and not args.force:
            print(f"SKIP {batch['batch_name']}: valid output exists", flush=True)
            continue
        command = build_exec_command(
            codex_exe=codex_exe,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            service_tier=args.service_tier,
            workdir=args.workdir,
            last_message_path=log_dir / f"{batch['batch_name']}.last_message.txt",
        )
        prompt = Path(batch["prompt_path"]).read_text(encoding="utf-8")
        print(f"RUN {batch['batch_name']}: {reason}", flush=True)
        with (log_dir / f"{batch['batch_name']}.stdout.txt").open(
            "w",
            encoding="utf-8",
        ) as stdout:
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
        valid, reason = validate_jsonl(
            path=output,
            input_rows=input_rows,
            labels=labels,
            id_column=args.id_column,
            label_key=args.label_key,
        )
        if result.returncode != 0 or not valid:
            failures.append(
                f"{batch['batch_name']}: exit={result.returncode}, validation={reason}"
            )
    if failures:
        raise RuntimeError("\n".join(failures))


def merge_outputs(
    *,
    rows: list[dict[str, str]],
    index: list[dict[str, str]],
    labels: set[str],
    args: argparse.Namespace,
) -> None:
    outputs: dict[str, dict[str, Any]] = {}
    for batch in index:
        batch_rows = read_csv(Path(batch["batch_csv"]))
        output = Path(batch["output_jsonl"])
        valid, reason = validate_jsonl(
            path=output,
            input_rows=batch_rows,
            labels=labels,
            id_column=args.id_column,
            label_key=args.label_key,
        )
        if not valid:
            raise ValueError(f"{output} failed validation: {reason}")
        for line_no, line in enumerate(
            output.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            item = json.loads(line)
            row_id = str(item[args.id_column])
            if row_id in outputs:
                raise ValueError(f"Duplicate output id: {row_id}")
            item["_source_jsonl"] = str(output.resolve())
            item["_source_line"] = line_no
            outputs[row_id] = item
    merged: list[dict[str, Any]] = []
    for source in rows:
        row_id = str(source[args.id_column])
        if row_id not in outputs:
            raise ValueError(f"Missing output id: {row_id}")
        item = outputs[row_id]
        merged.append(
            {
                **source,
                args.label_key: item[args.label_key],
                "label_confidence": item["confidence"],
                "language_guess": item["language_guess"],
                "repaired_text": item["repaired_text"],
                "label_note": item["note"],
                "label_source": "codex_cli",
                "source_jsonl": item["_source_jsonl"],
                "source_line": item["_source_line"],
            }
        )
    fields = list(rows[0]) + [
        args.label_key,
        "label_confidence",
        "language_guess",
        "repaired_text",
        "label_note",
        "label_source",
        "source_jsonl",
        "source_line",
    ]
    write_csv(args.output_dir / "labeled_phrases.csv", merged, fields)
    summary = {
        "rows_total": len(rows),
        "annotated_rows": len(merged),
        "batch_count": len(index),
        "label_counts": dict(Counter(row[args.label_key] for row in merged)),
        "labels": sorted(labels),
        "evidence_policy": "all phrases; local ASR and candidate titles only",
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Label every ASR phrase as talk or one concrete song title through Codex CLI."
    )
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--labels-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument("--id-column", default="index")
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--start-column", default="start_seconds")
    parser.add_argument("--end-column", default="end_seconds")
    parser.add_argument("--label-key", default="song_label")
    parser.add_argument("--batch-size", type=int, default=80)
    parser.add_argument("--codex-exe", default="")
    parser.add_argument("--model", default=DEFAULT_CODEX_MODEL)
    parser.add_argument("--service-tier", default=DEFAULT_SERVICE_TIER)
    parser.add_argument("--reasoning-effort", default="medium")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.input_csv = args.input_csv.resolve()
    args.labels_file = args.labels_file.resolve()
    args.output_dir = args.output_dir.resolve()
    args.workdir = args.workdir.resolve()
    rows = read_csv(args.input_csv)
    if not rows:
        raise ValueError(f"{args.input_csv} has no rows")
    required = {
        args.id_column,
        args.text_column,
        args.start_column,
        args.end_column,
    }
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"Missing ASR columns: {missing}")
    labels = read_allowed_labels(args.labels_file)
    index = prepare_batches(
        rows=rows,
        labels=labels,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        id_column=args.id_column,
        text_column=args.text_column,
        start_column=args.start_column,
        end_column=args.end_column,
        label_key=args.label_key,
    )
    if args.prepare_only:
        return 0
    run_batches(index=index, labels=set(labels), args=args)
    merge_outputs(rows=rows, index=index, labels=set(labels), args=args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
