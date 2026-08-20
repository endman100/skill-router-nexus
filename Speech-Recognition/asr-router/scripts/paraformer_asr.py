#!/usr/bin/env python3
"""Canonical DashScope Paraformer adapter for ASR Router."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


TRANSCRIPTION_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_config(explicit: Path | None) -> tuple[dict[str, str], Path | None]:
    config = dict(os.environ)
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit.expanduser())
    for origin in (Path.cwd(), Path(__file__).resolve()):
        current = origin if origin.is_dir() else origin.parent
        for parent in (current, *current.parents):
            candidate = parent / ".env"
            if candidate not in candidates:
                candidates.append(candidate)
    used = None
    for candidate in candidates:
        values = parse_env(candidate)
        for key, value in values.items():
            config.setdefault(key, value)
        if used is None and (values.get("DASHSCOPE_API_KEY") or values.get("PARAFORMER_API_KEY")):
            used = candidate
    return config, used


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method.upper())
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    if data is not None and not request.has_header("Content-Type"):
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DashScope HTTP {exc.code}: {body[:500]}") from exc


def headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def collect_text(result: Any) -> str:
    if not isinstance(result, dict):
        return ""
    if isinstance(result.get("text"), str):
        return result["text"].strip()
    parts: list[str] = []
    for key in ("transcripts", "sentences"):
        for item in result.get(key) or []:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"].strip())
    return "\n".join(part for part in parts if part)


def milliseconds_to_seconds(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number / 1000.0


def seconds_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def item_time(
    item: dict[str, Any],
    millisecond_keys: tuple[str, ...],
    second_keys: tuple[str, ...],
) -> float | None:
    for key in millisecond_keys:
        if key in item:
            return milliseconds_to_seconds(item.get(key))
    for key in second_keys:
        if key in item:
            return seconds_value(item.get(key))
    return None


def collect_segments(result: Any) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    candidates: list[Any] = list(result.get("sentences") or [])
    for transcript in result.get("transcripts") or []:
        if isinstance(transcript, dict):
            candidates.extend(transcript.get("sentences") or [])
    segments: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            continue
        start = item_time(item, ("begin_time", "start_time"), ("start",))
        end = item_time(item, ("end_time",), ("end",))
        segment: dict[str, Any] = {"text": str(item["text"]).strip()}
        if start is not None:
            segment["start"] = round(start, 3)
        if end is not None:
            segment["end"] = round(end, 3)
        segments.append(segment)
    return segments


def collect_words(result: Any) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    containers: list[Any] = [result]
    containers.extend(result.get("transcripts") or [])
    containers.extend(result.get("sentences") or [])
    words: list[dict[str, Any]] = []
    for container in containers:
        if not isinstance(container, dict):
            continue
        for item in container.get("words") or []:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", item.get("word", ""))).strip()
            start = item_time(item, ("begin_time", "start_time"), ("start",))
            end = item_time(item, ("end_time",), ("end",))
            if not text or start is None or end is None or start < 0 or end < start:
                continue
            confidence = item.get("confidence")
            words.append(
                {
                    "text": text,
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "confidence": float(confidence) if confidence is not None else None,
                }
            )
    return words


def transcribe(
    media_url: str,
    api_key: str,
    model: str,
    poll_interval: int,
    timeout: int,
) -> tuple[str, dict[str, Any]]:
    submit = http_json(
        "POST",
        TRANSCRIPTION_URL,
        headers={**headers(api_key), "X-DashScope-Async": "enable"},
        payload={"model": model, "input": {"file_urls": [media_url]}},
    )
    task_id = submit.get("output", {}).get("task_id") if isinstance(submit, dict) else ""
    if not task_id:
        raise RuntimeError(f"Paraformer task_id not found: {submit}")
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() <= deadline:
        query = http_json(
            "GET",
            TASK_URL.format(task_id=task_id),
            headers=headers(api_key),
        )
        last = query if isinstance(query, dict) else {}
        output = last.get("output", {})
        status = output.get("task_status") or last.get("task_status")
        if status in {"FAILED", "CANCELED"}:
            raise RuntimeError(f"Paraformer task {status}: {last}")
        if status == "SUCCEEDED":
            results = output.get("results") or output.get("task_results") or []
            result_url = results[0].get("transcription_url", "") if results and isinstance(results[0], dict) else ""
            if not result_url:
                raise RuntimeError(f"Paraformer transcription_url not found: {last}")
            result = http_json("GET", result_url)
            if not collect_text(result):
                raise RuntimeError("Paraformer result contains no transcript text")
            return str(task_id), result
        time.sleep(poll_interval)
    raise RuntimeError(f"Paraformer transcription timed out after {timeout}s: {last}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Canonical DashScope Paraformer ASR adapter")
    parser.add_argument("media_url", nargs="?")
    parser.add_argument("--model", default="paraformer-v2")
    parser.add_argument("--output", type=Path, default=Path("paraformer-result.json"))
    parser.add_argument("--poll-interval", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--doctor", action="store_true")
    args = parser.parse_args()

    config, env_file = load_config(args.env_file)
    api_key = config.get("DASHSCOPE_API_KEY") or config.get("PARAFORMER_API_KEY", "")
    if args.doctor:
        payload = {
            "dashscope_api_key": bool(api_key),
            "model": args.model,
            "env_file": str(env_file) if env_file else None,
            "ready": bool(api_key),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(0 if payload["ready"] else 1)
    if not args.media_url:
        parser.error("media_url is required unless --doctor is used")
    if not args.media_url.startswith(("http://", "https://")):
        parser.error("media_url must be reachable over HTTP(S)")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY/PARAFORMER_API_KEY is missing")

    task_id, raw_result = transcribe(
        args.media_url, api_key, args.model, args.poll_interval, args.timeout
    )
    payload = {
        "schema_version": "1.0",
        "provider": "paraformer",
        "model": args.model,
        "type": "api",
        "source": args.media_url,
        "source_sha256": None,
        "language": raw_result.get("language") if isinstance(raw_result, dict) else None,
        "text": collect_text(raw_result),
        "segments": collect_segments(raw_result),
        "words": collect_words(raw_result),
        "raw_artifact": str(args.output.expanduser().resolve()),
        "command": (
            f"python paraformer_asr.py {args.media_url} --model {args.model} "
            f"--output {args.output.expanduser().resolve()}"
        ),
        "task_id": task_id,
        "warnings": [],
        "fallback_trace": [{"provider": "paraformer", "status": "succeeded", "reason": ""}],
        "raw_result": raw_result,
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
