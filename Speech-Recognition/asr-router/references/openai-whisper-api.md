# OpenAI Whisper API

**Type:** **API**. **Required secret:** `OPENAI_API_KEY`. `OPENAI_BASE_URL` may
point to an OpenAI-compatible proxy or local gateway.

```bash
<asr-router>/scripts/openai_whisper_api.sh /path/to/audio.m4a
<asr-router>/scripts/openai_whisper_api.sh /path/to/audio.ogg --model whisper-1 --out /tmp/transcript.txt
<asr-router>/scripts/openai_whisper_api.sh /path/to/audio.m4a --language en --prompt "Speaker names: Peter, Daniel"
<asr-router>/scripts/openai_whisper_api.sh /path/to/audio.m4a --json --out /tmp/transcript.json
```

Defaults: `whisper-1`, `<input>.txt`, and `/v1/audio/transcriptions`. Preserve
the response file and map only fields present in the chosen response format.

Source migrated from
`Speech-Recognition/openai-whisper-api/scripts/transcribe.sh`.
