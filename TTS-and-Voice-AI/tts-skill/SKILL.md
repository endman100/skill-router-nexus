---
name: tts-skill
description: Generate cloned narration for local videos, voice auditions, digital-human narration, and subtitle-ready audio. Default to the user-approved Taiwan high-school energetic technical female voice 07 through local ComfyUI Fish Audio S2 Pro. Treat canonical pause values as mandatory minima while allowing separately recorded editorial additions; never silently substitute another provider, model, reference, or voice.
---

# TTS Skill

Use the user-approved Fish Audio S2 Pro profile for local narration unless the user explicitly selects another voice.

## Hard routing rules

1. Read `references/fish-s2-default-voice.json` before every local voice audition or final narration render.
2. Use local ComfyUI `FishS2VoiceCloneTTS` with model `s2-pro-fp8` and voice ID `taiwan-highschool-female-07-fast`.
3. Use the configured complete 60.929-second mono 44.1 kHz lossless WAV and its exact transcript as the sole cloning reference. Do not use an MP3, extract a shortened clip, denoise it, or substitute another recording.
4. Verify the bundled WAV byte count and SHA-256 before synthesis. Copying the same bytes into ComfyUI input is allowed; transcoding the reference is not.
5. Do not silently fall back to Qwen3-TTS, IndexTTS2, MiniMax, browser speech, system voices, another Fish model, or another reference. Stop and report a missing node, model, reference, or server.
6. Preserve the display script separately from pronunciation-only aliases and Fish control tags. Keep approved product names and English tokens unchanged in captions.
7. For structured narration, require a canonical `narration.json` array in which every object contains exactly `text` then positive integer `pause_after_ms`. Treat `pause_after_ms` as the mandatory minimum silence after that unit. Make every deliberate audible pause one item; keep IDs, scene/page fields, pronunciation aliases, paths, seeds, and hashes outside this file.
8. Generate one lossless WAV per minimal narration item, then run `scripts/assemble_pcm_narration.py --narration ... --manifest ...` to insert every required `pause_after_ms` as deterministic PCM silence and create `pause-timing.json`. When pacing needs more room, pass a separate `pacing-overrides.json` with one-based `unit_index`, non-negative `extra_pause_ms`, and a concrete reason. Compute `effective_pause_ms = pause_after_ms + extra_pause_ms`; never reduce or replace the canonical minimum.
9. Master one canonical final WAV after pause assembly. Record reference hashes, settings, segment seeds, prompt IDs, pause policy, output hash, and `used_fallback=false` in `voice_manifest.json`.
10. Use the final mastered WAV as the only subtitle and animation clock. Run ASR or forced alignment against that exact file; never estimate production timestamps from character counts or raw TTS segment durations.
11. For a paid digital-human render, require user approval of the exact final narration first. Changing audio invalidates approval.

## Fish Audio S2 Pro lane

1. Verify ComfyUI at the host and port declared by the default profile.
2. Verify `FishS2VoiceCloneTTS`, `s2-pro-fp8`, and the complete lossless cloning WAV declared by the default profile.
3. Use the exact reference transcript from the profile. A mismatched transcript weakens cloning and is a hard failure.
4. Generate one pause unit at a time. Derive stable unit IDs in a production manifest, increment `seed_base` by unit index, and retain successful lossless segments for safe retries. Never store production IDs or seeds in canonical `narration.json`.
5. Default to `language=zh`, CUDA, float16, SDPA, max 1024 new tokens, chunk length 400, temperature 0.85, top-p 0.86, and repetition penalty 1.1.
6. Convert selected segments to mono 16-bit PCM WAV at 44.1 kHz. Assemble them with every narration item's required `pause_after_ms` and any validated non-negative editorial addition from `pacing-overrides.json`; never substitute generic sentence, page, or tail defaults. Normalize the combined narration to -16 LUFS with a -1.5 dB true-peak ceiling.
7. Run an unprompted ASR listen check for missing or substituted content, then run forced alignment against the exact display script for timestamps.

Validate the bundled default profile after changing its metadata or audio asset:

```bash
python scripts/validate_fish_s2_profile.py
```

For mixed Chinese and English, also read `references/pronunciation-lexicon.json`. A user-approved pronunciation overrides generic heuristics.

## Explicit alternative lanes

- Use `references/qwen3-default-voice.json` and validate it with `scripts/validate_qwen3_tts_profile.py` only when the user explicitly requests Qwen3-TTS VoiceClone.
- Use `scripts/generate_indextts2_narration.py` only when the user explicitly requests IndexTTS2 or its legacy Pluviobyte voice.
- Use `references/minimax-relay-article.md` and `assets/minimax_tts.py` only for a public article or tutorial that explicitly demonstrates the MiniMax relay.

None of these lanes is a fallback for Fish Audio S2 Pro.

## QC gate

Before narration delivery, require:

- provider, model, node, voice ID, and reference hash match `references/fish-s2-default-voice.json`;
- the complete cloning reference is the configured mono 44.1 kHz 16-bit PCM WAV, lasts 60.929 seconds, and matches both its exact transcript and expected SHA-256;
- canonical narration has exactly `text` and `pause_after_ms` per item and reconstructs the approved script;
- `pause-timing.json` records every required minimum, editorial addition, effective pause, and reason exactly once;
- the final narration is lossless before video encoding;
- `used_fallback=false`;
- final integrated loudness is near -16 LUFS and true peak does not exceed -1.5 dBFS;
- ASR contains the complete spoken content;
- caption/alignment QC passes against the exact final WAV;
- the video contains one canonical narration track beginning at zero.
