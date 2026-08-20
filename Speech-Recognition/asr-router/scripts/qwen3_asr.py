from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def seconds_to_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{millis:03d}"


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise ValueError(f"audio duration must be positive: {path}")
    return duration


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


ASR_MODEL_ID = "Qwen/Qwen3-ASR-1.7B-hf"
ALIGNER_MODEL_ID = "Qwen/Qwen3-ForcedAligner-0.6B-hf"


def chunk_plan(
    audio_duration: float,
    chunk_seconds: float,
    overlap_seconds: float,
) -> list[dict[str, Any]]:
    if audio_duration <= 0:
        raise ValueError("audio_duration must be positive")
    if chunk_seconds <= 0 or chunk_seconds > 300:
        raise ValueError("chunk_seconds must be positive and no greater than 300")
    if overlap_seconds <= 0 or overlap_seconds >= chunk_seconds / 2:
        raise ValueError("overlap must be positive and less than half the chunk size")
    stride = chunk_seconds - overlap_seconds
    chunks: list[dict[str, Any]] = []
    start = 0.0
    while start < audio_duration - 0.05:
        end = min(audio_duration, start + chunk_seconds)
        index = len(chunks)
        chunks.append(
            {
                "chunk_id": f"chunk_{index:03d}",
                "chunk_index": index,
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": end - start,
                "retain_start_seconds": (
                    start if index == 0 else start + overlap_seconds / 2.0
                ),
                "retain_end_seconds": end,
            }
        )
        if end >= audio_duration:
            break
        start += stride
    for index, chunk in enumerate(chunks[:-1]):
        next_start = float(chunks[index + 1]["start_seconds"])
        chunk["retain_end_seconds"] = min(
            float(chunk["end_seconds"]),
            next_start + overlap_seconds / 2.0,
        )
    return chunks


def timestamp_value(item: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return float(value)
    return None


def make_phrase(index: int, words: list[dict[str, Any]]) -> dict[str, Any]:
    start = float(words[0]["start_seconds"])
    end = float(words[-1]["end_seconds"])
    return {
        "index": index,
        "language": words[0].get("language", ""),
        "text": "".join(str(word.get("text", "")) for word in words),
        "start_seconds": f"{start:.3f}",
        "end_seconds": f"{end:.3f}",
        "start_ts": seconds_to_timestamp(start),
        "end_ts": seconds_to_timestamp(end),
        "word_count": len(words),
    }


def build_phrases(
    words: list[dict[str, Any]],
    max_gap_seconds: float = 0.90,
    max_duration_seconds: float = 8.0,
) -> list[dict[str, Any]]:
    phrases: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    ordered = sorted(
        words,
        key=lambda row: (float(row["start_seconds"]), int(row["index"])),
    )
    for word in ordered:
        if not str(word.get("text", "")).strip():
            continue
        if not current:
            current = [word]
            continue
        gap = float(word["start_seconds"]) - float(current[-1]["end_seconds"])
        duration = float(word["end_seconds"]) - float(current[0]["start_seconds"])
        language_changed = word.get("language") != current[-1].get("language")
        if gap > max_gap_seconds or duration > max_duration_seconds or language_changed:
            phrases.append(make_phrase(len(phrases), current))
            current = [word]
        else:
            current.append(word)
    if current:
        phrases.append(make_phrase(len(phrases), current))
    return phrases


def extract_chunk(audio: Path, chunk_dir: Path, chunk: dict[str, Any]) -> Path:
    output = chunk_dir / f"{chunk['chunk_id']}.wav"
    if output.exists():
        return output
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{float(chunk['start_seconds']):.3f}",
            "-t",
            f"{float(chunk['duration_seconds']):.3f}",
            "-i",
            str(audio),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output),
        ],
        check=True,
    )
    return output


