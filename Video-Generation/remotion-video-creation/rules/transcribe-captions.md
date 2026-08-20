---
name: transcribe-captions
description: Importing ASR Router word timestamps to generate captions in Remotion
metadata:
  tags: captions, transcribe, whisper, audio, speech-to-text
---

# Supplying recognized words

Do not select or invoke an ASR model from this rule. Request
`profile=word_timestamps` from `Speech-Recognition/asr-router`, then convert its
normalized `words` array to Remotion captions.

Keep caption grouping, rendering, and visual timing inside the Remotion
workflow. Provider order, local/API choice, credentials, endpoint details, and
recognition fallback live only in ASR Router.
