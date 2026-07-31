#!/usr/bin/env python3
"""Validate the non-article audio-first production contract in this skill."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
SKILL = ROOT / "SKILL.md"
REFERENCE = ROOT / "references" / "production-contract.md"
TTS_ROOT = REPO_ROOT / "TTS-and-Voice-AI" / "tts-skill"
VOICE_PROFILE = TTS_ROOT / "references" / "qwen3-default-voice.json"
ASSEMBLER = TTS_ROOT / "scripts" / "assemble_pcm_narration.py"
PREPARE_NARRATION = ROOT / "scripts" / "prepare_minimal_narration.py"
MATERIALIZE_NARRATION = ROOT / "scripts" / "materialize_narration_manifest.py"
BUILD_MOTION_REVIEW = ROOT / "scripts" / "build_motion_review.py"
EXTRACT_REVIEW_STILLS = ROOT / "scripts" / "extract_review_stills_from_video.py"


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def probe_audio(path: Path) -> dict[str, object]:
    payload = json.loads(
        subprocess.check_output(
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
    )
    stream = payload["streams"][0]
    return {
        "codec": stream["codec_name"],
        "sample_rate": int(stream["sample_rate"]),
        "channels": int(stream["channels"]),
        "duration_seconds": float(payload["format"]["duration"]),
        "bytes": int(payload["format"]["size"]),
    }


def validate_minimal_pipeline(failures: list[str]) -> None:
    try:
        with tempfile.TemporaryDirectory(prefix="technical-remotion-contract-") as raw_tmp:
            temp = Path(raw_tmp)
            script_path = temp / "approved-script.txt"
            narration_path = temp / "narration.json"
            scenes_path = temp / "scenes.json"
            overrides_path = temp / "pronunciation-overrides.json"
            pacing_path = temp / "pacing-overrides.json"
            production_path = temp / "narration.production.json"
            manifest_path = temp / "segments-manifest.json"
            output_path = temp / "final.wav"
            timing_path = temp / "pause-timing.json"

            script_path.write_text("第一段，第二段；第三段。\n", encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(PREPARE_NARRATION),
                    "build",
                    "--script",
                    str(script_path),
                    "--narration",
                    str(narration_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            narration = json.loads(narration_path.read_text(encoding="utf-8"))
            require(
                [list(item) for item in narration]
                == [["text", "pause_after_ms"]] * 3,
                "minimal narration builder emitted extra or reordered fields",
                failures,
            )
            require(
                [item["pause_after_ms"] for item in narration] == [280, 360, 700],
                "minimal narration default pause values are incorrect",
                failures,
            )

            scenes_path.write_text(
                json.dumps(
                    [
                        {
                            "page_id": "01",
                            "chapter": "A",
                            "caption": "A",
                            "start_unit": 1,
                            "end_unit": 2,
                        },
                        {
                            "page_id": "02",
                            "chapter": "B",
                            "caption": "B",
                            "start_unit": 3,
                            "end_unit": 3,
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            overrides_path.write_text(
                json.dumps(
                    [{"unit_index": 2, "tts_text": "第二段落；"}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            pacing_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "policy": "minimum-plus-editorial-extra",
                        "max_extra_pause_ms": 600,
                        "units": [
                            {
                                "unit_index": 2,
                                "extra_pause_ms": 140,
                                "reason": "concept-comprehension",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(MATERIALIZE_NARRATION),
                    "--narration",
                    str(narration_path),
                    "--scenes",
                    str(scenes_path),
                    "--pronunciation-overrides",
                    str(overrides_path),
                    "--output",
                    str(production_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            production = json.loads(production_path.read_text(encoding="utf-8"))
            require(
                [item["id"] for item in production] == ["01-01", "01-02", "02-01"],
                "production narration IDs are not deterministically derived",
                failures,
            )
            require(
                "tts_text" not in production[0]
                and production[1].get("tts_text") == "第二段落；",
                "pronunciation overrides are not isolated in the derived manifest",
                failures,
            )

            segment_dir = temp / "segments"
            segment_dir.mkdir()
            manifest_segments = []
            for index, item in enumerate(production, start=1):
                audio_path = segment_dir / f"unit-{index:02d}.wav"
                with wave.open(str(audio_path), "wb") as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(44100)
                    audio.writeframes(b"\x00\x00" * 441)
                manifest_segments.append(
                    {
                        "id": item["id"],
                        "unit_index": index,
                        "page_id": item["page_id"],
                        "path": str(audio_path.relative_to(temp)),
                    }
                )
            manifest_path.write_text(
                json.dumps({"segments": manifest_segments}, ensure_ascii=False),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ASSEMBLER),
                    "--narration",
                    str(narration_path),
                    "--manifest",
                    str(manifest_path),
                    "--output",
                    str(output_path),
                    "--timing-output",
                    str(timing_path),
                    "--profile",
                    str(VOICE_PROFILE),
                    "--pacing-overrides",
                    str(pacing_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            timing = json.loads(timing_path.read_text(encoding="utf-8"))
            require(
                [item["pause_after"]["source_pause_after_ms"] for item in timing["segments"]]
                == [280, 360, 700],
                "PCM assembler did not preserve every required pause minimum",
                failures,
            )
            require(
                [item["pause_after"]["extra_pause_ms"] for item in timing["segments"]]
                == [0, 140, 0],
                "PCM assembler did not apply the selective editorial addition",
                failures,
            )
            require(
                [item["pause_after"]["effective_pause_after_ms"] for item in timing["segments"]]
                == [280, 500, 700],
                "PCM assembler effective pauses are not required plus extra",
                failures,
            )
            require(
                [item["pause_after"]["kind"] for item in timing["segments"]]
                == ["pause", "page", "tail"],
                "PCM assembler pause kinds are incorrect",
                failures,
            )
            require(
                timing["pause_policy"].get("profile_gap_defaults_used") is False,
                "PCM assembler used profile gap defaults",
                failures,
            )
            require(
                timing["pause_policy"].get("source_field")
                == "narration.json[].pause_after_ms-minimum-plus-pacing-overrides"
                and timing["pause_policy"].get("total_extra_pause_ms") == 140,
                "PCM assembler did not record its minimum-plus-editorial policy",
                failures,
            )
    except Exception as error:  # pragma: no cover - surfaced as contract output
        failures.append(f"minimal narration pipeline test failed: {error}")


def validate_video_review_pipeline(failures: list[str]) -> None:
    if not BUILD_MOTION_REVIEW.is_file() or not EXTRACT_REVIEW_STILLS.is_file():
        failures.append("rendered-video review scripts are missing")
        return
    try:
        with tempfile.TemporaryDirectory(prefix="technical-remotion-review-") as raw_tmp:
            temp = Path(raw_tmp)
            video_path = temp / "review.mp4"
            timing_path = temp / "timing.generated.json"
            motion_dir = temp / "motion-review"
            stills_dir = temp / "final-stills"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=108x192:rate=30:duration=2",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(video_path),
                ],
                check=True,
            )
            timing_path.write_text(
                json.dumps(
                    {
                        "composition": "contract-review",
                        "audioSha256": "test-audio",
                        "timingSource": "contract-test",
                        "scenes": [
                            {
                                "id": "01",
                                "start": 0.0,
                                "end": 1.0,
                                "speechStart": 0.1,
                                "speechEnd": 0.7,
                                "completedPageHold": [0.8, 0.95],
                                "visualCues": {"unit": 0.2},
                                "cues": {"page_enter": 0.0, "canonical": 0.3},
                            },
                            {
                                "id": "02",
                                "start": 1.0,
                                "end": 1.9,
                                "speechStart": 1.1,
                                "speechEnd": 1.6,
                                "completedPageHold": [1.7, 1.85],
                                "visualCues": {"unit": 1.2},
                                "cues": {"page_enter": 1.0, "canonical": 1.3},
                            },
                        ],
                        "captions": [
                            {
                                "sentence_id": "01-01",
                                "page_id": "01",
                                "start": 0.25,
                                "end": 0.65,
                                "text": "第一句，",
                            },
                            {
                                "sentence_id": "02-01",
                                "page_id": "02",
                                "start": 1.2,
                                "end": 1.6,
                                "text": "第二句。",
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(BUILD_MOTION_REVIEW),
                    "--video",
                    str(video_path),
                    "--timing",
                    str(timing_path),
                    "--output-dir",
                    str(motion_dir),
                    "--fps",
                    "2",
                    "--columns",
                    "2",
                    "--tile-width",
                    "54",
                    "--tile-height",
                    "96",
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(EXTRACT_REVIEW_STILLS),
                    "--video",
                    str(video_path),
                    "--timing",
                    str(timing_path),
                    "--output-dir",
                    str(stills_dir),
                    "--project-root",
                    str(temp),
                    "--width",
                    "54",
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            motion = json.loads(
                (motion_dir / "filmstrip-manifest.json").read_text(encoding="utf-8")
            )
            stills = json.loads(
                (stills_dir / "stills-manifest.json").read_text(encoding="utf-8")
            )
            expected_hash = hashlib.sha256(video_path.read_bytes()).hexdigest()
            require(
                motion.get("video_sha256") == expected_hash
                and motion.get("sample_rate_fps") == 2
                and len(motion.get("filmstrips", [])) == 2,
                "motion-review filmstrip manifest is incomplete or not bound to the video",
                failures,
            )
            require(
                stills.get("video_sha256") == expected_hash
                and stills.get("evidence_source")
                == "decoded-delivery-video-exact-frame-selection"
                and stills.get("sentence_animation_count") == 2,
                "final-MP4 still manifest is incomplete or not bound to the video",
                failures,
            )
            labels = {
                label
                for record in stills.get("records", [])
                for label in record.get("labels", [])
            }
            require(
                {
                    "scene-01-sentence-01-01-before",
                    "scene-01-sentence-01-01-after",
                    "scene-02-sentence-02-01-before",
                    "scene-02-sentence-02-01-after",
                }.issubset(labels),
                "final-MP4 still manifest lacks sentence before/after coverage",
                failures,
            )
    except Exception as error:  # pragma: no cover - surfaced as contract output
        failures.append(f"rendered-video review pipeline test failed: {error}")


def main() -> int:
    failures: list[str] = []
    skill = SKILL.read_text(encoding="utf-8")
    reference = REFERENCE.read_text(encoding="utf-8")

    validate_minimal_pipeline(failures)
    validate_video_review_pipeline(failures)

    require(
        re.search(r"^name: skill-technical-remotion$", skill, re.MULTILINE) is not None,
        "frontmatter name is missing or incorrect",
        failures,
    )
    require("skill-writing-technical-shorts" in skill, "Short article routing is missing", failures)
    require("REQUIRED CONDITIONAL SUB-SKILL" in skill, "Short routing is not conditional/explicit", failures)
    require("tts-skill" in skill, "Qwen3-TTS sub-skill routing is missing", failures)
    require("remotion-video-creation" in skill, "Short Remotion implementation sub-skill routing is missing", failures)
    require("plan-geometric-explainer-video" in skill, "landscape planning sub-skill routing is missing", failures)
    require("Do not route a Short through its 16:9 output contract" in skill, "Short/landscape routing conflict is unresolved", failures)
    require("verification-before-completion" in skill, "completion verification routing is missing", failures)
    require("Qwen/Qwen3-ASR-1.7B" in skill, "Qwen3 candidate/listen ASR is missing", failures)
    require("do not use Whisper" in skill, "Whisper prohibition is missing", failures)
    require("generate three candidates per pause unit" in skill, "three-candidate generation is missing", failures)
    require("normalized Pinyin syllable sequences" in skill, "pronunciation-equivalence gate is missing", failures)
    require("mean token log-probability" in skill, "Qwen confidence ranking is missing", failures)
    require("Qwen/Qwen3-ForcedAligner-0.6B" in skill, "Qwen forced alignment is missing", failures)
    require("final-narration.wav" in skill, "canonical final WAV is missing", failures)
    require("used_fallback=false" in skill, "fallback prohibition is missing", failures)
    require("Do not infer semantic timings" in skill, "estimated timing prohibition is missing", failures)
    require("assemble_pcm_narration.py" in skill and ASSEMBLER.exists(), "PCM narration assembler routing is missing", failures)
    require("exactly `text` then `pause_after_ms`" in skill, "strict two-field narration schema is missing", failures)
    require("`，；：。！？`" in skill, "deliberate Traditional Chinese pause boundaries are missing", failures)
    require("enumeration mark `、`" in skill, "enumeration-mark policy is missing", failures)
    require("reproduce the approved script exactly" in skill, "approved-script reconstruction gate is missing", failures)
    require(PREPARE_NARRATION.exists() and "prepare_minimal_narration.py" in skill, "minimal narration preparer is missing", failures)
    require(MATERIALIZE_NARRATION.exists() and "materialize_narration_manifest.py" in skill, "derived narration materializer is missing", failures)
    require("scenes.json" in skill and "pronunciation-overrides.json" in skill, "metadata separation is missing", failures)
    require("inferred default" in skill and "duplicated global gap" in skill, "pause fallback prohibition is missing", failures)
    require("pacing-overrides.json" in skill and "mandatory minimum" in skill, "minimum-plus-editorial pacing policy is missing", failures)
    require("0.90-second page gap" in skill, "page-gap policy is missing", failures)
    require("0.15 seconds minimum completed-page hold" in skill and "0.45 seconds transition" in skill and "0.30 seconds next-page pre-roll" in skill, "page-gap visual allocation is missing", failures)
    require("visual-animation-cues.json" in skill, "derived visual cue artifact is missing", failures)
    require("0.30–0.60-second semantic lead" in skill, "speech-anticipating cue policy is missing", failures)
    require("prove the WAV and SRT hashes are unchanged" in skill, "visual-only hash preservation gate is missing", failures)
    require("1080×1920 (9:16)" in skill, "vertical Short format gate is missing", failures)
    require("sentence-animation-map.json" in skill, "sentence animation mapping artifact is missing", failures)
    require("sentence-animation-qc.json" in skill, "sentence animation coverage QC is missing", failures)
    require("visual-semantic-qc.json" in skill, "visual semantic audit artifact is missing", failures)
    require("every minimal narration item" in skill, "per-narration-unit animation coverage is missing", failures)
    require("Subtitle changes, the global progress bar, ambient background motion, page transition, or a recurring card merely flying in do not count" in skill, "non-semantic animation exclusions are missing", failures)
    require("Trigger coverage proves only that a cue exists" in skill, "trigger coverage versus semantic meaning gate is missing", failures)
    require("No asset quota" in skill, "no-asset-quota policy is missing", failures)
    require("explained_by_sentence_ids" in skill and "visible_window_sentence_ids" in skill, "asset explanation-window fields are missing", failures)
    require("Source provenance is not semantic relevance" in skill, "asset provenance/relevance distinction is missing", failures)
    require("empty shell" in skill, "empty-shell semantic failure is missing", failures)
    require("before/after frames for every sentence animation" in skill, "per-sentence still review is missing", failures)
    require("motion-stability-qc.json" in skill and "1× speed" in skill, "continuous-motion review gate is missing", failures)
    require(
        BUILD_MOTION_REVIEW.exists()
        and "scripts/build_motion_review.py" in skill
        and "no less than 2 fps" in skill,
        "decoded per-scene motion filmstrip workflow is missing",
        failures,
    )
    require(
        EXTRACT_REVIEW_STILLS.exists()
        and "scripts/extract_review_stills_from_video.py" in skill
        and "decoded from that exact MP4" in skill,
        "final-MP4 exact-frame evidence workflow is missing",
        failures,
    )
    require(
        "blackdetect=d=0.5" in skill
        and "local 10 fps contact strip" in skill,
        "near-black transition detection workflow is missing",
        failures,
    )
    require(
        "outgoing fade" in skill and "non-overlapping incoming fade" in skill,
        "non-overlapping fade dead-zone prohibition is missing",
        failures,
    )
    require(
        "delivery MP4 SHA-256" in skill or "delivery location" in skill,
        "delivery-copy hash verification is missing",
        failures,
    )
    require("official-assets.json" in skill and "source video muted" in skill and "Label previews as official/source reference" in skill, "official-preview provenance gate is missing", failures)
    require("Do not alternate left/right entrances" in skill and "low-damping bounce" in skill, "stable-anchor motion prohibitions are missing", failures)
    require("production-contract.md" in skill and REFERENCE.exists(), "production contract reference is missing", failures)
    require(
        "../../TTS-and-Voice-AI/tts-skill/references/qwen3-default-voice.json" in skill and VOICE_PROFILE.exists(),
        "shared TTS voice profile is missing",
        failures,
    )

    order = [
        skill.find("Lock the display script"),
        skill.find("Separate production metadata"),
        skill.find("Generate pause-unit candidates"),
        skill.find("Select by pronunciation, then confidence"),
        skill.find("Assemble deterministic but editorial pacing"),
        skill.find("Listen before aligning"),
        skill.find("Force-align the locked audio"),
        skill.find("Build canonical and visual timing layers"),
        skill.find("Build sentence-animation coverage"),
        skill.find("Resolve format before layout"),
        skill.find("Implement Remotion scenes with stable anchors"),
        skill.find("Review the rendered motion before finalizing"),
        skill.find("Render and verify the delivered file"),
    ]
    require(all(index >= 0 for index in order) and order == sorted(order), "audio-first phase order is invalid", failures)

    required_artifacts = {
        "narration.json",
        "pacing-overrides.json",
        "scenes.json",
        "pronunciation-overrides.json",
        "voice_manifest.json",
        "candidate_selection_manifest.json",
        "final-narration.wav",
        "pause-timing.json",
        "asr-listen-check.json",
        "qwen-forced-aligner-raw.json",
        "captions.json",
        "captions.srt",
        "animation-cues.json",
        "visual-animation-cues.json",
        "sentence-animation-map.json",
        "sentence-animation-qc.json",
        "visual-semantic-qc.json",
        "stills-manifest.json",
        "filmstrip-manifest.json",
        "official-assets.json",
        "motion-stability-qc.json",
        "timing.generated.json",
        "caption-qc.json",
        "sync-validation.json",
    }
    missing = sorted(name for name in required_artifacts if name not in reference)
    require(not missing, f"production contract is missing artifacts: {missing}", failures)

    if VOICE_PROFILE.exists():
        profile = json.loads(VOICE_PROFILE.read_text(encoding="utf-8"))
        require(
            profile.get("provider") == "comfyui-qwen3-tts-voiceclone",
            "bundled Qwen3-TTS provider is incorrect",
            failures,
        )
        require(
            profile.get("voice_id")
            == "qwen3-voice-design-06-playful-club-fullprompt-t070",
            "bundled voice ID is incorrect",
            failures,
        )
        require(
            profile.get("model") == "Qwen3-TTS-12Hz-1.7B-Base",
            "bundled Qwen3-TTS model is incorrect",
            failures,
        )
        require(
            profile.get("comfyui", {}).get("node") == "FB_Qwen3TTSVoiceClone",
            "bundled Qwen3-TTS node is incorrect",
            failures,
        )
        require(
            profile.get("reference_mode") == "full-prompt-audio",
            "full-prompt reference mode is not selected",
            failures,
        )
        assets = profile.get("assets", {})
        require(set(assets) == {"cloning_audio"}, "voice profile must declare only cloning_audio", failures)

        record = assets.get("cloning_audio", {})
        relative_path = record.get("path", "")
        asset = TTS_ROOT / relative_path
        require(bool(relative_path) and not Path(relative_path).is_absolute(), "cloning_audio path must be relative", failures)
        require(asset.is_file(), "cloning_audio file is missing", failures)
        if asset.is_file():
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            require(digest == record.get("sha256"), "cloning_audio SHA-256 mismatch", failures)
            require(asset.stat().st_size == record.get("bytes"), "cloning_audio byte count mismatch", failures)
            info = probe_audio(asset)
            expected = profile.get("reference_audio_format", {})
            require(info["codec"] == expected.get("codec") == "flac", "cloning audio must be FLAC", failures)
            require(info["channels"] == expected.get("channels") == 1, "cloning audio must be mono", failures)
            require(info["sample_rate"] == expected.get("sample_rate") == 24000, "cloning audio must be 24 kHz", failures)
            require(
                abs(float(info["duration_seconds"]) - profile.get("reference_audio_duration_seconds", 0)) < 0.001,
                "cloning audio duration mismatch",
                failures,
            )

        audio_dir = TTS_ROOT / "assets" / "reference-audio"
        bundled_files = sorted(path.name for path in audio_dir.iterdir() if path.is_file())
        require(
            "qwen3-voice-design-06-playful-club-raw.flac" in bundled_files,
            "canonical Qwen3 reference audio is not bundled",
            failures,
        )
        require(not any(path.suffix.lower() == ".mp3" for path in audio_dir.iterdir()), "MP3 reference must not be bundled", failures)
        require(not any("clip" in path.name.lower() for path in audio_dir.iterdir()), "shortened reference clip must not be bundled", failures)
        reference_text = profile.get("reference_text", "")
        require(
            reference_text.startswith("嗨，我是今天的校園科技小主播。")
            and reference_text.endswith("陪你認識人工智慧。"),
            "full Qwen3 reference transcript is missing",
            failures,
        )
        require(
            profile.get("reference_audio_input")
            == "codex_voice_design_06-playful-club-raw.flac",
            "ComfyUI reference input filename is incorrect",
            failures,
        )
        require(profile.get("generation", {}).get("model_choice") == "1.7B", "Qwen3 model choice is incorrect", failures)
        require(profile.get("generation", {}).get("x_vector_only") is False, "full-prompt conditioning must remain enabled", failures)
        require(
            profile.get("generation", {}).get("candidate_seeds") == [47243, 52901, 88617],
            "Qwen3 candidate seeds are incorrect",
            failures,
        )
        require(profile.get("generation", {}).get("segment_unit") == "pause-unit", "TTS segment unit must be pause-unit", failures)
        require(
            profile.get("pause_policy", {}).get("production_extra_pause_policy")
            == "optional-pacing-overrides-nonnegative-only",
            "Qwen3 production extra-pause policy is incorrect",
            failures,
        )
        require(profile.get("fallback_allowed") is False, "TTS fallback must be forbidden", failures)

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    print("[PASS] skill-technical-remotion contract")
    print(f"[PASS] required artifacts: {len(required_artifacts)}")
    print("[PASS] shared Qwen3-TTS reference: complete 17.28-second lossless full-prompt FLAC")
    print("[PASS] narration schema: exact text + pause_after_ms with source reconstruction")
    print("[PASS] editorial pacing: required minima plus selective recorded additions")
    print("[PASS] visual timing: canonical Qwen cues plus 0.30-0.60s anticipatory cues")
    print("[PASS] Short format: true 1080x1920 portrait composition by default")
    print("[PASS] sentence motion: one visible semantic animation per narration unit")
    print("[PASS] visual semantics: every unit requires reviewed before/after meaning evidence")
    print("[PASS] stable motion: fixed anchors plus continuous 1x review contract")
    print("[PASS] rendered evidence: final-MP4 exact frames plus >=2 fps scene filmstrips")
    print("[PASS] transition QC: 0.5s black detection plus local 10 fps diagnosis")
    print("[PASS] delivery copy: SHA-256 must match the verified source render")
    print("[PASS] official previews: no quota, narrated relevance, bounded visibility, provenance")
    print("[PASS] candidate selection: three candidates, pronunciation gate, Qwen confidence")
    print("[PASS] Short writing is conditionally delegated; production remains audio-first")
    return 0


if __name__ == "__main__":
    sys.exit(main())
