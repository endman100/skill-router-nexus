---
name: ra-逐字稿提取skill
description: 视频内容逐字稿提取专用 skill。Use when the user provides a 抖音 or 小红书 URL and asks for逐字稿、视频转文字、听写视频或提取口播内容。Resolve media with qushuiyin, delegate recognition to asr-router, and keep extraction-only privacy and output rules here.
---

# ra-逐字稿提取skill

## Goal

Extract a faithful Markdown transcript from a 抖音 or 小红书 video URL.

This skill is intentionally narrow and lightweight:

- resolve the video URL with qushuiyin
- delegate the resolved media URL to `asr-router` with
  `preferred_provider=paraformer` and `fallback_allowed=false`
- write a Markdown transcript to `01-内容生产/视频工作台/.internal/洗稿/`（源隐私区——提取件默认按他人内容对待，源标题不得落入公开目录）
- print the complete transcript in the conversation

For final-video subtitle synchronization, route to `ra-audio-to-subtitles`.
Paragraph-level transcript timestamps from this skill are not production
caption timing.

Do not summarize, rewrite, translate, adapt, title, distribute, or start video production.

## Locate The Skill

```bash
ZT_HOME="$(
  for d in "$(pwd)/.codex/skills/ra-逐字稿提取skill" \
           "$(pwd)/.agents/skills/ra-逐字稿提取skill" \
           "$(pwd)/.claude/skills/ra-逐字稿提取skill" \
           "$HOME/.codex/skills/ra-逐字稿提取skill" \
           "$HOME/.agents/skills/ra-逐字稿提取skill" \
           "$HOME/.claude/skills/ra-逐字稿提取skill"; do
    [ -f "$d/SKILL.md" ] && echo "$d" && break
  done
)"
export ZT_HOME
```

Use `"$ZT_HOME/scripts/transcript.py"` for every operation.

## Workflow

1. Optional health check:

   ```bash
   python3 "$ZT_HOME/scripts/transcript.py" --doctor
   ```

2. Resolve the media URL and save the resolver artifact:

   ```bash
   python3 "$ZT_HOME/scripts/transcript.py" "<抖音或小红书视频URL>" \
     --resolve-only --resolve-output <work>/resolved-media.json
   ```

3. Read `video_url` from that artifact. The Agent invokes `asr-router` with
   `source=<video_url>`, `preferred_provider=paraformer`,
   `fallback_allowed=false`, `profile=transcript`, and `privacy=allow_api`.

4. Consume the Router normalized result and generate Markdown:

   ```bash
   python3 "$ZT_HOME/scripts/transcript.py" "<抖音或小红书视频URL>" \
     --resolved-input <work>/resolved-media.json \
     --asr-result <work>/asr-result.json
   ```

5. If the URL is unsupported, or qushuiyin/ASR Router fails, stop and report the
   exact error. Do not execute a provider adapter or try another extraction
   pipeline inside this skill.

## Required Config

Only Qushuiyin configuration stays here. ASR credentials, provider options, and
invocation are canonical in `asr-router/references/paraformer-api.md`; this skill
only supplies Router constraints and consumes its normalized result:

```bash
QUSHUIYIN_API_BASE=https://api.guijianpan.com
QUSHUIYIN_API_KEY=...
```

## Hard Rules

- Preserve spoken content as ASR text. Do not rewrite it into a better script.
- Keep paragraph-level timestamps when Paraformer returns sentence timing.
- Save transcripts by default to `01-内容生产/视频工作台/.internal/洗稿/`（隐私区）. Only write into `逐字稿/` when the user explicitly says the video is their own work（此时用 `--output-dir` 指定）；`逐字稿/` 的写入白名单见其 README.
- Show the full transcript in the conversation after extraction.
- Do not call other creation, rewriting, title, image, distribution, or video-production skills during this task.

## Command Options

```bash
python3 "$ZT_HOME/scripts/transcript.py" "<url>" \
  --title "<optional title>" \
  --output-dir "<optional output dir>" \
  --resolved-input "<resolved-media.json>" \
  --asr-result "<asr-result.json>"
```

Use `--no-save` only when the user explicitly does not want a `.md` file.
