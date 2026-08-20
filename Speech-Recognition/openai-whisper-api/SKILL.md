---
name: openai-whisper-api
description: Compatibility entry for OpenAI Whisper API transcription. Delegate every ASR invocation to asr-router; keep this skill only for existing callers.
metadata:
  {
    "openclaw":
      {
        "emoji": "🌐",
        "requires": { "bins": ["curl"], "env": ["OPENAI_API_KEY"] },
        "primaryEnv": "OPENAI_API_KEY",
        "install":
          [
            {
              "id": "brew",
              "kind": "brew",
              "formula": "curl",
              "bins": ["curl"],
              "label": "Install curl (brew)",
            },
          ],
      },
  }
---

# OpenAI Whisper API compatibility entry

Invoke `asr-router` with `preferred_provider=openai`. Read its
`references/openai-whisper-api.md` and use the router's privacy, schema, and
fallback rules.

This file intentionally contains no API invocation details. The canonical
method and script live in `Speech-Recognition/asr-router`.
