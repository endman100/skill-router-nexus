---
name: comfyui-research
description: Research current ComfyUI releases, APIs, models, workflows, custom nodes, licenses, and breaking changes. Use before making time-sensitive recommendations or updating any ComfyUI Skill.
---

# Research current ComfyUI behavior

Use fresh primary evidence. Do not treat this Skill or an old workflow as a current source.

## Source order

1. ComfyUI release notes and repository
2. Official ComfyUI documentation and workflow templates
3. Model publisher repository or model card
4. Custom-node publisher repository and releases
5. Reproducible community reports

Prefer:

- https://github.com/Comfy-Org/ComfyUI
- https://github.com/Comfy-Org/ComfyUI_frontend
- https://docs.comfy.org
- https://github.com/Comfy-Org/workflow_templates

## Research process

1. State the target topic and current date.
2. Check the latest ComfyUI release and relevant official documentation.
3. Inspect the target installation version when recommendations will be executed locally.
4. For a model, verify official file names, architecture, encoders, VAE, license and hardware guidance from its publisher.
5. For a custom node, verify maintenance status, compatible versions, installation method, dependencies and license from its repository.
6. Compare publication dates and distinguish release date from article date.
7. Record uncertainty and conflicts.
8. Cite direct sources next to each time-sensitive claim.

## Freshness policy

Recheck rather than relying on age alone:

- Core routes, node APIs and frontend hooks: before editing integration code
- Model files and official workflows: before generating a workflow
- Custom-node installation and compatibility: before recommending installation
- Licensing and commercial-use terms: before production use
- Performance and VRAM claims: on the target hardware or from a clearly labeled benchmark

## Updating Skills

When asked to update the knowledge base:

1. Remove facts that cannot be verified or are no longer needed.
2. Replace hardcoded counts, rankings and volatile filenames with discovery steps.
3. Keep a specific version only when the instruction is intentionally version-bound.
4. Link directly to the authoritative source.
5. Run static checks for missing local references and retired Skill names.
6. Do not create state, watch-list or report files unless the user requested persistent research tracking.

## Output

Return a concise table of claim, current finding, source date, source and confidence. Separate confirmed facts from inference. Never claim a workflow, model or node works without either official compatibility evidence or an executed test.
