---
name: xiaomi-lens-clothes-mask
description: "Create a clothes-only mask for outfit edits or inpainting using Xiaomi-Lens-0 text-guided segmentation, then subtract SegFormer B2 Clothes face, arm, and leg regions to exclude skin."
---

# Xiaomi-Lens clothes-only mask

## When to use

Use an image plus a garment description to select clothing for outfit editing or inpainting while excluding skin. This wrapper documents upstream tools; install models and dependencies in a separate working directory, outside this skill repository.

Verified on 2026-11-12: [Xiaomi-Lens-0](https://huggingface.co/SeerRay-Lab/Xiaomi-Lens-0) is described as a **4B** multimodal model built on **Qwen3.5-4B** with a lightweight mask decoder. It segments regions from text instructions; each emitted `<|mask|>` token decodes to one mask. See the [official code](https://github.com/SeerRay-Lab/Xiaomi-Lens-0), [technical report, arXiv:2610.23279](https://arxiv.org/abs/2610.23279), and [project page](https://seerray-lab.github.io/Xiaomi-Lens-0/).

## Install

The official inference path requires Python **3.10+** and a CUDA GPU supporting **bfloat16 and FlashAttention-2**. In a suitable Python environment, use the [official installation commands](https://github.com/SeerRay-Lab/Xiaomi-Lens-0#-quick-start):

```bash
git clone https://github.com/SeerRay-Lab/Xiaomi-Lens-0.git
cd Xiaomi-Lens-0
pip install -r requirements.txt
pip install -e .
```

The checkpoint argument below loads the [official HF weights](https://huggingface.co/SeerRay-Lab/Xiaomi-Lens-0); a downloaded checkpoint directory also works.

Optional: [ComfyUI-XiaomiLens](https://github.com/hiroki-abe-58/ComfyUI-XiaomiLens) is an **unofficial** integration. Follow its own installation and model-download instructions. Its Segment node exposes a union `mask`, per-instance `instance_masks`, and a separate `preview`; apply the skin subtraction to mask data.

## Write the instruction and obtain masks

Choose a description such as `clothes` or `shirt and skirt`; specify the person when several people appear. These garment prompts are suggested inputs, not verified quality examples. From the official repo root, use its grounding instruction format:

```bash
python infer.py \
  --checkpoint SeerRay-Lab/Xiaomi-Lens-0 \
  --image /path/to/image.jpg \
  --text 'Locate all instances in the image that match the description "shirt and skirt". Report bbox coordinates and masks.' \
  --output clothes-preview.jpg --draw-bbox
```

Each grounded instance is represented by `<bbox>[x1, y1, x2, y2]</bbox><mask><|mask|></mask>`; boxes use 0–1000 coordinates. Mask tensors follow token order, including tokens inside `<think>`. Exclude those reasoning masks and union only the desired final-answer garment masks. A compound description need not yield exactly one mask per garment. No final-answer mask means no usable selection; inspect or refine the instruction.

**The CLI saves colored overlays, including with `--per-mask-output`; these are not binary editing masks.** For binary data, follow the [official README Python API](https://github.com/SeerRay-Lab/Xiaomi-Lens-0#-quick-start) through `generate_completion`, then use its `run_forward` and `split_answer_content` helpers. The following continuation assumes the variables and imports from that example; it unions all answer masks, so first verify they refer only to the requested clothing:

```python
_, n_thought = split_answer_content(completion)
if num_masks <= n_thought:
    raise ValueError("No final-answer mask; refine the instruction")
logits = run_forward(model, inputs, completion_ids, mask_token_id, device)
answer_masks = logits[:, n_thought:].sigmoid() > 0.5
clothes = answer_masks[0].any(dim=0).cpu().numpy()
clothes = Image.fromarray(clothes.astype("uint8") * 255).resize(
    image.size, Image.Resampling.NEAREST)
```

Decoder masks use the resized vision-input canvas. Map them back to the original RGB image dimensions before combining masks; preserve image orientation and crop alignment. The example above resizes the binary union with nearest-neighbor interpolation.

## Subtract skin with SegFormer B2 Clothes

Run [mattmdjaga/segformer_b2_clothes](https://huggingface.co/mattmdjaga/segformer_b2_clothes) on the **same original image**. Its model card lists these body-part classes for exclusion:

| ID | Exact label |
|---|---|
| 11 | Face |
| 12 | Left-leg |
| 13 | Right-leg |
| 14 | Left-arm |
| 15 | Right-arm |

These are the five relevant body-part labels in its 18-class taxonomy. There is **no generic Skin class or separate neck, chest, torso, or hand label**; do not invent additional IDs. Hair (2) is a separate non-garment class, not a skin label.

Use the model card's processor/model and bilinear-logit-upsample pattern, then subtract the body-part union. This short wrapper example continues with the original PIL `image` and aligned PIL `clothes` mask above; it uses CPU for SegFormer to avoid retaining another GPU model:

```python
import numpy as np
import torch
import torch.nn.functional as F
from transformers import SegformerImageProcessor, AutoModelForSemanticSegmentation

model_id = "mattmdjaga/segformer_b2_clothes"
parser_processor = SegformerImageProcessor.from_pretrained(model_id)
parser_model = AutoModelForSemanticSegmentation.from_pretrained(model_id).eval()
with torch.inference_mode():
    inputs = parser_processor(images=image, return_tensors="pt")
    logits = parser_model(**inputs).logits
labels = F.interpolate(logits, size=(image.height, image.width),
                       mode="bilinear", align_corners=False).argmax(1)[0].numpy()
skin = np.isin(labels, [11, 12, 13, 14, 15])
clean = (np.asarray(clothes) > 0) & ~skin
Image.fromarray(clean.astype("uint8") * 255).save("clothes-only-mask.png")
```

The intended result is a clean clothes-only mask: white (255) selects clothing, black (0) excludes everything else. This subtraction removes **predicted** skin regions and does not guarantee zero skin leakage. Review the mask over the source image, especially neckline, hands, garment openings, sleeves, and hems; manually remove remaining skin and recover wrongly removed fabric before inpainting. For a stricter shirt/skirt/pants/dress selection, optionally intersect with SegFormer's garment labels **4 Upper-clothes, 5 Skirt, 6 Pants, 7 Dress**; this can also remove valid clothing when the parser is wrong.

## Known risks and verification status

- Accuracy **may drop on anime images**; this is an unverified domain-shift risk, not a measured result from the sources checked.
- **Not yet tested by joe.** Installation, garment prompts, mask extraction, and the combined subtraction workflow have been checked against source documentation, not run end to end here.
- **“4B probably runs on a 16 GB GPU” is an ESTIMATE, not verified.** Planned test machine: **gazai** (user-provided plan; no test completed). Resolution, generated token count, decoder implementation, and other loaded models affect memory use; parameter count alone is insufficient.
- Skin/body-part misclassification can leave skin or erase fabric. Unrepresented skin regions require visual review; an empty mask or visibly poor boundary is not ready for editing.

## Licenses

- Xiaomi-Lens-0 code and weights: **Apache-2.0**, verified in the [official code license](https://github.com/SeerRay-Lab/Xiaomi-Lens-0/blob/main/LICENSE) and HF model card.
- SegFormer B2 Clothes: its [model card](https://huggingface.co/mattmdjaga/segformer_b2_clothes#license) declares **license: other** and links to the [NVIDIA Source Code License for SegFormer](https://github.com/NVlabs/SegFormer/blob/master/LICENSE). Section 3.3 limits use to noncommercial **research or evaluation** (with an NVIDIA/affiliate exception). Do not assume these weights inherit Xiaomi-Lens-0's Apache license or permit commercial outfit-editing use.

Classification decision: `KEEP_FLAT` in `Image-Recognition`; the core task is text-guided segmentation and human parsing. Existing SAM/grounding skills do not cover this two-model clothes-mask workflow; no index or taxonomy update is needed.
