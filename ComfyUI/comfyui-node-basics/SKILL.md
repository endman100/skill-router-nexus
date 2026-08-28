---
name: comfyui-node-basics
description: Build ComfyUI custom nodes with the current V3 schema API. Use when creating node classes, defining schemas, registering extensions, or choosing between stable and latest ComfyUI APIs.
---

# ComfyUI V3 node basics

Use the public comfy_api package. Treat comfy_api.latest as a moving development alias; for maintained packages, pin the newest versioned namespace supported by the target ComfyUI release when one is available.

## Minimal node

    from comfy_api.latest import ComfyExtension, io

    class AddNumbers(io.ComfyNodeABC):
        @classmethod
        def define_schema(cls):
            return io.Schema(
                node_id='Example.AddNumbers',
                display_name='Add Numbers',
                category='examples/math',
                inputs=[
                    io.Float.Input('a', default=0.0),
                    io.Float.Input('b', default=0.0),
                ],
                outputs=[io.Float.Output(display_name='result')],
            )

        @classmethod
        def execute(cls, a: float, b: float) -> io.NodeOutput:
            return io.NodeOutput(a + b)

    class ExampleExtension(ComfyExtension):
        async def get_node_list(self):
            return [AddNumbers]

    async def comfy_entrypoint():
        return ExampleExtension()

Keep node_id globally unique and stable after release. Return io.NodeOutput in the same order as schema outputs.

## Schema fields

Use only fields exposed by the selected public io.Schema implementation. Current fields include node_id, display_name, category, inputs, outputs, hidden, description, search_aliases, is_input_list, is_output_node, is_deprecated, is_experimental, is_dev_only, is_api_node, not_idempotent, enable_expand, accept_all_inputs, essentials_category and has_intermediate_output.

Do not copy a schema field from this Skill without checking the target ComfyUI version. Inspect:

- https://docs.comfy.org/custom-nodes/v3_migration
- https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_api/latest/_io.py

## Rules

1. Import through comfy_api.latest or a documented versioned namespace. Do not import private modules such as comfy_api.latest._io.
2. Make execute a classmethod and keep its argument names aligned with schema input IDs.
3. Use not_idempotent only when results can differ despite identical inputs. It changes cache reuse semantics; it is not a blanket 'disable all caching' switch.
4. Set has_intermediate_output only when the node deliberately emits progress or intermediate UI state.
5. Query the installed source or official docs before using experimental fields.
6. Verify the node in a clean ComfyUI install and inspect startup logs for schema-registration errors.

## Completion check

Confirm that the extension loads, the node appears in the expected category, one workflow executes, outputs match the schema, and a second run demonstrates the intended cache behavior.
