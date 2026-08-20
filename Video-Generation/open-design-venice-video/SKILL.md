---
name: venice-video
description: |
  Video generation workflows via the Venice.ai API. Delegate speech recognition and transcription to asr-router.
triggers:
  - "venice video"
  - "venice video gen"
od:
  mode: video
  category: video-generation
  upstream: "https://github.com/veniceai/skills"
---

# venice-video

> Curated from the Venice.ai team.

## What it does

Video generation workflows via the Venice.ai API.

For speech recognition or transcription, invoke `asr-router`. Venice is not a
registered ASR provider because this repository has no executable Venice
transcription method; let the Router choose from its installed methods.

## Source

- Upstream: https://github.com/veniceai/skills
- Category: `video-generation`

## How to use

This catalogue entry advertises the skill in Open Design so the agent
discovers it during planning. To run the full upstream workflow with
its original assets, scripts, and references, install the upstream
bundle into your active agent's skills directory:

```bash
# Inspect the upstream README for exact paths
open https://github.com/veniceai/skills
```

Then ask the agent to invoke this skill by name (`venice-video`) or with
one of the trigger phrases listed in this skill's frontmatter.
