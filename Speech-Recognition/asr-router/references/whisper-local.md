# Whisper CLI

**Type:** local model. **API upload:** no. **Requirements:** the `whisper` CLI
and FFmpeg. Install with `pip install -U openai-whisper` and the platform's
FFmpeg package when the runtime is missing.

```bash
whisper /path/audio.mp3 --model medium --output_format txt --output_dir .
whisper /path/audio.m4a --task translate --output_format srt
whisper /path/audio.wav --language English --output_format json
```

The installed CLI defaults to `turbo`. Use smaller models for speed and larger
models for accuracy. Models download to the Whisper cache on first use.

Map plain text to `text`; map timestamped output only when the selected format
actually contains timestamps. Do not claim word-level timing from ordinary TXT
or SRT output. Preserve the CLI output as `raw_artifact`.

Whisper does not provide speaker diarization. Treat repetitions or invented
phrases as possible hallucinations, especially with silence, noise, or long
recordings. Split long inputs when reliability degrades and retain the source
audio for review. For realtime recognition, use an eligible realtime provider
from the Router instead of treating batch-oriented Whisper CLI as streaming.

Operational guidance consolidated from the former
`AI-Research/whisper/SKILL.md`; the compatibility entry remains at
`Speech-Recognition/openai-whisper/SKILL.md`.
