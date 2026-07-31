#!/usr/bin/env python3
"""Validate the portable explicit Qwen3-TTS alternative profile and reference audio."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "references" / "qwen3-default-voice.json"
ASSEMBLER = ROOT / "scripts" / "assemble_pcm_narration.py"
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?:^|[\"'])(?:[a-z]:[/\\])")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def probe_audio(path: Path) -> dict[str, object]:
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(output)
    stream = payload["streams"][0]
    return {
        "codec": stream["codec_name"],
        "sample_rate": int(stream["sample_rate"]),
        "channels": int(stream["channels"]),
        "duration_seconds": float(payload["format"]["duration"]),
        "bytes": int(payload["format"]["size"]),
    }


def main() -> int:
    failures: list[str] = []
    raw = PROFILE.read_text(encoding="utf-8")
    profile = json.loads(raw)

    require(
        not WINDOWS_ABSOLUTE_PATH.search(raw),
        "profile contains a machine-specific absolute path",
        failures,
    )
    require(
        profile.get("provider") == "comfyui-qwen3-tts-voiceclone",
        "Qwen3-TTS provider is incorrect",
        failures,
    )
    require(
        profile.get("voice_id")
        == "qwen3-voice-design-06-playful-club-fullprompt-t070",
        "voice ID is incorrect",
        failures,
    )
    require(
        profile.get("model") == "Qwen3-TTS-12Hz-1.7B-Base",
        "Qwen3-TTS model is incorrect",
        failures,
    )
    require(
        profile.get("comfyui", {}).get("node") == "FB_Qwen3TTSVoiceClone",
        "Qwen3-TTS ComfyUI node is incorrect",
        failures,
    )
    require(
        profile.get("reference_mode") == "full-prompt-audio",
        "full-prompt reference mode is not selected",
        failures,
    )

    assets = profile.get("assets", {})
    require(set(assets) == {"cloning_audio"}, "profile must declare only cloning_audio", failures)
    record = assets.get("cloning_audio", {})
    relative_path = record.get("path", "")
    asset = ROOT / relative_path
    require(
        bool(relative_path) and not Path(relative_path).is_absolute(),
        "cloning_audio path must be relative",
        failures,
    )
    require(asset.is_file(), "cloning reference audio is missing", failures)
    if asset.is_file():
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        require(digest == record.get("sha256"), "cloning audio SHA-256 mismatch", failures)
        require(asset.stat().st_size == record.get("bytes"), "cloning audio byte count mismatch", failures)
        info = probe_audio(asset)
        expected = profile.get("reference_audio_format", {})
        require(info["codec"] == expected.get("codec") == "flac", "cloning audio must be FLAC", failures)
        require(info["channels"] == expected.get("channels") == 1, "cloning audio must be mono", failures)
        require(
            info["sample_rate"] == expected.get("sample_rate") == 24000,
            "cloning audio must be 24 kHz",
            failures,
        )
        require(
            abs(float(info["duration_seconds"]) - profile.get("reference_audio_duration_seconds", 0))
            < 0.001,
            "cloning audio duration mismatch",
            failures,
        )

    require(
        profile.get("reference_audio_input") == "codex_voice_design_06-playful-club-raw.flac",
        "ComfyUI reference input filename is incorrect",
        failures,
    )
    reference_text = profile.get("reference_text", "")
    require(
        reference_text.startswith("嗨，我是今天的校園科技小主播。")
        and reference_text.endswith("陪你認識人工智慧。"),
        "complete reference transcript is missing",
        failures,
    )

    generation = profile.get("generation", {})
    expected_generation = {
        "model_choice": "1.7B",
        "language": "Chinese",
        "device": "cuda",
        "precision": "bf16",
        "attention": "sdpa",
        "max_new_tokens": 2048,
        "temperature": 0.7,
        "top_p": 0.75,
        "top_k": 20,
        "repetition_penalty": 1.05,
        "x_vector_only": False,
        "candidate_seeds": [47243, 52901, 88617],
        "segment_unit": "pause-unit",
    }
    for key, expected in expected_generation.items():
        require(generation.get(key) == expected, f"generation.{key} is incorrect", failures)

    pause_policy = profile.get("pause_policy", {})
    require(
        pause_policy.get("implementation") == "pcm-silence-after-segment-render",
        "PCM pause implementation is missing",
        failures,
    )
    require(
        pause_policy.get("production_pause_authority")
        == "narration.json[].pause_after_ms",
        "canonical production pause authority is missing",
        failures,
    )
    require(
        pause_policy.get("production_extra_pause_policy")
        == "optional-pacing-overrides-nonnegative-only",
        "editorial extra pause policy is missing",
        failures,
    )
    require(
        pause_policy.get("production_gap_defaults_allowed") is False,
        "profile gap defaults must be forbidden for production",
        failures,
    )
    require(profile.get("fallback_allowed") is False, "fallback must be forbidden", failures)
    require(ASSEMBLER.is_file(), "PCM narration assembler is missing", failures)

    audio_dir = ROOT / "assets" / "reference-audio"
    bundled_files = sorted(path.name for path in audio_dir.iterdir() if path.is_file())
    require(
        "qwen3-voice-design-06-playful-club-raw.flac" in bundled_files,
        "canonical Qwen3 reference is not bundled",
        failures,
    )
    require(
        not any(path.suffix.lower() == ".mp3" for path in audio_dir.iterdir()),
        "lossy MP3 references must not be bundled",
        failures,
    )

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    print("[PASS] portable explicit Qwen3-TTS alternative profile")
    print("[PASS] canonical 17.28-second full-prompt FLAC metadata and hash")
    print("[PASS] Qwen3-TTS 1.7B Base / FB_Qwen3TTSVoiceClone recipe")
    print("[PASS] production pause authority: narration.json[].pause_after_ms")
    print("[PASS] editorial extra pauses: optional, separate, and non-negative only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
