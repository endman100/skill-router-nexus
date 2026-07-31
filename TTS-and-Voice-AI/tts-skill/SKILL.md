---
name: tts-skill
description: Generate cloned narration for local videos, voice auditions, digital-human narration, and subtitle-ready audio. Default to the user-approved playful school-tech host reference through local ComfyUI Qwen3-TTS VoiceClone. Treat canonical pause values as mandatory minima while allowing separately recorded editorial additions; never silently substitute another provider, model, or voice.
---

# TTS Skill

Use the user-approved Qwen3-TTS voice-clone profile for local narration unless the user explicitly selects another voice.

## Hard routing rules

1. Read `references/qwen3-default-voice.json` before every local voice audition or final narration render.
2. Use local ComfyUI `FB_Qwen3TTSVoiceClone` with model `Qwen3-TTS-12Hz-1.7B-Base` and voice ID `qwen3-voice-design-06-playful-club-fullprompt-t070`.
3. Use the configured complete 17.28-second lossless FLAC and its exact full transcript as the sole cloning reference. Keep `x_vector_only=false`; do not convert, trim, denoise, or substitute the recording.
4. The ComfyUI input file must be the same bytes as the bundled asset. Verify the SHA-256 before synthesis; copying the file into ComfyUI input is allowed, transcoding it is not.
5. Do not silently fall back to Fish Audio, IndexTTS2, MiniMax, browser speech, system voices, another Qwen3 model, or another reference. Stop and report a missing node, model, reference, or server.
6. Preserve the display script separately from pronunciation-only aliases or provider-specific control text. Keep approved product names and English tokens unchanged in captions.
7. For structured narration, require a canonical `narration.json` array in which every object contains exactly `text` then positive integer `pause_after_ms`. Treat `pause_after_ms` as the mandatory minimum silence after that unit, not an instruction to make every final gap exactly that duration. Make every deliberate audible pause one item. Keep IDs, scene/page fields, pronunciation aliases, paths, seeds, and hashes outside this file.
8. Generate one lossless WAV per minimal narration item, then run `scripts/assemble_pcm_narration.py --narration ... --manifest ...` to insert every required `pause_after_ms` as deterministic PCM silence and create `pause-timing.json`. When pacing benefits from more breathing room, pass a separate `pacing-overrides.json` containing one-based `unit_index`, non-negative `extra_pause_ms`, and a concrete reason such as comprehension, emphasis, source-preview reading, or scene hold. Compute `effective_pause_ms = pause_after_ms + extra_pause_ms`; never reduce, replace, or hide the canonical minimum. Page gaps and the final tail must already have their minima encoded in the applicable narration items; never add an unrelated global gap or fall back to profile defaults.
9. Master one canonical final WAV after pause assembly. Record reference hashes, settings, segment seeds, prompt IDs, pause policy, output hash, and `used_fallback=false` in `voice_manifest.json`.
10. Use the final mastered WAV as the only subtitle and animation clock. Run ASR or forced alignment against that exact file; never estimate production timestamps from character counts or raw TTS segment durations.
11. For a paid digital-human render, require user approval of the exact final narration first. Changing audio invalidates approval.

## Qwen3-TTS VoiceClone lane

1. Verify ComfyUI at the host and port declared by the default profile.
2. Verify `FB_Qwen3TTSVoiceClone`, `Qwen3-TTS-12Hz-1.7B-Base`, and the complete lossless full-prompt FLAC declared by the default profile.
3. Use the exact reference transcript from the profile with `x_vector_only=false`. A mismatched transcript changes the prompt conditioning and is a hard failure.
4. Generate one pause unit at a time. Derive stable unit IDs in a production manifest; never store them in canonical `narration.json`. Generate three candidates with the recorded seeds `47243`, `52901`, and `88617` when quality selection is required, and retain successful lossless segments for safe retries.
5. Default to `model_choice=1.7B`, `language=Chinese`, CUDA, bf16, SDPA, max 2048 new tokens, temperature 0.7, top-p 0.75, top-k 20, and repetition penalty 1.05.
6. Convert segments to mono PCM WAV at 44.1 kHz. Assemble them with the profile lead-in, every minimal narration item's required `pause_after_ms`, and any validated non-negative editorial addition from `pacing-overrides.json`; do not substitute the profile's generic sentence/page/tail defaults. Record required, extra, effective, and reason fields per unit. Then normalize the combined narration to -16 LUFS with a -1.5 dB true-peak ceiling.
7. Run an unprompted ASR listen check for missing or substituted content, then run forced alignment against the exact display script for timestamps.

Validate the bundled default profile after changing its metadata or audio asset:

```bash
python scripts/validate_qwen3_tts_profile.py
```

For mixed Chinese and English, also read `references/pronunciation-lexicon.json`. A user-approved pronunciation overrides generic heuristics.

## Explicit alternative lanes

- Use `references/fish-s2-default-voice.json` and validate it with `scripts/validate_fish_s2_profile.py` only when the user explicitly requests Fish Audio S2 Pro.
- Use `scripts/generate_indextts2_narration.py` only when the user explicitly requests IndexTTS2 or its legacy Pluviobyte voice.
- Use `references/minimax-relay-article.md` and `assets/minimax_tts.py` only for a public article or tutorial that explicitly demonstrates the MiniMax relay.

None of these lanes is a fallback for Qwen3-TTS.

## QC gate

Before narration delivery, require:

- provider, model, node, voice ID, and reference hash match `references/qwen3-default-voice.json`;
- the complete cloning reference is the configured mono 24 kHz lossless FLAC, lasts 17.28 seconds, and matches both its exact transcript and expected SHA-256;
- canonical narration has exactly `text` and `pause_after_ms` per item and reconstructs the approved script;
- `pause-timing.json` matches the final narration hash and records every required minimum, editorial addition, effective pause, and reason exactly once, without reducing a minimum or duplicating a page/tail gap;
- when the project defines visual page-gap allocation, its parts exactly fill the page-ending item's physical silence;
- the final narration is lossless before video encoding;
- `used_fallback=false`;
- final integrated loudness is near -16 LUFS and true peak does not exceed -1.5 dBFS;
- ASR contains the complete spoken content;
- caption/alignment QC passes against the exact final WAV;
- the video contains one canonical narration track beginning at zero.
