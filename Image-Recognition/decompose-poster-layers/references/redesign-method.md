# ReDesign Method Reference

Read this reference when implementing, testing, or explaining the full ReDesign-style workflow. Use the parent `SKILL.md` for the routing rules, official action map, and per-expansion quality gate; use this file for the controller loop, execution levels, evaluation, and provenance.

## Control Loop

```text
tree = root(input_raster)
queue = [root]

while queue contains an unresolved node:
    parent = queue.pop_front()
    action, parameters = controller(parent, tree, history)
    proposed_children = run(action, parent, parameters)
    verdict = verifier(parent, proposed_children, tree)

    if verdict == accept:
        attach(proposed_children)
        queue.extend(non_atomic(proposed_children))
    elif verdict == prune:
        attach(valid_subset(proposed_children))
        queue.extend(non_atomic(valid_subset(proposed_children)))
    elif verdict == retry:
        record_failure(parent, action, parameters, verdict.reason)
        queue.push_front(parent)

export_editable_hierarchy(tree)
```

The important invariant is local repair: detect divergence at the parent-to-children edge and retry only that branch.

## Practical Execution Levels

### Full reproduction

Use the official repository, its documented environment, downloaded checkpoints, and an OpenAI-compatible VLM endpoint. Inspect the current upstream README before installing because dependency, CUDA, and entrypoint details can change.

### Lightweight trial

Use Qwen-Image-Layered for an initial coarse split, then apply available OCR, mask refinement, inpainting, connected components, and tracing. Retain the tree and verifier loop. Label this a ReDesign-inspired implementation.

### Minimal fallback

For machines unable to host the layered model, combine OCR, conventional segmentation, connected components, and vector tracing. Ask for human mask correction where occlusion or typography confidence is low. Do not imply benchmark-equivalent performance.

Qwen-Image-Layered is a 20B BF16 model and its Hugging Face repository is large, so check storage, GPU memory, CUDA compatibility, and inference time before downloading or promising a local run.

## Evaluation Guidance

Evaluate both reconstruction and actual editability:

- Reconstruction: alpha-compose all leaves and compare against the source using alignment checks and perceptual/pixel metrics.
- Structure: inspect hierarchy, grouping, z-order, content types, masks, and sibling coverage.
- Edit replay: perform delete, move, resize, rotate, recolor, opacity, z-order, and text-rewrite operations, then compare the rendered edit with the intended result.
- Failure audit: list missing content, duplicates, hallucinations, residual backgrounds, mask seams, OCR errors, font substitutions, and incorrect vectorization.

Do not infer character-rigging readiness from these tests. Live2D requires a separate target representation and animation-specific validation.

## Primary Sources

- ReDesign paper: https://arxiv.org/abs/2607.25565
- Official implementation: https://github.com/jintae-00/ReDesign
- Project page: https://jintae-00.github.io/ReDesign/
- Figma-909 dataset: https://huggingface.co/datasets/Jintae-Park/ReDesign-Figma909
- Qwen-Image-Layered model card: https://huggingface.co/Qwen/Qwen-Image-Layered

At the time this reference was written, the paper reports evaluation on Figma-909 and Crello-style designs. Re-check upstream sources before reporting current installation requirements, licenses, model sizes, or benchmark claims.
