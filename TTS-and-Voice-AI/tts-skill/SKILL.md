---
name: tts-skill
description: Generate cloned narration for local videos, voice auditions, digital-human narration, and subtitle-ready audio. Default to the user-approved Taiwan high-school energetic technical female voice 07 through local ComfyUI Fish Audio S2 Pro. Use the lossless canonical reference and final-audio timestamps; never silently substitute another provider or voice.
---

# TTS Skill

Use the user-approved Fish Audio S2 Pro profile for local narration unless the user explicitly selects another voice.

## Hard routing rules

1. Read `references/fish-s2-default-voice.json` before every local voice audition or final narration render.
2. Use local ComfyUI `FishS2VoiceCloneTTS` with model `s2-pro-fp8` and voice ID `taiwan-highschool-female-07-fast`.
3. Use the configured complete 60-second lossless WAV as the sole cloning reference. Do not use an MP3, extract a shortened clip, or substitute another recording.
4. Do not silently fall back to IndexTTS2, MiniMax, browser speech, system voices, or another Fish reference. Stop and report a missing node, model, reference, or server.
5. Preserve the display script separately from Fish control tags. Keep approved product names and English tokens unchanged in captions.
6. Generate scene-sized lossless segments, then concatenate and master one canonical final WAV. Record reference hashes, settings, segment seeds, prompt IDs, output hash, and `used_fallback=false` in `voice_manifest.json`.
7. Use the final mastered WAV as the only subtitle and animation clock. Run ASR or forced alignment against that exact file; never estimate production timestamps from character counts or TTS segment durations.
8. For a paid digital-human render, require user approval of the exact final narration first. Changing audio invalidates approval.

## Fish Audio S2 Pro lane

1. Verify ComfyUI at the host and port declared by the default profile.
2. Verify `FishS2VoiceCloneTTS`, `s2-pro-fp8`, and the complete lossless cloning WAV declared by the default profile.
3. Use the exact reference transcript from the profile. A mismatched transcript weakens cloning and is a hard failure.
4. Generate one scene at a time. Increment `seed_base` by scene index and retain successful lossless segments for safe retries.
5. Default to `language=zh`, CUDA, float16, SDPA, temperature 0.85, top-p 0.86, and repetition penalty 1.1.
6. Convert segments to mono PCM WAV at 44.1 kHz. Add production pauses, then normalize the combined narration to -16 LUFS with a -1.5 dB true-peak ceiling.
7. Run an unprompted ASR listen check for missing or substituted content, then run forced alignment against the exact display script for timestamps.

Validate the bundled default profile after changing its metadata or audio asset:

```bash
python scripts/validate_fish_s2_profile.py
```

For mixed Chinese and English, also read `references/pronunciation-lexicon.json`. A user-approved pronunciation overrides generic heuristics.

## Explicit alternative lanes

- Use `scripts/generate_indextts2_narration.py` only when the user explicitly requests IndexTTS2 or its legacy Pluviobyte voice.
- Use `references/minimax-relay-article.md` and `assets/minimax_tts.py` only for a public article or tutorial that explicitly demonstrates the MiniMax relay.

Neither lane is a fallback for Fish S2.

## QC gate

Before narration delivery, require:

- voice ID and reference hashes match `references/fish-s2-default-voice.json`;
- the complete cloning reference is the configured mono 44.1 kHz 16-bit PCM WAV and matches its expected hash and duration;
- the final narration is lossless before video encoding;
- `used_fallback=false`;
- final integrated loudness is near -16 LUFS and true peak does not exceed -1.5 dBFS;
- ASR contains the complete spoken content;
- caption/alignment QC passes against the exact final WAV;
- the video contains one canonical narration track beginning at zero.
