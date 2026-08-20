# Whisper CLI

**Type:** local model. **API upload:** no. **Requirement:** the `whisper` CLI.

```bash
whisper /path/audio.mp3 --model medium --output_format txt --output_dir .
whisper /path/audio.m4a --task translate --output_format srt
```

The installed CLI defaults to `turbo`. Use smaller models for speed and larger
models for accuracy. Models download to the Whisper cache on first use.

Map plain text to `text`; map timestamped output only when the selected format
actually contains timestamps. Do not claim word-level timing from ordinary TXT
or SRT output. Preserve the CLI output as `raw_artifact`.

Source migrated from `Speech-Recognition/openai-whisper/SKILL.md`.
