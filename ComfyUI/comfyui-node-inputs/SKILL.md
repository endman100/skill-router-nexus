---
name: comfyui-node-inputs
description: Define current ComfyUI V3 node inputs, widgets, connections, optional and hidden inputs. Use when configuring input schemas or debugging input validation and UI behavior.
---

# ComfyUI V3 inputs

Define inputs with the public classes exported by comfy_api. Check the installed API before using newer widget types.

## Common inputs

    inputs=[
        io.Int.Input('steps', default=20, min=1, max=100),
        io.Float.Input('cfg', default=7.0, min=0.0, max=30.0, step=0.1),
        io.String.Input('prompt', multiline=True),
        io.Boolean.Input('enabled', default=True),
        io.Combo.Input('sampler', options=['euler', 'dpmpp_2m']),
        io.Image.Input('image'),
    ]

Use a connection type such as io.Image.Input when the value must come from another node. Use widget-capable scalar inputs for editable UI controls.

## Optional and hidden values

Mark an input optional only when execute has a safe default or handles absence explicitly. Keep input IDs and execute parameter names identical.

Hidden inputs are supplied by the runtime rather than by a visible widget. Use only members exported by the current io.Hidden API. Current installations may expose values such as node ID, display node ID, workflow, dynamic prompt, extra PNG info, authentication token, API key/comfy usage data, or source information. Do not hardcode a hidden member from an older release; inspect:

- https://docs.comfy.org/custom-nodes/v3_migration
- https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_api/latest/_io.py

Some output or API nodes receive runtime-managed hidden values automatically. Do not duplicate those inputs unless the installed schema requires them.

## Dynamic behavior

Use lazy inputs only when execution can decide which connected values are actually needed. Implement check_lazy_status and test every branch.

Use documented MatchType or Autogrow inputs for supported dynamic connection patterns.

## Validation checklist

- Defaults satisfy min, max and option constraints.
- execute accepts every declared input.
- Missing optional inputs do not raise.
- Hidden values are not exposed as normal widgets.
- Dynamic inputs work across the intended graph boundary; MatchType and Autogrow have subgraph limitations.
- The node passes registration and one real execution on the target ComfyUI version.
