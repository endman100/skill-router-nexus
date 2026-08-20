"""Canonical Volcengine Seed ASR adapter for ASR Router.

Extracts mono 16kHz audio with ffmpeg, submits it to Volcengine Recording File
Recognition, and writes raw plus normalized ASR Router artifacts.

Usage:
    python seed_asr.py <audio-or-video> --output raw.json --normalized-output asr-result.json
    python seed_asr.py <audio> --mode flash --output raw.json
    python seed_asr.py --doctor
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SUBMIT_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
QUERY_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
FLASH_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
DEFAULT_RESOURCES = {
    "seed": "volc.seedasr.auc",
    "standard": "volc.bigasr.auc",
    "flash": "volc.bigasr.auc_turbo",
}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            values[key] = value.strip().strip('"').strip("'")
    return values


def _env_candidates(explicit: Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit.expanduser())
    for origin in (Path.cwd(), Path(__file__).resolve()):
        current = origin if origin.is_dir() else origin.parent
        for parent in (current, *current.parents):
            candidate = parent / ".env"
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def load_config(explicit: Path | None = None) -> tuple[dict[str, str], Path | None]:
    config = dict(os.environ)
    used: Path | None = None
    for candidate in _env_candidates(explicit):
        values = _parse_env(candidate)
        for key, value in values.items():
            config.setdefault(key, value)
        if used is None and values.get("VOLCENGINE_API_KEY"):
            used = candidate
    return config, used


def load_api_key(explicit: Path | None = None) -> str:
    config, _ = load_config(explicit)
    value = config.get("VOLCENGINE_API_KEY", "")
    if not value:
        sys.exit("VOLCENGINE_API_KEY not found in workspace .env or environment")
    return value


def extract_audio(video_path: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(dest),
    ]
    subprocess.run(cmd, check=True)


def _api_request(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
) -> tuple[dict[str, Any], dict[str, str]]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            body = response.read().decode("utf-8", errors="replace")
            normalized_headers = {key.lower(): value for key, value in response.headers.items()}
            return (json.loads(body) if body else {}), normalized_headers
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Volcengine HTTP {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Volcengine request failed: {exc.reason}") from exc


def call_async(
    audio_path: Path,
    api_key: str,
    resource_id: str,
    num_speakers: int | None = None,
    poll_interval: int = 3,
    timeout: int = 900,
) -> dict[str, Any]:
    audio_bytes = audio_path.read_bytes()
    if len(audio_bytes) > 48 * 1024 * 1024:
        raise RuntimeError("Audio is larger than 48 MB; split or compress it before ASR")

    request_id = str(uuid.uuid4())
    payload = {
        "user": {"uid": "video-use"},
        "audio": {
            "data": base64.b64encode(audio_bytes).decode("ascii"),
            "format": audio_path.suffix.lower().lstrip(".") or "mp3",
        },
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": False,
            "show_utterances": True,
            "enable_speaker_info": bool(num_speakers and num_speakers > 1),
        },
    }
    common_headers = {
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "Content-Type": "application/json",
    }
    _, submit_headers = _api_request(
        SUBMIT_URL,
        payload,
        {**common_headers, "X-Api-Sequence": "-1"},
    )
    submit_status = submit_headers.get("x-api-status-code", "")
    if submit_status != "20000000":
        message = submit_headers.get("x-api-message", "")
        raise RuntimeError(f"Volcengine submit failed: status={submit_status or 'missing'} message={message}")

    query_headers = dict(common_headers)
    if submit_headers.get("x-tt-logid"):
        query_headers["X-Tt-Logid"] = submit_headers["x-tt-logid"]

    deadline = time.monotonic() + timeout
    while time.monotonic() <= deadline:
        time.sleep(poll_interval)
        result, response_headers = _api_request(QUERY_URL, {}, query_headers)
        query_status = response_headers.get("x-api-status-code", "")
        if query_status == "20000000":
            return result
        if query_status in {"", "20000001", "20000002"}:
            continue
        if query_status == "20000003":
            raise RuntimeError("Volcengine treated the audio as silent")
        message = response_headers.get("x-api-message", "")
        raise RuntimeError(f"Volcengine query failed: status={query_status} message={message}")
    raise RuntimeError(f"Volcengine ASR timed out after {timeout}s")


def call_flash(
    audio_path: Path,
    api_key: str,
    resource_id: str,
    num_speakers: int | None = None,
) -> dict[str, Any]:
    audio_bytes = audio_path.read_bytes()
    if len(audio_bytes) > 100 * 1024 * 1024:
        raise RuntimeError("Audio is larger than the 100 MB flash limit")
    request_id = str(uuid.uuid4())
    payload = {
        "user": {"uid": "asr-router"},
        "audio": {
            "data": base64.b64encode(audio_bytes).decode("ascii"),
            "format": audio_path.suffix.lower().lstrip(".") or "mp3",
        },
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": False,
            "show_utterances": True,
            "enable_speaker_info": bool(num_speakers and num_speakers > 1),
        },
    }
    result, headers = _api_request(
        FLASH_URL,
        payload,
        {
            "X-Api-Key": api_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": request_id,
            "X-Api-Sequence": "-1",
            "Content-Type": "application/json",
        },
    )
    status = headers.get("x-api-status-code", "")
    if status != "20000000":
        message = headers.get("x-api-message", "")
        raise RuntimeError(f"Volcengine flash failed: status={status or 'missing'} message={message}")
    return result


def normalize_volcengine_result(
    result: dict[str, Any],
    resource_id: str,
    requested_language: str | None = None,
    source: str | None = None,
    raw_artifact: str | None = None,
    command: str | None = None,
    source_sha256: str | None = None,
) -> dict[str, Any]:
    root = result.get("result", result)
    utterances = root.get("utterances") if isinstance(root, dict) else None
    if not isinstance(utterances, list):
        raise RuntimeError("Volcengine response has no result.utterances")

    words: list[dict[str, Any]] = []
    previous_end: float | None = None
    for utterance in utterances:
        if not isinstance(utterance, dict):
            continue
        utterance_speaker = utterance.get("speaker_id", utterance.get("speaker"))
        for word in utterance.get("words") or []:
            if not isinstance(word, dict):
                continue
            text = str(word.get("text", "")).strip()
            start_raw = word.get("start_time")
            end_raw = word.get("end_time")
            if not text or start_raw is None or end_raw is None:
                continue
            start = float(start_raw) / 1000.0
            end = float(end_raw) / 1000.0
            if start < 0 or end < start:
                continue
            if previous_end is not None and start - previous_end >= 0.2:
                words.append({
                    "text": "",
                    "start": round(previous_end, 3),
                    "end": round(start, 3),
                    "type": "spacing",
                })
            normalized_word: dict[str, Any] = {
                "text": text,
                "start": round(start, 3),
                "end": round(end, 3),
                "type": "word",
            }
            speaker = word.get("speaker_id", word.get("speaker", utterance_speaker))
            if speaker is not None:
                normalized_word["speaker_id"] = str(speaker)
            words.append(normalized_word)
            previous_end = max(previous_end or 0.0, end)

    if not any(word.get("type") == "word" for word in words):
        raise RuntimeError("Volcengine response has no usable word timestamps")

    transcript_text = str(root.get("text", "")).strip() if isinstance(root, dict) else ""
    detected_language = None
    if isinstance(root, dict):
        detected_language = root.get("language") or root.get("language_code")
    segments: list[dict[str, Any]] = []
    for utterance in utterances:
        if not isinstance(utterance, dict):
            continue
        text = str(utterance.get("text", "")).strip()
        start_raw = utterance.get("start_time", utterance.get("start"))
        end_raw = utterance.get("end_time", utterance.get("end"))
        if not text or start_raw is None or end_raw is None:
            continue
        start = float(start_raw) / 1000.0
        end = float(end_raw) / 1000.0
        if start >= 0 and end >= start:
            segments.append({"text": text, "start": round(start, 3), "end": round(end, 3)})

    return {
        "schema_version": "1.0",
        "provider": "seed-asr",
        "model": resource_id,
        "type": "api",
        "source": source,
        "source_sha256": source_sha256,
        "resource_id": resource_id,
        "language": detected_language,
        "requested_language": requested_language,
        "text": transcript_text,
        "segments": segments,
        "words": words,
        "raw_artifact": raw_artifact,
        "command": command,
        "warnings": [],
        "fallback_trace": [{"provider": "seed-asr", "status": "succeeded", "reason": ""}],
        "raw_result": result,
    }


def transcribe_source(
    source: Path,
    output: Path,
    normalized_output: Path | None,
    api_key: str,
    mode: str,
    resource_id: str,
    language: str | None = None,
    num_speakers: int | None = None,
    verbose: bool = True,
    poll_interval: int = 3,
    timeout: int = 900,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if normalized_output is not None:
        normalized_output.parent.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"  preparing audio from {source.name}", flush=True)

    started = time.time()
    with tempfile.TemporaryDirectory(prefix="video-use-volc-") as temp_name:
        if source.suffix.lower() in AUDIO_EXTS:
            audio = source
        else:
            audio = Path(temp_name) / f"{source.stem}.mp3"
            extract_audio(source, audio)
        if verbose:
            print(f"  submitting {audio.name} to Volcengine ASR ({mode})", flush=True)
        if mode == "flash":
            raw_result = call_flash(audio, api_key, resource_id, num_speakers=num_speakers)
        else:
            raw_result = call_async(
                audio,
                api_key,
                resource_id,
                num_speakers=num_speakers,
                poll_interval=poll_interval,
                timeout=timeout,
            )
    output.write_text(json.dumps(raw_result, ensure_ascii=False, indent=2), encoding="utf-8")
    source_hash = file_sha256(source)
    normalized_path = normalized_output or output
    command_parts = [
        "python",
        "seed_asr.py",
        str(source),
        "--mode",
        mode,
        "--resource-id",
        resource_id,
        "--output",
        str(output),
        "--normalized-output",
        str(normalized_path),
    ]
    if language:
        command_parts.extend(["--language", language])
    if num_speakers:
        command_parts.extend(["--num-speakers", str(num_speakers)])
    payload = normalize_volcengine_result(
        raw_result,
        resource_id,
        requested_language=language,
        source=str(source),
        raw_artifact=str(output),
        command=subprocess.list2cmdline(command_parts),
        source_sha256=source_hash,
    )
    if normalized_output is not None:
        normalized_output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if verbose:
        elapsed = time.time() - started
        word_count = sum(1 for word in payload["words"] if word.get("type") == "word")
        print(f"  saved: {output} ({word_count} words) in {elapsed:.1f}s")
    return normalized_output or output


def doctor(explicit_env: Path | None = None, mode: str = "seed") -> int:
    config, env_file = load_config(explicit_env)
    checks = {
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "volcengine_api_key": bool(config.get("VOLCENGINE_API_KEY")),
        "mode": mode,
        "resource_id": config.get("VOLCENGINE_RESOURCE_ID", DEFAULT_RESOURCES[mode]),
        "env_file": str(env_file) if env_file else None,
    }
    checks["ready"] = bool(checks["ffmpeg"] and checks["ffprobe"] and checks["volcengine_api_key"])
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if checks["ready"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Canonical Volcengine Seed ASR adapter")
    parser.add_argument("source", type=Path, nargs="?", help="Local audio or video file")
    parser.add_argument("--output", type=Path, default=Path("seed-asr-raw.json"))
    parser.add_argument("--normalized-output", type=Path, default=None)
    parser.add_argument("--mode", choices=tuple(DEFAULT_RESOURCES), default="seed")
    parser.add_argument("--resource-id", default=None)
    parser.add_argument("--language", type=str, default=None)
    parser.add_argument("--num-speakers", type=int, default=None)
    parser.add_argument("--poll-interval", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--doctor", action="store_true")
    args = parser.parse_args()

    if args.doctor:
        raise SystemExit(doctor(args.env_file, args.mode))
    if not args.source:
        parser.error("source is required unless --doctor is used")
    source = args.source.expanduser().resolve()
    if not source.is_file():
        sys.exit(f"source not found: {source}")
    config, _ = load_config(args.env_file)
    resource_id = args.resource_id or config.get("VOLCENGINE_RESOURCE_ID") or DEFAULT_RESOURCES[args.mode]
    transcribe_source(
        source=source,
        output=args.output.expanduser().resolve(),
        normalized_output=(args.normalized_output.expanduser().resolve() if args.normalized_output else None),
        api_key=load_api_key(args.env_file),
        mode=args.mode,
        resource_id=resource_id,
        language=args.language,
        num_speakers=args.num_speakers,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
