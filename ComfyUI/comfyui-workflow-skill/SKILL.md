---
name: comfyui-workflow-skill
description: Build, validate, convert, and repair current ComfyUI workflows using the target server's installed node schemas and official templates. Use for image, video, audio, 3D, LLM, inpainting, ControlNet, LoRA, upscaling, or custom-node workflows.
---

# Build reliable ComfyUI workflows

Build against the target installation, not a frozen node catalog.

## Choose the required format

Ask or infer the destination:

- UI workflow JSON: editable visual graph. Follow the current Workflow JSON schema.
- API prompt JSON: executable object keyed by node IDs, each containing class_type and inputs.

Current UI schema:

https://docs.comfy.org/specs/workflow_json

Do not label LiteGraph UI JSON as API format and do not POST it directly to /prompt.

## Build process

1. Inspect GET /object_info on the target server.
2. Inventory required model filenames and custom-node packages.
3. Start from a workflow exported by the same ComfyUI version or a current official template.
4. Make the smallest graph change necessary.
5. Preserve node IDs, link types and output indices consistently.
6. Validate every class_type and input against /object_info.
7. Validate referenced model filenames against the target inventory.
8. For API execution, queue through POST /prompt and inspect node_errors before waiting.
9. Save provenance: ComfyUI version, template source and required custom-node packages.

Official templates:

https://github.com/Comfy-Org/workflow_templates

Fetch the current repository index when needed. Do not hardcode template counts, categories or filenames.

## Model selection

Use the current official tutorial for the requested family and hardware. Avoid guessing loader classes or file names from model marketing names. Modern pipelines can require separate diffusion, text-encoder and VAE files, multiple experts, or architecture-specific latent nodes.

Relevant current tutorial index:

https://docs.comfy.org/tutorials

## Connections

In API prompt format, a connection is normally represented by node ID and output index:

    "model": ["4", 0]

Literal values remain literals. All required inputs must be present, including scheduler, sampler, noise, latent, conditioning and model-specific settings.

## Repair process

When a workflow fails:

1. Preserve the original.
2. Identify missing class types and invalid input names through /object_info.
3. Map renamed nodes only with official or package migration evidence.
4. Replace unavailable models only after reporting the semantic difference.
5. Revalidate, queue a minimal run and inspect history.
6. Return the corrected workflow plus a dependency list.

## Guardrails

Do not auto-download executable custom nodes or models without explicit approval. Verify licenses, hashes and sources. Never invent a node class_type, model filename, download URL or output index.

## Completion check

A workflow is complete only when it parses, matches the requested format, validates against the target /object_info, references available models, queues without node_errors, and produces or reaches the expected terminal result.
