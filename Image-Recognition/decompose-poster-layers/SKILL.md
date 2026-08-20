---
name: decompose-poster-layers
description: Recover editable layer structures from flat raster graphics with a ReDesign-style agentic decomposition workflow. Use when the user asks for 拆圖、拆層、海報拆圖、字卡拆圖、平面設計還原、圖片轉可編輯圖層, or wants a poster, social card, banner, advertisement, slide cover, screenshot, PNG, or JPEG reconstructed as editable RGBA layers, text, vector shapes, groups, z-order, JSON, PSD, SVG, or a Figma-like file. Prefer this workflow for graphic-design layouts containing text, shapes, and placed images. Do not use it as the primary workflow for character or Live2D rigging, hidden-body-part completion, or skeletal/mesh animation preparation.
---

# Decompose Poster Layers

Use ReDesign as the first workflow to evaluate when a flat poster, title card, social card, banner, advertisement, or similar graphic must become independently editable layers. Treat ReDesign as an agentic method that composes existing tools, not as a proprietary model or downloadable ReDesign checkpoint.

## Route the Request

Choose the smallest workflow that satisfies the edit goal:

- Use ordinary background removal when the user needs only one foreground cutout.
- Prefer this workflow when the design contains multiple text, shape, image, group, or overlap relationships that must remain editable.
- Rebuild directly in HTML, SVG, or a design tool when semantic layout matters more than pixel-level reconstruction.
- Route character or Live2D work to a character-part and rigging workflow. It requires hidden-region completion, anatomy/part taxonomy, joint overlaps, mesh deformation, and motion parameters that ReDesign does not recover.

## Establish the Contract

Before decomposing:

1. Confirm that the user owns the image or is authorized to transform it. Preserve attribution and licensing metadata when supplied.
2. Record the source canvas width, height, color mode, and transparency.
3. Define the target: loose PNG layers, editable hierarchy JSON, SVG, PSD, Figma-like reconstruction, or another explicit format.
4. Define the useful granularity. Do not split decorative texture into hundreds of fragments unless those fragments need independent editing.
5. Identify required edit operations such as rewrite text, recolor, delete, move, rotate, resize, or reorder.

## Build an Editable Layer Tree

Start with the complete raster image as the root node. Grow a coarse-to-fine hierarchy breadth-first so that large groups and z-order relationships are established before fine details.

For each unresolved node, inspect its content and choose one action:

| Action | Use when | Preferred implementation | Expected children |
| --- | --- | --- | --- |
| Extract text | The node contains editable typography | OCR + font recognition + text mask + inpainting | Text metadata and a cleaned background |
| Fork layers | The node is a composite with overlapping semantic regions | Qwen-Image-Layered or an equivalent RGBA decomposition model | Several ordered RGBA layers |
| Split components | One layer contains spatially disconnected elements | Connected-component analysis | Disjoint child elements |
| Detect and segment | A named object or foreground region must be isolated | Object detection + segmentation + background inpainting | Foreground object and background |
| Vectorize | A leaf is a flat shape, icon, or simple graphic | VTracer or another tracing tool | Editable vector path |

Keep photographs and complex textures raster. Convert text to real text when recognition is reliable. Vectorize only shape-like leaves.

See [references/redesign-method.md](references/redesign-method.md) when implementing the full tool chain, comparing a lightweight substitute, or reporting research provenance.

## Verify Every Expansion

Run a local verifier immediately after each parent-to-children expansion. Return exactly one of these outcomes:

- `accept`: children plausibly explain the parent and improve editability.
- `prune`: remove hallucinated, empty, duplicate, or redundant children.
- `retry`: rerun the branch with a different tool, layer count, prompt, threshold, mask, or configuration.

Check all of the following before accepting an expansion:

- The alpha-composited children cover the parent without unexplained holes or major residuals.
- Siblings do not duplicate the same pixels or semantic object.
- No child invents text, objects, edges, or texture absent from the source.
- Boundaries have no obvious white/black halos, clipped shadows, or transparency seams.
- The proposed representation matches the content type: text, vector, or raster.
- The child ordering reproduces the parent when composited.

Store the selected action, parameters, verifier result, and retry history on the node. Repair only the failing branch instead of restarting the entire design.

## Stop at Atomic Editable Leaves

Finish a branch when each leaf represents one useful editable unit, such as one text box, shape, icon, photo, or indivisible decorative element. Avoid both extremes:

- Do not stop with a coarse layer containing several objects that must be edited independently.
- Do not over-decompose antialiasing, gradients, noise, or photographic texture into meaningless pieces.

## Export the Result

Preserve a tool-neutral canonical output even when also producing PSD, SVG, or another adapter:

```text
output/
  hierarchy.json
  manifest.json
  reconstruction.png
  verification.json
  layers/
    000-background.png
    010-title.png
    020-object.png
```

Include canvas geometry, node IDs, parent/child relationships, z-order, bounds, opacity, blend mode, content type, source lineage, and editable metadata. For text, include recognized content, font candidate, size, color, alignment, and confidence. For vectors, include path and fill/stroke properties.

## Run the Final Quality Gate

Do not declare success from the presence of layer files alone. Verify:

1. Recomposition uses the original dimensions and closely matches the source. Use visual inspection plus L1, PSNR, LPIPS, or SSIM when available.
2. Delete, move, resize, rotate, recolor, opacity, and z-order edits affect only the intended layer.
3. Text can be rewritten without editing neighboring artwork when text recovery was requested.
4. No required element is missing, duplicated, hallucinated, or flattened into the wrong sibling.
5. The chosen output opens in the target editor, or clearly state that the result is a canonical JSON/RGBA handoff rather than a native design file.

## Report Limitations Honestly

- Say `ReDesign pipeline` or `ReDesign method`; do not call it a `ReDesign model`.
- Distinguish a complete ReDesign run from using Qwen-Image-Layered alone. Qwen produces RGBA layers but does not by itself recover the full text/vector/group hierarchy or graceful verification loop.
- State when fonts, occluded backgrounds, or vector geometry were inferred rather than recovered exactly.
- Treat performance on Figma and Crello-style designs as evidence for graphic-design reconstruction, not proof of suitability for character rigging or arbitrary photographs.
- When the official stack is unavailable or too heavy, preserve the same controller/tree/verifier logic with available OCR, segmentation, inpainting, and tracing tools, and label the result `ReDesign-inspired` rather than an official ReDesign run.
