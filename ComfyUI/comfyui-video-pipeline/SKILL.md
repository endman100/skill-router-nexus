---
name: comfyui-video-pipeline
description: Design and validate current ComfyUI text-to-video, image-to-video, video-to-video, motion-control, talking-character, interpolation, and production workflows against installed models and nodes.
---

# Build a ComfyUI video pipeline

Use the target server inventory and the current official tutorial for the chosen model. Video model names, loader layouts and memory requirements change quickly.

## Choose the pipeline

Confirm:

- text-to-video, image-to-video, reference/control, edit or talking-character
- target duration, frame rate, resolution and aspect ratio
- camera motion and subject motion
- first/last-frame or audio conditioning
- identity and temporal-consistency requirements
- available accelerator memory and acceptable runtime
- final delivery codec and platform

## Model verification

Before writing a workflow:

1. Check the latest ComfyUI release and video tutorials.
2. Confirm the exact model variant, files, encoders, VAE and loader nodes.
3. Confirm every class_type through /object_info.
4. Confirm license and hardware guidance from the model publisher.
5. Start from the matching official workflow when available.

Official Wan 2.2 workflows distinguish TI2V-5B, I2V-A14B and T2V-A14B, and A14B workflows can require separate high-noise and low-noise experts.

https://docs.comfy.org/tutorials/video/wan/wan2_2

Recheck newer families through:

https://docs.comfy.org/tutorials/video

Treat AnimateDiff and other older systems as compatibility options, not default recommendations.

## Build and test

1. Validate a short, low-resolution clip first.
2. Lock seed and input assets while tuning motion.
3. Increase one of duration, resolution or batch pressure at a time.
4. Inspect first frame, last frame, temporal consistency, anatomy, camera motion and loop boundaries.
5. Use supported interpolation or upscaling only after base motion is acceptable.
6. Keep audio/lip-sync as a separate validated stage unless the model natively conditions on audio.

## Production manifest

Record source image/video/audio, prompts, negative conditioning if supported, model files, workflow JSON, seed, dimensions, frame count, frame rate, ComfyUI version and custom-node revisions. This replaces the former generic project-manager Skill.

For final assembly, hand clips and audio to a dedicated video-editing workflow. Record exact frame rate and color/audio assumptions; do not embed obsolete Remotion or publishing instructions in the ComfyUI graph.

## Completion check

The workflow must validate against /object_info, queue without node_errors, render a short test, preserve requested constraints and export media with verified duration, frame rate and codec metadata.
