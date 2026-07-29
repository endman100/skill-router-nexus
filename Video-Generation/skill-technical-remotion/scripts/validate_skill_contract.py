#!/usr/bin/env python3
"""Validate the non-article audio-first production contract in this skill."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
SKILL = ROOT / "SKILL.md"
REFERENCE = ROOT / "references" / "production-contract.md"
TTS_ROOT = REPO_ROOT / "TTS-and-Voice-AI" / "tts-skill"
VOICE_PROFILE = TTS_ROOT / "references" / "fish-s2-default-voice.json"


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    skill = SKILL.read_text(encoding="utf-8")
    reference = REFERENCE.read_text(encoding="utf-8")

    require(
        re.search(r"^name: skill-technical-remotion$", skill, re.MULTILINE) is not None,
        "frontmatter name is missing or incorrect",
        failures,
    )
    require("skill-writing-technical-shorts" in skill, "Short article routing is missing", failures)
    require("REQUIRED CONDITIONAL SUB-SKILL" in skill, "Short routing is not conditional/explicit", failures)
    require("tts-skill" in skill, "Fish S2 TTS sub-skill routing is missing", failures)
    require("plan-geometric-explainer-video" in skill, "Remotion planning sub-skill routing is missing", failures)
    require("verification-before-completion" in skill, "completion verification routing is missing", failures)
    require("Qwen/Qwen3-ASR-0.6B" in skill, "unprompted Qwen listen check is missing", failures)
    require("Qwen/Qwen3-ForcedAligner-0.6B" in skill, "Qwen forced alignment is missing", failures)
    require("final-narration.wav" in skill, "canonical final WAV is missing", failures)
    require("used_fallback=false" in skill, "fallback prohibition is missing", failures)
    require("Do not infer semantic timings" in skill, "estimated timing prohibition is missing", failures)
    require("production-contract.md" in skill and REFERENCE.exists(), "production contract reference is missing", failures)
    require(
        "../../TTS-and-Voice-AI/tts-skill/references/fish-s2-default-voice.json" in skill and VOICE_PROFILE.exists(),
        "shared TTS voice profile is missing",
        failures,
    )

    order = [
        skill.find("Lock the display script"),
        skill.find("Generate scene audio"),
        skill.find("Listen before aligning"),
        skill.find("Force-align the locked audio"),
        skill.find("Build one timing truth"),
        skill.find("Implement Remotion scenes"),
        skill.find("Review stills first"),
        skill.find("Render and verify"),
    ]
    require(all(index >= 0 for index in order) and order == sorted(order), "audio-first phase order is invalid", failures)

    required_artifacts = {
        "voice_manifest.json",
        "final-narration.wav",
        "asr-listen-check.json",
        "qwen-forced-aligner-raw.json",
        "captions.json",
        "captions.srt",
        "animation-cues.json",
        "timing.generated.json",
        "caption-qc.json",
        "sync-validation.json",
    }
    missing = sorted(name for name in required_artifacts if name not in reference)
    require(not missing, f"production contract is missing artifacts: {missing}", failures)

    if VOICE_PROFILE.exists():
        profile = json.loads(VOICE_PROFILE.read_text(encoding="utf-8"))
        require(profile.get("voice_id") == "taiwan-highschool-female-07-fast", "bundled voice ID is incorrect", failures)
        require(profile.get("model") == "s2-pro-fp8", "bundled Fish S2 model is incorrect", failures)
        require(profile.get("reference_mode") == "full-lossless-wav", "full lossless WAV mode is not selected", failures)
        assets = profile.get("assets", {})
        require(set(assets) == {"cloning_wav"}, "voice profile must declare only cloning_wav", failures)

        record = assets.get("cloning_wav", {})
        relative_path = record.get("path", "")
        asset = TTS_ROOT / relative_path
        require(bool(relative_path) and not Path(relative_path).is_absolute(), "cloning_wav path must be relative", failures)
        require(asset.is_file(), "cloning_wav file is missing", failures)
        if asset.is_file():
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            require(digest == record.get("sha256"), "cloning_wav SHA-256 mismatch", failures)
            require(asset.stat().st_size == record.get("bytes"), "cloning_wav byte count mismatch", failures)
            with wave.open(str(asset), "rb") as wav:
                duration = wav.getnframes() / wav.getframerate()
                require(wav.getnchannels() == 1, "cloning WAV must be mono", failures)
                require(wav.getframerate() == 44100, "cloning WAV must be 44.1 kHz", failures)
                require(wav.getsampwidth() == 2, "cloning WAV must be 16-bit PCM", failures)
                require(wav.getcomptype() == "NONE", "cloning WAV must be uncompressed PCM", failures)
                require(abs(duration - profile.get("reference_audio_duration_seconds", 0)) < 0.001, "cloning WAV duration mismatch", failures)

        audio_dir = TTS_ROOT / "assets" / "reference-audio"
        bundled_files = sorted(path.name for path in audio_dir.iterdir() if path.is_file())
        require(bundled_files == ["taiwan-highschool-female-07-fast-lossless.wav"], "reference-audio must contain only the full lossless WAV", failures)
        require(not any(path.suffix.lower() == ".mp3" for path in audio_dir.iterdir()), "MP3 reference must not be bundled", failures)
        require(not any("clip" in path.name.lower() for path in audio_dir.iterdir()), "shortened reference clip must not be bundled", failures)
        reference_text = profile.get("reference_text", "")
        require("第三個步驟" in reference_text and "快速排查不是靠猜測" in reference_text, "full 60-second reference transcript is missing", failures)
        require("[" not in reference_text and "]" not in reference_text, "reference transcript must not contain Fish control tags", failures)

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    print("[PASS] skill-technical-remotion contract")
    print(f"[PASS] required artifacts: {len(required_artifacts)}")
    print("[PASS] shared TTS Fish S2 reference audio: full 60-second lossless WAV only")
    print("[PASS] Short writing is conditionally delegated; production remains audio-first")
    return 0


if __name__ == "__main__":
    sys.exit(main())
