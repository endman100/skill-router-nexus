"""Import an Agent-produced ASR Router result into video-use's transcript cache."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_router_result(payload: Any, video: Path) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload.get("schema_version"):
        raise ValueError("input is not an ASR Router normalized result")
    if not payload.get("provider") or not payload.get("model"):
        raise ValueError("Router result is missing provider or model")
    words = payload.get("words")
    if not isinstance(words, list):
        raise ValueError("Router result is missing words")
    usable = [
        word
        for word in words
        if isinstance(word, dict)
        and str(word.get("text", "")).strip()
        and word.get("start") is not None
        and word.get("end") is not None
    ]
    if not usable:
        raise ValueError("video-use requires real word timestamps from asr-router")
    expected_hash = payload.get("source_sha256")
    if expected_hash and expected_hash != file_sha256(video):
        raise ValueError("Router result source_sha256 does not match the video")
    return payload


def transcribe_one(
    video: Path,
    edit_dir: Path,
    asr_result: Path | None = None,
    verbose: bool = True,
) -> Path:
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    output = transcripts_dir / f"{video.stem}.json"
    if output.exists():
        if verbose:
            print(f"cached: {output.name}")
        return output
    if asr_result is None:
        raise ValueError("invoke asr-router first and pass --asr-result")
    result_path = asr_result.expanduser().resolve()
    if not result_path.is_file():
        raise FileNotFoundError(result_path)
    payload = validate_router_result(
        json.loads(result_path.read_text(encoding="utf-8")),
        video,
    )
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if verbose:
        print(f"cached Router result: {output.name}")
    return output


def doctor() -> int:
    print("video-use does not execute an ASR provider directly.")
    print("The Agent must invoke asr-router and pass its normalized result here.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Import an ASR Router result into video-use")
    parser.add_argument("video", type=Path, nargs="?")
    parser.add_argument("--edit-dir", type=Path, default=None)
    parser.add_argument("--asr-result", type=Path, default=None)
    parser.add_argument("--doctor", action="store_true")
    args = parser.parse_args()
    if args.doctor:
        raise SystemExit(doctor())
    if not args.video:
        parser.error("video is required unless --doctor is used")
    video = args.video.expanduser().resolve()
    if not video.is_file():
        raise SystemExit(f"video not found: {video}")
    edit_dir = (args.edit_dir or video.parent / "edit").expanduser().resolve()
    transcribe_one(video, edit_dir, asr_result=args.asr_result)


if __name__ == "__main__":
    main()
