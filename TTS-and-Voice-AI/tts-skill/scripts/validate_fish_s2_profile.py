#!/usr/bin/env python3
"""Validate the portable default Fish Audio S2 voice profile and WAV."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "references" / "fish-s2-default-voice.json"
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?:^|[\"'])(?:[a-z]:[/\\])")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    raw = PROFILE.read_text(encoding="utf-8")
    profile = json.loads(raw)

    require(not WINDOWS_ABSOLUTE_PATH.search(raw), "profile contains a machine-specific absolute path", failures)
    require(profile.get("voice_id") == "taiwan-highschool-female-07-fast", "voice ID is incorrect", failures)
    require(profile.get("model") == "s2-pro-fp8", "Fish S2 model is incorrect", failures)
    require(profile.get("reference_mode") == "full-lossless-wav", "full lossless WAV mode is not selected", failures)

    assets = profile.get("assets", {})
    require(set(assets) == {"cloning_wav"}, "profile must declare only cloning_wav", failures)
    record = assets.get("cloning_wav", {})
    relative_path = record.get("path", "")
    asset = ROOT / relative_path
    require(bool(relative_path) and not Path(relative_path).is_absolute(), "cloning_wav path must be relative", failures)
    require(asset.is_file(), "cloning WAV is missing", failures)

    if asset.is_file():
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        require(digest == record.get("sha256"), "cloning WAV SHA-256 mismatch", failures)
        require(asset.stat().st_size == record.get("bytes"), "cloning WAV byte count mismatch", failures)
        with wave.open(str(asset), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
            require(wav.getnchannels() == 1, "cloning WAV must be mono", failures)
            require(wav.getframerate() == 44100, "cloning WAV must be 44.1 kHz", failures)
            require(wav.getsampwidth() == 2, "cloning WAV must be 16-bit PCM", failures)
            require(wav.getcomptype() == "NONE", "cloning WAV must be uncompressed PCM", failures)
            require(abs(duration - profile.get("reference_audio_duration_seconds", 0)) < 0.001, "cloning WAV duration mismatch", failures)

    audio_dir = ROOT / "assets" / "reference-audio"
    bundled_files = sorted(path.name for path in audio_dir.iterdir() if path.is_file()) if audio_dir.is_dir() else []
    require(bundled_files == ["taiwan-highschool-female-07-fast-lossless.wav"], "reference-audio must contain only the canonical WAV", failures)
    reference_text = profile.get("reference_text", "")
    require("第三個步驟" in reference_text and "快速排查不是靠猜測" in reference_text, "complete reference transcript is missing", failures)

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    print("[PASS] portable Fish S2 profile")
    print("[PASS] canonical 60-second lossless WAV metadata and hash")
    return 0


if __name__ == "__main__":
    sys.exit(main())
