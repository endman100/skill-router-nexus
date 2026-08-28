---
name: comfyui-lora-training
description: Plan and validate LoRA training datasets and configurations for models used with ComfyUI. Use for subject, character, style, product, image, or video LoRAs after verifying the base model and trainer.
---

# Plan LoRA training for ComfyUI use

ComfyUI commonly consumes LoRAs but is not the source of truth for trainer syntax. Select and configure a trainer from its current official documentation.

## Establish the target

Confirm:

- exact base model and architecture
- LoRA purpose: identity, style, product, motion or adaptation
- expected inference loader and compatible format
- available GPU memory, system memory, storage and time
- licensing and commercial-use constraints
- whether the chosen trainer explicitly supports this base model version

Do not reuse SDXL, FLUX, Qwen, Wan or LTX settings across architectures.

## Dataset

1. Remove duplicates, corrupt files, watermarks and accidental private data.
2. Preserve useful variation while keeping the target concept consistent.
3. Use captions appropriate to the trainer and base model.
4. Reserve validation prompts/images that are not exact training duplicates.
5. Record source, license and consent for every dataset subset.
6. Keep a dataset manifest and deterministic split.

For identity or voice-adjacent training, obtain permission and avoid impersonation or deceptive deployment.

## Configuration

Derive resolution, buckets, rank, alpha, learning rates, optimizer, precision, gradient accumulation, text-encoder training and checkpoint cadence from the selected trainer's current architecture guide.

Treat online recipe values as experiment seeds, not universal defaults. Change one major variable at a time and log the full command/config plus software revisions.

## Evaluation

Evaluate multiple checkpoints in the same ComfyUI workflow using fixed seeds and controlled prompts. Check:

- likeness or concept strength
- prompt adherence and editability
- overfitting and background leakage
- style/identity entanglement
- artifacts across poses, lighting and aspect ratios
- inference compatibility with the intended loader

Select the smallest checkpoint that meets the goal. Keep the base-model license and dataset restrictions with the artifact.

## Sources

Use primary documentation for the selected base model and trainer. Confirm the final LoRA loads in the target ComfyUI version through /object_info and a minimal workflow. Do not invent download links, trainer flags or model filenames.
