---
name: openai-whisper
description: Compatibility entry for local Whisper speech-to-text. Delegate every ASR invocation to asr-router; keep this skill only for existing callers.
metadata:
  {
    "openclaw":
      {
        "emoji": "🎤",
        "requires": { "bins": ["whisper"] },
        "install":
          [
            {
              "id": "brew",
              "kind": "brew",
              "formula": "openai-whisper",
              "bins": ["whisper"],
              "label": "Install OpenAI Whisper (brew)",
            },
          ],
      },
  }
---

# Whisper compatibility entry

Invoke `asr-router` with `preferred_provider=whisper`. Read its
`references/whisper-local.md` and use the router's schema and fallback rules.

This file intentionally contains no Whisper invocation details. The canonical
method lives in `Speech-Recognition/asr-router`.
