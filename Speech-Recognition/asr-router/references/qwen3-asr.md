# Qwen3-ASR

**Type:** local model. **API upload:** no. **Requirement:** CUDA, FFmpeg,
PyTorch, Transformers, and access to the Hugging Face model files.

Use `Qwen/Qwen3-ASR-1.7B-hf` with
`Qwen/Qwen3-ForcedAligner-0.6B-hf`. The migrated script keeps the original
240-second chunking, 15-second overlap, multilingual recognition, overlap
deduplication, and forced word alignment.

```powershell
python <asr-router>/scripts/qwen3_asr.py `
  --audio <audio> `
  --output-dir <output-directory> `
  --precision bf16
```

Use `--precision fp16` when BF16 is unsupported. Important options are
`--chunk-seconds`, `--overlap-seconds`, `--max-new-tokens`,
`--phrase-gap-seconds`, and `--phrase-duration-seconds`.

Canonical outputs include `qwen3_full_asr_words.json`,
`qwen3_full_asr_phrases.json`, CSV equivalents, per-chunk raw alignment data,
`qwen3_asr_run_summary.json`, and normalized `asr-result.json`. The normalized
result maps phrase rows to `segments`, word rows to `words`, and records both
exact model IDs.

Failure conditions: missing CUDA, missing `ffmpeg`/`ffprobe`, missing Python
packages, invalid audio, or empty aligned output. A caller may lock this method
with `preferred_provider=qwen3` and `fallback_allowed=false`.

Source migrated from `Video-Editing/skill-song-stream-clipper/scripts/run_qwen3_asr.py`.
