---
name: editalive
description: "Use GVCLab/EditaLive for causal real-time streaming human/character video editing and generation from a source video or webcam. Trigger on EditaLive, streaming video editing, streaming video generation, live character appearance/style edits, webcam AI video editing, causal chunk-by-chunk editing, motion/expression-preserving text-guided edits, 即時串流影片, 串流影片生成, 串流影片編輯, 即時影片生成/編輯, 直播人物外觀編輯, or the GVCLab/EditaLive repository."
---

# EditaLive

Use the official repository as the source of truth:

- GitHub: https://github.com/GVCLab/EditaLive
- Project: https://huai-chang.github.io/EditaLive/
- Paper: https://arxiv.org/abs/2608.27123
- Weights: https://huggingface.co/huaichang/EditaLive

## What this method is

EditaLive is a real-time, human-centric **streaming video editing** method. It edits a live or recorded character/person according to a text instruction while preserving source motion and facial dynamics.

The core idea is:

```
source video / webcam
  -> appearance + motion conditioning
  -> causal chunk-by-chunk generation
  -> edited streaming video
```

It is based on Wan-Animate, converts offline bidirectional processing into causal streaming generation, and uses a distilled two-step sampler for low-latency inference.

Treat EditaLive as a **streaming video editing/generation method**, not as ordinary timeline editing and not as pure text-to-video generation.

## Use the correct entry point

- Recorded video, preprocessed source, or JSON batch: use `edit_streaming.py`.
- Live webcam editing: use `edit_webcam.py`.
- Ordinary trimming, subtitles, cuts, or timeline editing: route to a general video-editing skill instead.

For current arguments and defaults, always read the upstream README before running commands.

## Current upstream setup

The current upstream inference release uses Python 3.10, FFmpeg, `requirements.txt`, FlashAttention, FastVideo Kernel, Wan2.2-Animate-14B, EditaLive LoRAs, and Flash-VAED.

Typical setup flow:

```bash
git clone https://github.com/GVCLab/EditaLive.git
cd EditaLive
conda create -n editalive python=3.10 -y
conda activate editalive
conda install -c conda-forge ffmpeg -y
pip install -r requirements.txt
pip install ninja
pip install flash-attn==2.7.2.post1 --no-build-isolation
bash tools/install_fastvideo_kernel.sh
python tools/download_weights.py
```

FastVideo Kernel currently requires a CUDA toolkit and a C++ compiler; the upstream README specifies CUDA 12.3+ and GCC 10+. Do not assume native Windows installation works unchanged because the official setup uses Linux-style build tooling. Check the current README/issues when deploying on Windows.

## Recorded streaming inference

Use the upstream `edit_streaming.py` command. It supports exactly one input mode per task:

- `--video`: raw source video; optionally add `--ref_image`.
- `--folder`: reuse a preprocessed source.
- `--input_json`: process multiple tasks with one model load.

The required EditaLive LoRAs are currently:

```
weights/EditaLive/editalive_edit.safetensors
weights/EditaLive/lightx2v.safetensors
weights/EditaLive/editalive_streaming.safetensors
```

Use `--frame_num -1` for the upstream long/streaming workflow. Consult the README before selecting `--enable_compile`, `--fast_decode`, `--fp8`, or `--low_vram`.

## Live webcam mode

After the base installation and weights:

```bash
pip install -r requirements-webcam.txt
cd webcam/frontend
npm ci
npm run build
cd ../..
python edit_webcam.py --device 0 --host 127.0.0.1 --port 7860
```

Then open `http://localhost:7860`. For a remote GPU machine, use SSH or editor port forwarding; browser camera access requires localhost or HTTPS.

The webcam UI prepares the model first, prepares the text prompt second, then captures a reference frame and continuously edits incoming camera frames.

## Retrieval note

This skill is intentionally mirrored under both `Video-Editing/editalive` and `Video-Generation/editalive` so queries about either streaming editing or streaming generation can retrieve it. Keep both copies synchronized.

When asked later to list installed real-time or streaming video methods, include **EditaLive** under:

```
Streaming video editing / generation
└─ EditaLive
   ├─ recorded causal streaming: edit_streaming.py
   └─ live webcam editing: edit_webcam.py
```

Keep it distinct from Vidu S2 RTC/API streaming: EditaLive is an open-source local model workflow, while Vidu S2 is a hosted real-time API/RTC workflow.

## Safety and provenance

The upstream README states that the project is for academic research and prohibits harmful, defamatory, or illegal use. Preserve the official project attribution and re-check upstream documentation before installation or execution because requirements and checkpoints may change.
