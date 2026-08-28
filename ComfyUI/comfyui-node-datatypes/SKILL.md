---
name: comfyui-node-datatypes
description: Select and handle current ComfyUI V3 data types for tensors, models, conditioning, audio, video, 3D data, collections, geometry, widgets, and custom values.
---

# ComfyUI V3 data types

Treat the installed public io module as the authoritative type registry. The list evolves; this Skill intentionally does not claim to be exhaustive.

## Core families

Common public families include:

- Tensors and diffusion data: Image, Mask, Latent, Conditioning
- Model pipeline objects: Model, Clip, Vae, ControlNet, Gligen
- Scalars and widgets: String, Boolean, Int, Float, Combo
- Media: Audio and Video
- Collections and structured data: List, Dict, Array and release-specific structured types
- Geometry and UI data: Colors, BoundingBoxes, Range, Histogram and release-specific 3D file or preview types
- Dynamic facilities: MatchType, Autogrow, Splat, MultiType or equivalents exposed by the selected API version

Inspect current exports at:

https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_api/latest/_io.py

Import types through the public io namespace.

## Tensor contracts

Images normally use floating tensors shaped batch, height, width, channels. Masks normally use batch, height, width. Latents are dictionaries whose keys depend on the model pipeline. Do not assume every latent contains only samples.

Preserve batch dimensions. Validate dtype, device, channel count and value range at the node boundary. Avoid unconditional CPU/GPU transfers.

## Model objects

Pass model, CLIP, VAE, conditioning and control objects through their declared socket types. Do not serialize, deep-copy or inspect undocumented internals unless the node explicitly owns that integration.

## Structured and custom values

Use built-in structured types when available. For a true domain object, define a documented custom type with a stable identifier and clear compatibility rules. Validate values before crossing package boundaries.

## Selection rule

1. Use the narrowest public type that represents the value.
2. Use a collection type only when the entire collection is one socket value.
3. Use list execution semantics only for ComfyUI execution lists.
4. Use wildcard/multi-type sockets only at adapter boundaries.
5. Pin or test the API namespace when using newly added types.

## Completion check

Test one valid value, one invalid value, empty and batched forms, device movement, serialization/save-reload, and compatibility with at least one core node.
