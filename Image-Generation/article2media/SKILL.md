---
name: article2media
description: "Turn articles or video transcripts into Chinese long images, Xiaohongshu carousel cards, WeChat layouts, narrated shorts, argument whiteboards, or comics using the upstream article2media tools. Use for article-to-image, 小红书图文, 公众号排版, 原文长图, and multi-format repurposing requests."
---

# article2media

[article2media](https://github.com/threerocks/article2media) provides ten composable capabilities plus an entry skill for fetching, transcribing, rewriting, translating, and presenting source content. It accepts X/Twitter posts and threads, web and WeChat articles, local Markdown/text, pasted prose, Douyin/YouTube/Bilibili links, local audio/video, and SRT/VTT subtitles. Outputs include long images, carousel cards, paste-ready WeChat HTML, narrated vertical videos, argument maps, and comics, with batch queues and local publication statistics.

Use it when a user supplies source content and wants visual adaptations, original-text layouts, or several publication formats. The agent writes summaries, translations, and storyboards; upstream scripts handle extraction, rendering, media processing, and checks.

This is a documentation-only wrapper. Clone upstream outside this skill repository and run its scripts there. All paths below are relative to that clone; none of its engine, scripts, themes, or assets are bundled here.

## Install and setup

Follow the [upstream installation instructions](https://github.com/threerocks/article2media#安装). With Node.js **22+** and Chrome/Chromium available:

```bash
git clone --depth 1 https://github.com/threerocks/article2media.git ~/code/article2media
cd ~/code/article2media
bash scripts/install.sh
node skills/article2media/engine/scripts/doctor.mjs
```

`install.sh` checks dependencies and prints suggested installation commands; it does not install them. The renderer has zero npm package dependencies. Fix failed required checks before continuing. Set `ARTICLE2MEDIA_CHROME=/path/to/chrome` when browser detection fails. Chrome must be allowed to launch and write its cache.

Optional font localization, explicitly downloading approximately 65 MB:

```bash
node skills/article2media/scripts/fonts.mjs
```

Without local fonts, themes load web fonts and can fall back to system fonts. Rendering does not itself install a font cache.

For native host registration, upstream also documents `npx skills add threerocks/article2media -g -a claude-code -a codex -y`, or the Claude Code plugin commands below. These install upstream skills separately from this wrapper. Their shared `skills/article2media/engine/` must stay alongside the capability directories; installing a single capability without its engine is insufficient.

```bash
claude plugin marketplace add threerocks/article2media
claude plugin install article2media@article2media
```

## Workflow

Read the clone's `skills/article2media/SKILL.md` and `skills/article2media/references/pipeline.md`, then the selected capability's `SKILL.md` and referenced guide. In upstream documents, `${CLAUDE_SKILL_DIR}` means the directory of that upstream skill, **not this wrapper's directory**. When native skills are unavailable, follow those files directly and execute their scripts from the clone.

Use one work directory per source, normally `./article2media-out/<slug>/`. Capabilities exchange `article.md` (source/transcript), `article.zh.md` (translation), `content.json` (structured rewrite), and `rewrite.md` (exported rewrite).

| Requested result | Upstream capability sequence |
|---|---|
| Long summary image, default | article-fetch → article-rewrite → long-image |
| Xiaohongshu summary cards | article-fetch → article-rewrite → image-cards, 3:4 |
| Original-text long image/cards | article-fetch → long-image/image-cards, using article.md |
| WeChat layout | article-fetch → wechat-layout, using article.md |
| WeChat summary | article-fetch → article-rewrite → export.mjs → wechat-layout, using rewrite.md |
| Full translation and layout | article-fetch → article-translate → desired original-text layout |
| Video to cards | video-transcript → article-rewrite → image-cards |
| Narration, argument map, comic | Fetch/transcribe → explainer-video, logic-whiteboard, or article-comic |

Long images and cards default to summaries; WeChat defaults to original-text layout. Explicit “原文 / 全文 / 一字不改” preserves the text. Translate first when an original-text layout needs another output language. Narration, whiteboard, and comic modes require their own agent-authored JSON rather than an automatic summary command. Reuse existing source/rewrite files when adding formats.

After native upstream installation, these are **host prompts**, not shell commands (Codex uses `$article2media`):

```text
/article2media ./my-essay.md 小红书
/article2media ./my-essay.md 公众号
/article2media ./my-essay.md -f
/article2media ./my-essay.md 长图、小红书、公众号都要
```

Direct script example: fetch a local article, then create verbatim cards and WeChat layout. Replace the source path; run from the clone:

```bash
node skills/article-fetch/scripts/fetch.mjs /absolute/path/my-essay.md --out ./article2media-out/essay
node skills/image-cards/scripts/cards.mjs ./article2media-out/essay/article.md --ratio 3:4
node skills/wechat-layout/scripts/wechat.mjs ./article2media-out/essay/article.md --theme quiet
```

For summaries, first author `content.json` according to `skills/article-rewrite/references/content-schema.md`, `writing-guide.md`, and `figures.md`; cards also need `skills/image-cards/references/xhs-guide.md`. There is no standalone command that writes the summary for the agent. Then:

```bash
node skills/article-rewrite/scripts/check.mjs ./article2media-out/essay/content.json --ratio 3:4
node skills/image-cards/scripts/cards.mjs ./article2media-out/essay/content.json --ratio 3:4
node skills/long-image/scripts/long.mjs ./article2media-out/essay/content.json --theme midnight
```

Resolve failed checks before delivery and inspect the images/overview or video contact sheet. Original-text modes compare rendered blocks against the source; automated checks do not establish factual accuracy. Deliver absolute artifact paths, the chosen sequence/theme, posting copy where produced, and remaining warnings. WeChat delivery uses `article.html` → “复制到公众号” → paste in the editor. Batch/checklist/statistics tools manage local files; publication is a separate action.

## Dependencies and credentials

- **Base rendering:** Node.js 22+, Chrome/Chromium, suitable Chinese fonts, and a Claude Code/Codex host for agent-authored content. Basic rendering needs no image API key or GPU; host access is separate.
- **Illustrations and comics:** upstream supports a logged-in Codex CLI (`codex login`), `OPENAI_API_KEY`, or a paid image-capable Gemini key (`GEMINI_API_KEY` or `GOOGLE_API_KEY`). These are optional for ordinary layouts; comics require image generation. Provider/model overrides are documented upstream via `ARTICLE2MEDIA_IMAGE_PROVIDER`, `ARTICLE2MEDIA_IMAGE_MODEL_CODEX`, `ARTICLE2MEDIA_IMAGE_MODEL_OPENAI`, and `ARTICLE2MEDIA_IMAGE_MODEL_GEMINI`.
- **Narrated video:** ffmpeg; optional Apple Silicon + mlx-audio + VoxCPM2 for local narration, with edge-tts (networked) or macOS system speech fallbacks. Optional mlx-whisper provides word alignment; fallback timing uses edge-tts boundaries or estimates.
- **Video input:** yt-dlp for YouTube/Bilibili subtitles/audio and Douyin fallback; ffmpeg for audio extraction. Without subtitles, upstream's local ASR path uses Apple Silicon, mlx-whisper, and whisper-large-v3-turbo. SRT/VTT can be parsed directly. Follow upstream's diagnostics for the selected path rather than installing all optional components.

## Known limits and verification status

- Extraction depends on source availability: X uses FxTwitter; ordinary pages try r.jina.ai, defuddle.md, then local Chrome (`--no-proxy` avoids the web proxies). Internal `x.com/i/article/...` links require the publishing post URL. Paywalls, incomplete bodies, and platform login/anti-bot checks can prevent extraction; request the full text or a local file rather than inventing missing content. Browser-cookie reuse requires user consent under upstream's workflow.
- The documented local VoxCPM2/MLX path targets Apple Silicon. Other-platform acceleration, output quality, latency, and resource requirements are unverified here. Missing ASR limits video input to available subtitles; missing image generation prevents comics.
- Chinese output is the main workflow; summary mode supports `--lang en`. Transcripts may misrecognize names and terms. Layout/translation checks cannot guarantee faithful writing or factual correctness; report uncertain content and inspect the result.
- Reviewed on **2026-11-13** against upstream commit [`772d3402655d5223002d48713d9b8af3bc7fda99`](https://github.com/threerocks/article2media/tree/772d3402655d5223002d48713d9b8af3bc7fda99): README, all eleven SKILL.md files, LICENSE, pipeline, dependency checker, image-provider variables, and script entry points. Commands and requirements were checked against documentation/source. Installation, rendering, transcription, narration, and paid services were **not tested end to end**; upstream quality/speed claims are not local measurements.

## License

Upstream code is [MIT](https://github.com/threerocks/article2media/blob/772d3402655d5223002d48713d9b8af3bc7fda99/LICENSE), copyright © 2026 LeiLiu; retain its copyright and permission notice when redistributing copies or substantial portions. Upstream states its six bundled voices were generated from text descriptions and may be used/distributed with the project; imported personal voices remain the user's responsibility. Example articles/media retain their authors' rights. Third-party model, font, and service terms are separate and were not independently audited here.

Classification decision: `KEEP_FLAT` in `Image-Generation`; article-driven long images and templated cards fit the existing category. No index or taxonomy entry is required.
