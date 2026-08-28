---
name: comfyui-node-migration
description: Migrate legacy ComfyUI V1 custom nodes to the public V3 API while preserving workflow compatibility, node IDs, inputs, outputs, validation, caching, UI behavior, and packaging.
---

# Migrate ComfyUI V1 nodes to V3

Migrate one node at a time and preserve observable contracts before refactoring behavior.

## Mapping

- INPUT_TYPES becomes define_schema returning io.Schema.
- RETURN_TYPES and RETURN_NAMES become schema outputs.
- FUNCTION becomes a classmethod execute.
- CATEGORY, DESCRIPTION, OUTPUT_NODE and similar class fields move into the schema.
- A raw tuple return becomes io.NodeOutput.
- NODE_CLASS_MAPPINGS becomes a ComfyExtension implementation returned by comfy_entrypoint.
- Legacy VALIDATE_INPUTS, IS_CHANGED and lazy-input hooks become their documented V3 equivalents.
- WEB_DIRECTORY remains package metadata but frontend code must follow current extension hooks.

Use the official mapping table because hook names and signatures can change:

https://docs.comfy.org/custom-nodes/v3_migration

## Compatibility rules

Keep the original node ID when existing workflows must continue loading. Keep input IDs, output order and types stable unless a deliberate migration path exists.

Do not silently change widget defaults, enum values, list behavior or cache semantics. If a breaking change is unavoidable, add a new node ID and mark the old node deprecated only after validating workflow replacement behavior.

## Process

1. Capture a representative legacy workflow and expected outputs.
2. Port registration and schema without changing computation.
3. Port execute and return io.NodeOutput.
4. Port validation, fingerprints, lazy inputs and UI outputs separately.
5. Export and reload both UI and API workflow formats.
6. Test old workflow JSON on the target ComfyUI release.
7. Remove legacy code only after parity is demonstrated.

## Node replacement

Use the current official node-replacement mechanism when renaming or splitting nodes. Do not invent a JSON rewrite rule or rely on display names.

## Completion check

Verify startup registration, old workflow loading, prompt validation, one execution per branch, cache behavior, output order, UI previews and package installation from a clean environment.
