---
name: comfyui-node-outputs
description: Return typed data and UI previews from current ComfyUI V3 custom nodes. Use when defining node outputs, previewing media, saving results, or implementing output nodes.
---

# ComfyUI V3 outputs

Declare output types in io.Schema and return io.NodeOutput with values in the same order.

    class SplitText(io.ComfyNodeABC):
        @classmethod
        def define_schema(cls):
            return io.Schema(
                node_id='Example.SplitText',
                inputs=[io.String.Input('text')],
                outputs=[
                    io.String.Output(display_name='original'),
                    io.Int.Output(display_name='length'),
                ],
            )

        @classmethod
        def execute(cls, text):
            return io.NodeOutput(text, len(text))

Never return a bare tuple from a V3 node.

## UI output

Use UI helper classes currently exported by comfy_api.latest._ui for previews and saved results. Available helpers vary by release and can include image, mask, audio, text, video and 3D previews.

Check the installed public API rather than memorizing helper names:

- https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_api/latest/_ui.py
- https://docs.comfy.org/custom-nodes/v3_migration

For media saved to ComfyUI output or temporary directories, use the official helpers or path utilities so filenames, subfolders, MIME types and preview metadata match frontend expectations.

## Output-node rules

Set is_output_node only when the node performs a terminal side effect such as saving or sending data. A preview-only node may also need output-node behavior depending on the helper and target version; verify against the installed implementation.

Keep large tensors and media in typed outputs. UI payloads should contain compact metadata, not duplicated binary content.

## Completion check

Verify socket types, output order, frontend preview rendering, saved-file location, and queue completion. Test empty batches and unsupported media separately.
