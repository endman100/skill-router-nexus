---
name: comfyui-node-advanced
description: Implement supported advanced ComfyUI V3 node patterns such as type matching, autogrowing inputs, dynamic combos, expansion, custom types, and wildcard compatibility. Use only after basic V3 nodes work.
---

# Advanced ComfyUI V3 nodes

Advanced schema features change faster than core inputs and outputs. Confirm every class and parameter against the installed public comfy_api namespace before use.

## Type matching and autogrow

Use the documented MatchType and Autogrow facilities when multiple sockets must share a type or a repeated input group must grow in the UI. Keep match groups local and test reconnection behavior.

These mechanisms have limitations at subgraph boundaries. Read the current frontend limitation document before depending on them:

https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/core/graph/subgraph-dynamic-input-limitations.md

## Dynamic combo options

Prefer a callable or documented dynamic-combo provider when choices depend on installed resources. Make enumeration deterministic and inexpensive. Validate the selected value again during execution because models and files can change after the UI list was created.

## Node expansion

Use node expansion only when the current API explicitly supports the required graph transformation. Generated nodes must use valid class types, unique IDs, correct output indices and serializable inputs. Validate the expanded graph through the server before queueing it.

## Wildcards and multiple accepted types

Prefer explicit public types. Use wildcard or multi-type compatibility only at integration boundaries and validate the concrete runtime value before processing it. Avoid private implementation imports and undocumented string sentinels.

## Custom types

Create a public custom type with the documented comfytype mechanism. Give it a stable unique identifier and define compatibility deliberately. Do not rely on Python class identity alone when the value crosses node packages.

## Source of truth

- https://docs.comfy.org/custom-nodes/v3_migration
- https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_api/latest/_io.py
- https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/core/graph/subgraph-dynamic-input-limitations.md

## Completion check

Test schema registration, save/reload, copy/paste, reconnection, subgraph behavior, API-format export and server execution. Remove the advanced mechanism if a normal fixed schema solves the same task.
