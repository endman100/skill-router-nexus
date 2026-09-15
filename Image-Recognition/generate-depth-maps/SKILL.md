---
name: generate-depth-maps
description: Generate a depth map from a single RGB image with Marigold V2. Use when an image workflow needs monocular relative-depth estimation for compositing, relighting, parallax, masking, or approximate 3D reconstruction, especially in ComfyUI.
---

# Generate Depth Maps

Use the ComfyUI-ready [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0) model to estimate depth from one image.

## Workflow

1. Download the model files and place them in the ComfyUI model folders shown on the model card. Preserve the listed `diffusion_models`, `embeddings`, `loras`, and `vae` locations.
2. Select the depth components, including the depth conditioning, `depth_log_stage2` LoRA, and matching depth VAE.
3. Run the source image through a Marigold V2 depth workflow and save the depth output in a lossless format such as PNG or EXR.
4. Check that foreground and background depth ordering matches the source image before using the result downstream.

## Interpret the Result

- Treat the output as affine-invariant relative depth with an unknown scale and shift for each image. It is not metric distance without separate calibration.
- In the default log-depth output, larger values represent greater distance.
- Keep a high-bit-depth output when later operations need smooth depth gradients or precise masks.
- Consult the linked model card when filenames or the recommended ComfyUI workflow change.
