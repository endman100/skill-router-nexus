---
name: minimax-h3-prompt-rewriter-ref2va
description: >-
  Use when running or documenting lightx2v's MiniMax-H3 Prompt Rewriter
  (Qwen3.8-27B SFT) for Ref2VA: vLLM server + post_vllm client that expands a
  short brief plus image/video/audio refs into the six-section MiniMax H3
  full-reference prompt. Trigger on MiniMax-H3 Prompt Rewriter, Ref2VA rewriter,
  lightx2v rewriter, Qwen3.8-27B-Ref2VA, vllm_server.sh / post_vllm, H3 prompt
  rewrite model. Prefer sibling h3-prompt-writing for hand-authored prompts;
  prefer minimax-h3-nsfw-prompt for the fixed pic1ref ComfyUI action-clip graph.
---

# MiniMax-H3 Prompt Rewriter (Ref2VA)

Official open rewriter that turns a short creative brief plus reference media
into MiniMax H3 **full-reference (Ref2VA)** prompts. Model card:

https://huggingface.co/lightx2v/MiniMax-H3-Prompt-Rewriter-Qwen3.8-27B-Ref2VA

Base: supervised fine-tune of [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)
(~27B, BF16). Repo ships weights, `vllm_server.sh`, `post_vllm.sh` /
`post_vllm.py`, and `VIDEO_PROMPT_WRITING_GUIDE_ref_en.md` (vendored beside this
`SKILL.md`).

## When to use this vs siblings

| Need | Skill |
| --- | --- |
| Run / set up the **rewriter model** (vLLM + multimodal post) | **this skill** |
| Hand-write T2VA / I2VA / FL2VA / L2VA / Ref2VA fields | `h3-prompt-writing` |
| Fixed pic1ref 5 s anime action-clip ComfyUI graph | `minimax-h3-nsfw-prompt` |

Do not invent unprovided reference labels. The rewriter only sees paths you pass
in `IMAGES` / `VIDEOS` / `AUDIOS`.

## Setup

Server Python env with GPU + vLLM:

```bash
pip install vllm requests pillow qwen-vl-utils
```

For video references, install `ffmpeg` and `ffprobe` on `PATH`. Run scripts from
the model directory (or use absolute script paths).

## Run

### 1. Start vLLM

Edit `vllm_server.sh`: set `MODEL_PATH` to the downloaded Ref2VA weights, pick
GPU / host / port. Defaults: GPU 0, `127.0.0.1:8000`, `MAX_IMAGES=50`,
`--max-model-len 32768`, output cap 16384, reasoning parser `qwen3`,
`enable_thinking` + `reasoning_effort=xhigh`, sampling
`temperature=0.7 top_p=0.8 top_k=20`.

```bash
bash vllm_server.sh
```

To run this rewriter alongside another model, give each its own GPU and port and
point the client `SERVER_URL` at the matching server.

### 2. Post a rewrite request

Edit `post_vllm.sh`:

- `PROMPT` — short brief; refer to media as `image 1`, `video 1`, `audio 1` …
- `DURATION` — target seconds (H3 production windows are typically 1–15 s)
- Absolute paths in `IMAGES`, `VIDEOS`, and/or `AUDIOS` (unused arrays empty)
- Keep `MODEL` / `SERVER_URL` aligned with the server's `MODEL_NAME` / host / port
- `GUIDE` defaults to `VIDEO_PROMPT_WRITING_GUIDE_ref_en.md` in the same folder

```bash
bash post_vllm.sh
```

Dry run (build request only, no server call): add `--dry_run` to the
`post_vllm.py` invocation inside `post_vllm.sh`.

Useful client knobs (also in `post_vllm.sh`):

| Knob | Default | Notes |
| --- | --- | --- |
| `VIDEO_FRAMES` | 8 | Frames sampled per video reference |
| `IMAGE_MAX_SIDE` | 2048 | Long-edge resize for stills |
| `VIDEO_MAX_SIDE` | 1024 | Long-edge resize for sampled frames |
| `MAX_IMAGES` | 50 | Stills + sampled frames must fit client **and** server limits |
| `MAX_NEW_TOKENS` | 16384 | Must stay within 32768 context with text + image tokens |
| `REASONING_EFFORT` | `xhigh` | `low` / `medium` / `xhigh` |
| `TIMEOUT_SECONDS` | 1800 | Long rewrites need headroom |

`python post_vllm.py --help` lists every flag.

## Reference numbering and audio behavior

- Each modality is numbered from **1 in array order**, matching `image N` /
  `video N` / `audio N` in `PROMPT`.
- Videos become `VIDEO_FRAMES` images each; total images + frames ≤ `MAX_IMAGES`.
- Audio paths are existence-checked and passed as **labels only** — contents are
  not read or uploaded. To reference a video's soundtrack, put that video path in
  `AUDIOS` as well (or a standalone audio file).

## Outputs

Each run overwrites `infer_outputs/`:

| File | Contents |
| --- | --- |
| `result.request.json` | Request payload |
| `result.prompt.txt` | Text preview of the request |
| `result.json` | Response, reasoning, parameters, usage, timing |

Dry runs write only the request + preview.

## Rewrite output format (full-reference / Ref2VA)

The model is trained to emit **six English sections** in this fixed order
(dialogue / lyrics keep original language inside `<d>…</d>`; visible scene text
keeps its language):

1. `subject_definitions:` — `<Subject N>`, optional standalone `<Picture N>` /
   `<Video N>` / `<Audio N>` with roles
2. `summary:` — starts with `[task types…]` such as
   `[reference generation + audio reference]`
3. `retention_analysis:` — per label
   `fully_preserved` / `partially_preserved` / `attribute_transfer` /
   `weak_reference` (audio: `fully_copy` / `partially_copy` / `reference` /
   `weak_reference`)
4. `detailed_description:` — style line, then `[Shot 1]` (no timestamp), later
   `[Shot N] At MM:SS.mmm, …`; speakers `(Sx)`; dialogue in `<d>[Lang] …</d>`
5. `overall_soundscape:` — ambience / physical sound (or `N/A`)
6. `non_diegetic_music:` — audience-only score (or `N/A`)

Task-type tokens used in `summary` (combine with ` + `, no duplicates):
`keyframe completion`, `reference generation`, `video editing`,
`video continuation`, `audio reuse`, `audio reference`.

Generation-task `detailed_description` is normally ~350–500 English words;
editing tasks scale with source complexity. Full rules and the complete worked
example live in `VIDEO_PROMPT_WRITING_GUIDE_ref_en.md` next to this skill (same
file as upstream). For shared T2VA/I2VA/FL2VA/L2VA shot / camera / speaker
conventions when writing by hand, also read `h3-prompt-writing`.

## Ops notes

- Context is **32768** tokens for text + image/frame tokens + output; reference
  *count* alone does not guarantee a fit — lower `VIDEO_FRAMES` / resize sides /
  fewer refs if the server rejects.
- Default example servers both want GPU 0 + port 8000; isolate GPUs/ports when
  co-hosting.
- Treat rewriter output as a draft: still audit duration, label inventory, and
  clothing / identity locks against the user's brief before queuing H3.

## Sources

- Model: https://huggingface.co/lightx2v/MiniMax-H3-Prompt-Rewriter-Qwen3.8-27B-Ref2VA
- Base: https://huggingface.co/Qwen/Qwen3.8-27B
- Guide (vendored): `VIDEO_PROMPT_WRITING_GUIDE_ref_en.md`
