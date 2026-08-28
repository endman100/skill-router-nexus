---
name: comfyui-node-frontend
description: Extend the current ComfyUI frontend with supported JavaScript extension hooks, commands, settings, menus, sidebar tabs, badges, dialogs, and custom widgets.
---

# ComfyUI frontend extensions

Place frontend files under the package WEB_DIRECTORY and register an extension through the supported frontend API.

    import { app } from '../../scripts/app.js'
    import { api } from '../../scripts/api.js'

    app.registerExtension({
      name: 'example.extension',
      setup() {
        // Register supported UI behavior here.
      },
    })

Import paths depend on where the file is served. Confirm them against the current frontend extension documentation.

## Use supported hooks

Prefer documented extension hooks, commands, settings, menus, bottom panels, sidebar tabs, badges, toasts and dialogs.

Use documented extension hooks rather than overriding internal LiteGraph objects. Current frontend releases use subgraphs and frontend-managed IDs.

## Compatibility workflow

1. Identify the minimum ComfyUI frontend version.
2. Read the current ComfyExtension type and official migration notes.
3. Register only documented fields.
4. Feature-detect optional hooks.
5. Remove listeners and DOM resources when the extension unloads or rerenders.
6. Test with the browser console open and no cached frontend bundle.

## Security and stability

Escape untrusted text before inserting it into the DOM. Use the provided API client for server calls. Do not embed credentials, read arbitrary local paths, or attach global listeners without cleanup.

## Sources

- https://docs.comfy.org/custom-nodes/js/javascript_overview
- https://docs.comfy.org/custom-nodes/js/javascript_hooks
- https://docs.comfy.org/custom-nodes/js/context-menu-migration
- https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/types/comfy.ts

## Completion check

Test initial load, refresh, workflow reload, duplicate nodes, subgraphs, multiple tabs, dark/light themes if relevant, and frontend versions at the declared compatibility boundary.
