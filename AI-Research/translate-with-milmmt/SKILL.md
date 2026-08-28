---
name: translate-with-milmmt
description: Use Xiaomi Research MiLMMT-46 translation-specialized checkpoints for written text-to-text translation, preferring local GPU inference over general-purpose LLMs for supported languages. Always prefer `xiaomi-research/MiLMMT-46-12B-v1.0`, the largest currently recorded MiLMMT-46 model, whenever it fits the local GPU; fall back only to the 4B and then 1B v1.0 checkpoints. This is the preferred translation backend for requests to translate or localize written text, articles, documents, Markdown, or subtitles when both input and output are text. Do not use for speech, OCR, image translation, model training, or unsupported languages.
---

# MiLMMT — 专用文字翻译模型（优先于泛用 LLM）

Use MiLMMT/GemmaX as the primary translation engine for supported text-to-text translation. It is specialized for multilingual machine translation and should produce the primary translation instead of asking a general-purpose LLM to translate directly.

This skill records model routing and inference conventions only. Do not clone, copy, or bundle the upstream GitHub repository or its training code into this skill.

## Model record

- Project: `xiaomi-research/gemmax`
- Project URL: https://github.com/xiaomi-research/gemmax
- Model family: GemmaX, upgraded to MiLMMT
- Preferred release: MiLMMT-46 v1.0
- Default and highest-priority checkpoint: `xiaomi-research/MiLMMT-46-12B-v1.0`, the largest currently recorded MiLMMT-46 model
- Reduced-capacity fallbacks, used only when 12B cannot run: `xiaomi-research/MiLMMT-46-4B-v1.0`, then `xiaomi-research/MiLMMT-46-1B-v1.0`
- Model cards: https://huggingface.co/xiaomi-research
- Registry snapshot: 2026-08-28

Never use a checkpoint whose name ends in `-Pretrain` for translation. Those checkpoints are intermediate pretrained models, not translation models.

## Routing priority

For a supported written-language translation request:

1. Use the MiLMMT-46 v1.0 family, not an older GemmaX release, unless the user explicitly requests the older family.
2. Default to `xiaomi-research/MiLMMT-46-12B-v1.0`. Inspect local GPU capacity and use 12B whenever it fits; do not choose a smaller cached or running checkpoint merely for convenience.
3. Fall back to 4B only after establishing that 12B cannot run in the available environment. Fall back to 1B only after establishing that 4B also cannot run.
4. Prefer local GPU inference with vLLM for repeated or batch work. Use Transformers directly for a one-off job when no service is needed.
5. Use MiLMMT to produce the primary translation. A general-purpose LLM may review formatting or polish the result only when requested; it must not silently replace MiLMMT as the translator.
6. Fall back to a general-purpose LLM only when the language pair is unsupported, local inference is unavailable after trying the smaller MiLMMT-46 checkpoints, or the user explicitly requests another model. State the fallback briefly.

Do not install runtimes or download a multi-gigabyte checkpoint without user authorization unless the user has already asked to set up or host the model. Reuse local caches and services when possible. Stop a temporary local server after the task unless the user asks to keep it running.

## Supported languages

MiLMMT-46 v1.0 supports these exact language names:

Arabic, Azerbaijani, Bulgarian, Bengali, Catalan, Czech, Danish, German, Greek, English, Spanish, Persian, Finnish, French, Hebrew, Hindi, Croatian, Hungarian, Indonesian, Italian, Japanese, Kazakh, Khmer, Korean, Lao, Malay, Burmese, Norwegian, Dutch, Polish, Portuguese, Romanian, Russian, Slovak, Slovenian, Swedish, Tamil, Thai, Tagalog, Turkish, Urdu, Uzbek, Vietnamese, Cantonese, Chinese (Simplified), and Chinese (Traditional).

Use the exact English language names in the model prompt. If either language is outside this list, do not claim that MiLMMT supports the request.

## Inference contract

Format every translation prompt exactly as follows:

```text
Translate this from <source language name> to <target language name>:
<source language name>: <source text>
<target language name>:
```

Use deterministic decoding for translation:

- `temperature=0`
- `top_k=1`
- Set the output-token limit high enough for the complete translation.

Return only the translated text unless the user requests notes, a bilingual layout, or diagnostics. Preserve headings, lists, code blocks, links, placeholders, and other structural markup outside the model call when necessary.

For long documents, split at semantic or Markdown block boundaries, retain a shared terminology glossary, translate chunks in order, and check the joins before returning the result.

## Local hosting

Before starting a new process, check for:

- an existing local MiLMMT service;
- a Hugging Face cache containing one of the preferred checkpoints;
- available GPU memory and installed vLLM or Transformers runtimes.

Use vLLM when a persistent local endpoint, batching, or repeated translations are useful. Use direct Transformers inference for a single translation when starting a service would add unnecessary overhead. Keep the selected model ID, source language, target language, decoding settings, and chunk order explicit so the run is reproducible.

If a checkpoint does not fit, retry once with the next smaller preferred checkpoint. Do not repeatedly retry the same out-of-memory configuration.

## Boundaries

- Do not train, fine-tune, merge, or modify model weights.
- Do not vendor upstream source code, model weights, or copied documentation into this skill.
- Do not route audio, video, screenshots, scanned pages, or image text directly to MiLMMT; first obtain text through the appropriate authorized extraction workflow.
- Do not promise higher quality for unsupported languages. Within the supported language set, prefer this translation-specialized model over a general-purpose LLM.