def process_chunk(
    *,
    chunk: dict[str, Any],
    audio: Path,
    chunk_dir: Path,
    asr_processor: Any,
    asr_model: Any,
    aligner_processor: Any,
    aligner_model: Any,
    torch_module: Any,
    max_new_tokens: int,
) -> dict[str, Any]:
    chunk_id = str(chunk["chunk_id"])
    raw_json = chunk_dir / f"{chunk_id}_asr_alignment.json"
    words_csv = chunk_dir / f"{chunk_id}_words_fullvideo.csv"
    if raw_json.exists() and words_csv.exists():
        return json.loads(raw_json.read_text(encoding="utf-8"))

    wav_path = extract_chunk(audio, chunk_dir, chunk)
    print(
        f"ASR {chunk_id} {seconds_to_timestamp(chunk['start_seconds'])}-"
        f"{seconds_to_timestamp(chunk['end_seconds'])}",
        flush=True,
    )
    inputs = asr_processor.apply_transcription_request(audio=str(wav_path)).to(
        asr_model.device,
        asr_model.dtype,
    )
    with torch_module.inference_mode():
        output_ids = asr_model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
    generated_ids = output_ids[:, inputs["input_ids"].shape[1] :]
    raw = asr_processor.decode(generated_ids)[0]
    parsed = asr_processor.decode(generated_ids, return_format="parsed")[0]
    transcription = asr_processor.decode(
        generated_ids,
        return_format="transcription_only",
    )[0]
    language = parsed.get("language") or "Chinese"

    aligner_inputs, word_lists = aligner_processor.prepare_forced_aligner_inputs(
        audio=str(wav_path),
        transcript=transcription,
        language=language,
    )
    aligner_inputs = aligner_inputs.to(aligner_model.device, aligner_model.dtype)
    with torch_module.inference_mode():
        outputs = aligner_model(**aligner_inputs)
    timestamps = aligner_processor.decode_forced_alignment(
        logits=outputs.logits,
        input_ids=aligner_inputs["input_ids"],
        word_lists=word_lists,
        timestamp_token_id=aligner_model.config.timestamp_token_id,
    )[0]

    base = float(chunk["start_seconds"])
    retain_start = float(chunk["retain_start_seconds"])
    retain_end = float(chunk["retain_end_seconds"])
    word_rows: list[dict[str, Any]] = []
    for index, item in enumerate(timestamps):
        local_start = timestamp_value(item, "start_time", "start", "start_seconds")
        local_end = timestamp_value(item, "end_time", "end", "end_seconds")
        if local_start is None or local_end is None:
            continue
        full_start = base + local_start
        full_end = base + local_end
        word_rows.append(
            {
                "index": index,
                "chunk_id": chunk_id,
                "language": language,
                "text": item.get("text", ""),
                "chunk_start_seconds": f"{local_start:.3f}",
                "chunk_end_seconds": f"{local_end:.3f}",
                "start_seconds": f"{full_start:.3f}",
                "end_seconds": f"{full_end:.3f}",
                "start_ts": seconds_to_timestamp(full_start),
                "end_ts": seconds_to_timestamp(full_end),
                "retained_for_full_merge": str(retain_start <= full_start < retain_end),
            }
        )
    word_fields = [
        "index",
        "chunk_id",
        "language",
        "text",
        "chunk_start_seconds",
        "chunk_end_seconds",
        "start_seconds",
        "end_seconds",
        "start_ts",
        "end_ts",
        "retained_for_full_merge",
    ]
    write_csv(words_csv, word_rows, word_fields)
    retained_count = sum(row["retained_for_full_merge"] == "True" for row in word_rows)
    payload = {
        "chunk_id": chunk_id,
        "audio": str(wav_path.resolve()),
        "asr_model": ASR_MODEL_ID,
        "aligner_model": ALIGNER_MODEL_ID,
        "dtype": str(asr_model.dtype),
        "chunk_start_seconds": base,
        "chunk_end_seconds": float(chunk["end_seconds"]),
        "retain_start_seconds": retain_start,
        "retain_end_seconds": retain_end,
        "parsed_language": language,
        "raw": raw,
        "parsed": parsed,
        "transcription": transcription,
        "transcription_chars": len(transcription),
        "timestamp_count": len(timestamps),
        "retained_timestamp_count": retained_count,
        "timestamps": timestamps,
    }
    raw_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    gc.collect()
    if torch_module.cuda.is_available():
        torch_module.cuda.empty_cache()
    return payload


