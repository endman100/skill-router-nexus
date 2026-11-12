---
name: xiaomi-lens
description: "Use Xiaomi-Lens-0 for general text-prompted image segmentation, referring-expression masks, multi-instance grounding, and reasoning segmentation. Covers official installation, instructions, mask decoding, and the optional unofficial ComfyUI integration."
---

# Xiaomi-Lens

Verified on 2026-11-12: [Xiaomi-Lens-0](https://huggingface.co/SeerRay-Lab/Xiaomi-Lens-0) is described as a **4B** multimodal model built on **Qwen3.5-4B** with a lightweight mask decoder. It segments regions from text instructions; each emitted `<|mask|>` token decodes to one mask. Code and weights use **Apache-2.0**, verified in the [official code license](https://github.com/SeerRay-Lab/Xiaomi-Lens-0/blob/main/LICENSE) and HF model card.

Sources: [official code](https://github.com/SeerRay-Lab/Xiaomi-Lens-0), [weights/model card](https://huggingface.co/SeerRay-Lab/Xiaomi-Lens-0), [technical report, arXiv:2610.23279](https://arxiv.org/abs/2610.23279), and [project page](https://seerray-lab.github.io/Xiaomi-Lens-0/).

## When to use

Use an image plus a text instruction to locate and segment described objects or regions, find multiple instances, or resolve a target through reasoning. Masks can support annotation, cutouts, compositing, and editing workflows. This wrapper documents upstream tools; install models and dependencies in a separate working directory, outside this skill repository.

## Install

The official inference path requires Python **3.10+** and a CUDA GPU supporting **bfloat16 and FlashAttention-2**. In a suitable Python environment, use the [official installation commands](https://github.com/SeerRay-Lab/Xiaomi-Lens-0#-quick-start):

```bash
git clone https://github.com/SeerRay-Lab/Xiaomi-Lens-0.git
cd Xiaomi-Lens-0
pip install -r requirements.txt
pip install -e .
```

The checkpoint argument below loads the [official HF weights](https://huggingface.co/SeerRay-Lab/Xiaomi-Lens-0); a downloaded checkpoint directory also works.

Optional: [ComfyUI-XiaomiLens](https://github.com/hiroki-abe-58/ComfyUI-XiaomiLens) is an **unofficial** integration. Follow its own installation and model-download instructions. Its Segment node exposes a union `mask`, per-instance `instance_masks`, and a separate `preview`.

## Write the instruction and obtain masks

Describe the target clearly, including position or appearance when similar objects are present. Request bbox coordinates and masks using the official grounding instruction format:

```bash
python infer.py \
  --checkpoint SeerRay-Lab/Xiaomi-Lens-0 \
  --image /path/to/image.jpg \
  --text 'Locate all instances in the image that match the description "the cat on the left". Report bbox coordinates and masks.' \
  --output result.jpg --draw-bbox
```

Examples of instruction styles shown by upstream:

- Referring expression: `the cat on the left`, inserted into the grounding template above.
- Multiple instances: `all bottles`, inserted into the same template.
- Reasoning: `What could be used to package a gift?` Request bbox coordinates and masks when a spatial output is needed.

Each grounded instance is represented by `<bbox>[x1, y1, x2, y2]</bbox><mask><|mask|></mask>`; boxes use 0–1000 coordinates. Mask tensors follow token order, including tokens inside `<think>`. Exclude those reasoning masks when consuming only the final answer. No final-answer mask means no usable selection; inspect or refine the instruction.

**The CLI saves colored overlays, including with `--per-mask-output`; these are not binary editing masks.** For binary data, follow the [official README Python API](https://github.com/SeerRay-Lab/Xiaomi-Lens-0#-quick-start) through `generate_completion`, then use its `run_forward` and `split_answer_content` helpers. This continuation assumes the variables and imports from that example:

```python
_, n_thought = split_answer_content(completion)
if num_masks <= n_thought:
    raise ValueError("No final-answer mask; refine the instruction")
logits = run_forward(model, inputs, completion_ids, mask_token_id, device)
answer_masks = logits[:, n_thought:].sigmoid() > 0.5  # (1, K, H, W)
```

Keep masks separate for per-instance operations, or union the desired masks for a combined selection. Decoder masks use the resized vision-input canvas. Map them back to the original RGB image dimensions before combining them with other image data; preserve image orientation and crop alignment. Use nearest-neighbor interpolation when resizing binary masks.

## Known limits and verification status

- Predictions can miss objects or produce inaccurate boxes and masks, particularly for small, occluded, or ambiguous regions. Inspect the selected instances and boundaries before downstream use; a text description does not guarantee an exact selection.
- The supplied official inference path supports images. Do not assume video tracking or other input modes from this wrapper.
- **Not yet tested by joe.** Installation and mask extraction have been checked against source documentation, not run end to end here. Upstream examples are not local quality measurements.
- **“4B probably runs on a 16 GB GPU” is an ESTIMATE, not verified or tested.** Resolution, generated token count, decoder implementation, and other loaded models affect memory use; parameter count alone is insufficient.

Classification decision: `KEEP_FLAT` in `Image-Recognition`; the core task is text-guided segmentation and visual grounding. No index or taxonomy update is needed.
