# Default narration production

Use this profile when the user asks to generate or replace narration and does not explicitly select another voice.

## Voice identity

- Provider: local ComfyUI Fish Audio S2 Pro.
- Node: `FishS2VoiceCloneTTS`.
- Model: `s2-pro-fp8`.
- Voice ID: `taiwan-highschool-female-07-fast`.
- ComfyUI host: `127.0.0.1`, port `1120`.
- Canonical profile from this skill root: `../../TTS-and-Voice-AI/tts-skill/references/fish-s2-default-voice.json`.
- Canonical audio is the complete 60-second lossless WAV declared by that profile under `tts-skill/assets/reference-audio/`.
- Import or copy that bundled WAV into the local ComfyUI input directory using the profile's `reference_audio_input` basename. Never commit a machine-specific absolute path.
- Use the profile's complete `reference_text` exactly; do not shorten the WAV or transcript.

Do not silently substitute another voice. If the reference or node is unavailable, report the dependency instead of falling back.

## Generation defaults

Generate one narration scene at a time so failed segments can be retried without changing successful audio.

```json
{
  "language": "zh",
  "device": "cuda",
  "precision": "float16",
  "attention": "sdpa",
  "max_new_tokens": 1024,
  "chunk_length": 400,
  "temperature": 0.85,
  "top_p": 0.86,
  "repetition_penalty": 1.1,
  "seed_base": 7007,
  "sentence_pause_tag": "[short pause]"
}
```

Increment the seed by scene index. Preserve the exact display script separately from any Fish control tags.

## Mastering and synchronization

1. Convert segments to mono PCM WAV at 44.1 kHz.
2. Add 0.65 seconds of leading silence, 0.55 seconds between scenes, and 0.8 seconds at the end unless the content requires another cadence.
3. Loudness-normalize the combined narration to -16 LUFS, LRA 7, and a -1.5 dB true-peak ceiling.
4. Save one canonical final narration WAV and record its SHA-256.
5. Run Qwen forced alignment against the exact display script after mastering.
6. Derive captions, scene boundaries, and named animation cues only from the final WAV timestamps.
7. Render one top-level narration track beginning at frame zero; never assemble independent scene audio inside Remotion.
8. Save a manifest with reference hashes, settings, segment seeds, prompt IDs, durations, output hash, and whether fallback occurred.
