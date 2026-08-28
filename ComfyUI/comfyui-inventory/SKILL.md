---
name: comfyui-inventory
description: Discover the capabilities of a current ComfyUI installation, including node schemas, model folders, custom nodes, runtime versions, devices, and workflow compatibility. Use before generating or repairing workflows.
---

# Inspect a ComfyUI installation

Inventory the actual target instance. Do not infer installed models or nodes from generic examples.

## Online inspection

1. GET /system_stats for ComfyUI, Python, PyTorch, device and memory information exposed by the server.
2. GET /object_info for installed node class types, required and optional inputs, return types, categories and metadata.
3. Use documented model-folder routes when available.
4. Submit a dry validation through /prompt only with user approval if it would enqueue work; otherwise validate locally against /object_info.
5. Record custom-node package versions from the installation or manager when available.

Route details:

https://docs.comfy.org/development/comfyui-server/comms_routes

## Offline inspection

When the server is unavailable:

- Locate the exact ComfyUI installation supplied by the user.
- Enumerate model folders through ComfyUI's folder_paths configuration, including extra_model_paths.yaml.
- Inspect custom_nodes package metadata and version-control revisions.
- Read requirements and runtime versions without importing untrusted custom-node code.
- Mark results as offline and potentially incomplete.

Do not assume the current working directory is the ComfyUI root.

## Inventory output

Return a timestamped summary containing:

- server/base path and inspection mode
- ComfyUI commit or release when discoverable
- Python, PyTorch, accelerator and memory
- installed node class types or package summary
- model categories and filenames
- missing requirements for the requested workflow
- confidence and limitations

Do not persist an inventory file unless the caller asks for one. If persisted, place it in a user-approved project path and include generated_at plus the target instance identity.

## Compatibility check

For each workflow node:

1. Confirm class_type exists in /object_info.
2. Confirm required input names and accepted types.
3. Confirm referenced model filenames exist in the correct model category.
4. Confirm custom-node versions support saved widget values.
5. Report substitutions rather than silently changing the workflow.
