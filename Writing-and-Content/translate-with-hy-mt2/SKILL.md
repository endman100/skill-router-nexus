---
name: translate-with-hy-mt2
description: Use Tencent Hy-MT2-1.8B-GGUF for lightweight local text-to-text translation with llama.cpp or Ollama. Use when the user explicitly requests Hy-MT2, wants private local translation on CPU or consumer hardware, or needs a compact GGUF translation model. Support plain text, documents, Markdown, structured text, terminology constraints, and style instructions. Do not use for speech, OCR, image translation, or model training.
---

# Translate with Hy-MT2

Use `tencent/Hy-MT2-1.8B-GGUF` as a compact local translation model. Keep this skill limited to model selection, prompting, inference, and translation output.

## Model record

- Model: `tencent/Hy-MT2-1.8B-GGUF`
- Model card: https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF
- Runtime: recent `llama.cpp` with the STQ kernel support required by the model, or an application that bundles a compatible runtime
- License: Apache-2.0
- Default quantization: `Q8_0` (about 1.91 GB)
- Reduced-memory fallbacks: `Q6_K` (about 1.47 GB), then `Q4_K_M` (about 1.13 GB)
- Registry snapshot: 2026-09-17

Do not copy model weights or upstream source code into this skill. Do not install a runtime or download model weights unless the user has asked to set up or run the model. Reuse an existing compatible installation and cache when possible.

## Workflow

1. Confirm both source and target are in the supported-language list below.
2. Check for an existing compatible llama.cpp or Ollama installation and a cached Hy-MT2 model.
3. Use `Q8_0` by default. Fall back to `Q6_K` only when Q8_0 cannot fit in available memory, then use `Q4_K_M` only when Q6_K also cannot fit.
4. Build one translation prompt using the templates below. Do not add a system prompt; the model card states that the 1.8B model has no default system prompt.
5. Run inference with the recommended sampling settings.
6. Return only the translation unless the user requests notes, diagnostics, or a bilingual layout.

For long documents, split at semantic or Markdown block boundaries, keep a shared glossary, translate chunks in order, and check terminology and joins before returning the result.

## Quick local run

Prefer a recent llama.cpp build:

```powershell
llama-cli -hf tencent/Hy-MT2-1.8B-GGUF:Q8_0 --jinja -st -n 4096 -p "Translate the following text into Traditional Chinese. Note that you should only output the translated result without any additional explanation:`nHello, world."
```

Ollama may also load the Hugging Face GGUF directly when its bundled runtime supports this model:

```powershell
ollama run hf.co/tencent/Hy-MT2-1.8B-GGUF:Q8_0
```

If llama.cpp reports an unknown tensor, architecture, or quantization type, update to a build that includes the model's required STQ support. Do not repeatedly retry an incompatible binary.

## Prompt templates

Use full language names in the same language as the instruction.

Default translation:

```text
Translate the following text into <target language>. Note that you should only output the translated result without any additional explanation:
<source text>
```

With terminology:

```text
Reference the following translations:
<source term> translates to <target term>

Translate the following text into <target language>. Note that you must ONLY output the translated result without any additional explanation:
<source text>
```

For Markdown, JSON, YAML, subtitles, or code-adjacent text, explicitly require preservation of structure, keys, placeholders, delimiters, indentation, links, and code. Translate only user-facing natural-language text.

## Inference settings

Use the official recommended settings for the 1.8B model:

```text
temperature: 0.7
top_p: 0.6
top_k: 20
repetition_penalty: 1.05
max_tokens: 4096
```

Increase the output limit only when needed to avoid truncation. Preserve the other values unless the user requests an experiment.

## Supported languages

Chinese, Traditional Chinese, English, French, Portuguese, Spanish, Japanese, Turkish, Russian, Arabic, Korean, Thai, Italian, German, Vietnamese, Malay, Indonesian, Filipino, Hindi, Polish, Czech, Dutch, Khmer, Burmese, Persian, Gujarati, Urdu, Telugu, Marathi, Hebrew, Bengali, Tamil, Ukrainian, Tibetan, Kazakh, Mongolian, Uyghur, and Cantonese.

Do not claim support for an unlisted language. Use another translation workflow when either language is unsupported.

## Boundaries

- Use this skill when Hy-MT2 or lightweight local GGUF translation is requested. Keep the existing MiLMMT routing for other supported translation requests.
- Extract text through an appropriate workflow before translating screenshots, scans, audio, or video.
- Preserve facts, numbers, names, markup, and placeholders. Do not summarize or silently omit source content.
- Stop a temporary local server after the task unless the user asks to keep it running.
