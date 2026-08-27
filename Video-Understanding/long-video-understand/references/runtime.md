# Runtime and model boundary

## Tested configuration

- Model: `MCG-NJU/VideoChat3-4B`
- Revision: `37fa901ec5913f84bc31108ebc1e60ad1903634c`
- Python: 3.12.8
- PyTorch: 2.11.0+cu130
- Transformers: 4.57.6
- Accelerate: 1.12.0
- qwen-vl-utils: 0.0.14
- decord: 0.6.0
- GPU used for validation: NVIDIA GeForce RTX 5090, 32 GB

The wrapper downloads model weights, processor files, and pinned Hugging Face remote code into the normal Hugging Face cache. None of those files belong in the skill directory.

## Dependency recovery

Preserve an already-working CUDA PyTorch installation. Install the remaining tested packages with:

```powershell
python -m pip install -r scripts/requirements.txt
```

If `doctor.py` reports no CUDA, install a CUDA-enabled PyTorch build appropriate for the installed NVIDIA driver; do not silently fall back to CPU for a 4B video model.

## Attention backends

- `auto`: use FlashAttention 2 when importable; otherwise use SDPA.
- `sdpa`: portable PyTorch fallback tested on Windows. Bound memory by reducing frames and pixels.
- `flash_attention_2`: preferred for larger frame counts on supported Linux/CUDA environments.
- `eager`: diagnostic fallback only; it is slower and more memory intensive.

The upstream model config defaults the vision tower to FlashAttention 2 even when that package is unavailable. The wrapper overrides only the in-memory config to SDPA; it does not patch downloaded upstream code.

## Expected first-run behavior

The first invocation downloads roughly 8.3 GiB of safetensor weights plus processor and pinned remote-code files. Loading is much slower than subsequent segment inference. Keep all segments in one process so the model loads once.

The validated four-frame, 100352-pixel test used about 9.2 GiB peak allocated CUDA memory and correctly recovered a synthetic red-to-blue-to-green scene sequence with a left-to-right moving square.

## Limitations

- Frame sampling can miss brief events between selected frames.
- VideoChat3-4B currently analyzes visual content only; it does not transcribe the audio track.
- SDPA memory grows quickly with visual token count. Prefer more temporal chunks over a very large `--nframes` value.
- The model uses `trust_remote_code=True`; keep the tested revision pinned and review new upstream revisions before changing it.