def merge_outputs(
    *,
    chunks: list[dict[str, Any]],
    payloads: list[dict[str, Any]],
    chunk_dir: Path,
    output_dir: Path,
    phrase_gap_seconds: float,
    phrase_duration_seconds: float,
) -> tuple[int, int]:
    chunk_rows: list[dict[str, Any]] = []
    word_rows: list[dict[str, Any]] = []
    full_index = 0
    for chunk, payload in zip(chunks, payloads, strict=True):
        chunk_rows.append(
            {
                "index": int(chunk["chunk_index"]),
                "chunk_id": chunk["chunk_id"],
                "language": payload.get("parsed_language", ""),
                "text": payload.get("transcription", ""),
                "start_seconds": f"{float(chunk['start_seconds']):.3f}",
                "end_seconds": f"{float(chunk['end_seconds']):.3f}",
                "start_ts": seconds_to_timestamp(float(chunk["start_seconds"])),
                "end_ts": seconds_to_timestamp(float(chunk["end_seconds"])),
                "retain_start_seconds": f"{float(chunk['retain_start_seconds']):.3f}",
                "retain_end_seconds": f"{float(chunk['retain_end_seconds']):.3f}",
                "transcription_chars": payload.get("transcription_chars", 0),
                "timestamp_count": payload.get("timestamp_count", 0),
                "retained_timestamp_count": payload.get("retained_timestamp_count", 0),
            }
        )
        path = chunk_dir / f"{chunk['chunk_id']}_words_fullvideo.csv"
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for source in csv.DictReader(handle):
                if source.get("retained_for_full_merge") != "True":
                    continue
                row = dict(source)
                row["index"] = full_index
                row.pop("retained_for_full_merge", None)
                word_rows.append(row)
                full_index += 1

    chunk_fields = list(chunk_rows[0].keys())
    word_fields = [
        "index",
        "chunk_id",
        "language",
        "text",
        "chunk_start_seconds",
        "chunk_end_seconds",
        "start_seconds",
        "end_seconds",
        "start_ts",
        "end_ts",
    ]
    write_csv(
        output_dir / "qwen3_full_asr_segments_or_chunks.csv", chunk_rows, chunk_fields
    )
    write_csv(output_dir / "qwen3_full_asr_words.csv", word_rows, word_fields)
    phrases = build_phrases(
        word_rows,
        max_gap_seconds=phrase_gap_seconds,
        max_duration_seconds=phrase_duration_seconds,
    )
    phrase_fields = [
        "index",
        "language",
        "text",
        "start_seconds",
        "end_seconds",
        "start_ts",
        "end_ts",
        "word_count",
    ]
    write_csv(output_dir / "qwen3_full_asr_phrases.csv", phrases, phrase_fields)
    (output_dir / "qwen3_full_asr_words.json").write_text(
        json.dumps(word_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "qwen3_full_asr_phrases.json").write_text(
        json.dumps(phrases, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(word_rows), len(phrases)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run full-video multilingual Qwen3 ASR plus forced word alignment."
    )
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chunk-seconds", type=float, default=240.0)
    parser.add_argument("--overlap-seconds", type=float, default=15.0)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--precision", choices=("bf16", "fp16"), default="bf16")
    parser.add_argument("--phrase-gap-seconds", type=float, default=0.90)
    parser.add_argument("--phrase-duration-seconds", type=float, default=8.0)
    parser.add_argument("--limit-chunks", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise FileNotFoundError("ffmpeg and ffprobe must be available on PATH")
    audio = args.audio.resolve()
    if not audio.is_file():
        raise FileNotFoundError(audio)
    output_dir = args.output_dir.resolve()
    chunk_dir = output_dir / "asr_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(audio)
    chunks = chunk_plan(duration, args.chunk_seconds, args.overlap_seconds)
    if args.limit_chunks:
        chunks = chunks[: args.limit_chunks]
    (output_dir / "qwen3_chunk_plan.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        import torch
        from transformers import (
            AutoModelForMultimodalLM,
            AutoModelForTokenClassification,
            AutoProcessor,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Qwen3 ASR requires torch and transformers in the active Python environment"
        ) from exc
    if not torch.cuda.is_available():
        raise RuntimeError("Full-video Qwen3 ASR requires CUDA")
    dtype = torch.bfloat16 if args.precision == "bf16" else torch.float16
    print(f"cuda=True precision={args.precision} chunks={len(chunks)}", flush=True)
    asr_processor = AutoProcessor.from_pretrained(ASR_MODEL_ID)
    asr_model = AutoModelForMultimodalLM.from_pretrained(
        ASR_MODEL_ID,
        dtype=dtype,
        device_map="auto",
    ).eval()
    aligner_processor = AutoProcessor.from_pretrained(ALIGNER_MODEL_ID)
    aligner_model = AutoModelForTokenClassification.from_pretrained(
        ALIGNER_MODEL_ID,
        dtype=dtype,
        device_map="auto",
    ).eval()
    payloads = [
        process_chunk(
            chunk=chunk,
            audio=audio,
            chunk_dir=chunk_dir,
            asr_processor=asr_processor,
            asr_model=asr_model,
            aligner_processor=aligner_processor,
            aligner_model=aligner_model,
            torch_module=torch,
            max_new_tokens=args.max_new_tokens,
        )
        for chunk in chunks
    ]
    word_count, phrase_count = merge_outputs(
        chunks=chunks,
        payloads=payloads,
        chunk_dir=chunk_dir,
        output_dir=output_dir,
        phrase_gap_seconds=args.phrase_gap_seconds,
        phrase_duration_seconds=args.phrase_duration_seconds,
    )
    summary = {
        "audio": str(audio),
        "audio_duration_seconds": duration,
        "asr_model": ASR_MODEL_ID,
        "aligner_model": ALIGNER_MODEL_ID,
        "precision": args.precision,
        "fp8_allowed": False,
        "chunk_seconds": args.chunk_seconds,
        "overlap_seconds": args.overlap_seconds,
        "chunk_count": len(chunks),
        "word_count": word_count,
        "phrase_count": phrase_count,
    }
    (output_dir / "qwen3_asr_run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    word_rows = json.loads(
        (output_dir / "qwen3_full_asr_words.json").read_text(encoding="utf-8")
    )
    phrase_rows = json.loads(
        (output_dir / "qwen3_full_asr_phrases.json").read_text(encoding="utf-8")
    )
    languages = sorted(
        {
            str(row.get("language", "")).strip()
            for row in word_rows
            if str(row.get("language", "")).strip()
        }
    )
    command = subprocess.list2cmdline(
        [
            sys.executable,
            "qwen3_asr.py",
            "--audio",
            str(audio),
            "--output-dir",
            str(output_dir),
            "--precision",
            args.precision,
            "--chunk-seconds",
            str(args.chunk_seconds),
            "--overlap-seconds",
            str(args.overlap_seconds),
            "--max-new-tokens",
            str(args.max_new_tokens),
            "--phrase-gap-seconds",
            str(args.phrase_gap_seconds),
            "--phrase-duration-seconds",
            str(args.phrase_duration_seconds),
            "--limit-chunks",
            str(args.limit_chunks),
        ]
    )
    normalized = {
        "schema_version": "1.0",
        "provider": "qwen3",
        "model": ASR_MODEL_ID,
        "aligner_model": ALIGNER_MODEL_ID,
        "type": "local",
        "source": str(audio),
        "source_sha256": file_sha256(audio),
        "language": languages[0] if len(languages) == 1 else None,
        "languages": languages,
        "text": "\n".join(str(row.get("text", "")).strip() for row in phrase_rows).strip(),
        "segments": [
            {
                "text": str(row.get("text", "")).strip(),
                "start": float(row["start_seconds"]),
                "end": float(row["end_seconds"]),
            }
            for row in phrase_rows
            if str(row.get("text", "")).strip()
        ],
        "words": [
            {
                "text": str(row.get("text", "")).strip(),
                "start": float(row["start_seconds"]),
                "end": float(row["end_seconds"]),
                "confidence": None,
            }
            for row in word_rows
            if str(row.get("text", "")).strip()
        ],
        "raw_artifact": str((output_dir / "qwen3_asr_run_summary.json").resolve()),
        "command": command,
        "warnings": [],
        "fallback_trace": [
            {"provider": "qwen3", "status": "succeeded", "reason": ""}
        ],
    }
    (output_dir / "asr-result.json").write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
