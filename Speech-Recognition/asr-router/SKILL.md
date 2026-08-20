---
name: asr-router
description: Route audio or video through the installed ASR methods in this repository. Use for speech-to-text, transcript extraction, word timestamps, or realtime recognition when the caller needs one canonical provider order, explicit local-versus-API handling, and a normalized result contract. Exclude subtitle downloads and existing-caption extraction.
---

# ASR Router

Treat this skill as the single interface for speech recognition. Keep downloading,
editing, caption rendering, and business-specific QC in the calling skill.

## Workflow

1. Read [references/schema.md](references/schema.md). Record the requested
   profile, privacy policy, GPU availability, language, timing granularity, and
   whether fallback is allowed.
2. Select the first available method in the schema that satisfies every required
   capability. A method that lacks required word timestamps, realtime support,
   privacy permission, credentials, or installed runtime is unavailable.
3. Before uploading media to an API, require `privacy=allow_api`. Stop after the
   local methods when `privacy=local_only`.
4. Read only the selected method file and follow its invocation exactly:
   - [Qwen3-ASR](references/qwen3-asr.md) — local GPU
   - [Whisper CLI](references/whisper-local.md) — local
   - [Seed ASR](references/seed-asr-api.md) — API
   - [Deepgram](references/deepgram-api.md) — API
   - [Paraformer](references/paraformer-api.md) — API
   - [OpenAI Whisper API](references/openai-whisper-api.md) — API
   - [Gladia](references/gladia-api.md) — API
   - [Rev AI](references/rev-ai-api.md) — API
   - [Wit.ai](references/wit-ai-api.md) — API
5. Normalize the result to the schema. Preserve the raw provider artifact and
   record the exact provider, model, command, source hash, and fallback trace.
6. On failure, record the error and try the next eligible method only when
   fallback is allowed. Never silently cross from local processing to an API.

## Invariants

- Use ASR output as recognized text unless a calling workflow supplies approved
  display text. In that case, use ASR only as the timing substrate.
- Keep one recognition result per source hash, provider, model, and parameter
  set. Do not mix timestamps or text from different runs.
- Preserve caller constraints such as `preferred_provider=qwen3`,
  `fallback_allowed=false`, or
  production word-timestamp QC even when another method ranks higher globally.
- A calling skill may lock a provider only through Router input constraints. It
  must not locate or execute a provider adapter itself.
- Report actual availability. A catalogue entry or uninstalled upstream bundle
  is not an executable fallback.
