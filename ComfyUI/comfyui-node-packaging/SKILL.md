---
name: comfyui-node-packaging
description: Package and publish current ComfyUI custom nodes with pyproject.toml metadata, extension registration, frontend assets, help pages, dependencies, tests, and the official Comfy Registry workflow.
---

# Package a ComfyUI custom node

Use a normal Python package layout with a root entrypoint that exports comfy_entrypoint or the registration form required by the target API version.

    package-root/
      __init__.py
      pyproject.toml
      requirements.txt
      nodes/
      web/
        js/
        docs/

Set WEB_DIRECTORY to the directory served by ComfyUI when frontend assets exist. Put node help documents under WEB_DIRECTORY/docs, not at the package root.

## Dependencies

Declare only dependencies the node imports. Do not assume optional ML packages such as accelerate are bundled with ComfyUI. Check the current core requirements and test installation in a clean environment.

Use ComfyUI folder-path utilities for models and outputs. Do not derive the ComfyUI installation path from the working directory.

## Registry metadata

Follow the current Comfy Registry pyproject specification:

- https://docs.comfy.org/registry/specifications
- https://docs.comfy.org/registry/publishing

Validate package name, publisher ID, version, license, repository URL, supported operating systems and accelerator declarations against the current schema. Do not copy obsolete metadata keys from older examples.

## Publishing

Prefer the current Comfy-Org/publish-node-action workflow. Store the Registry token as REGISTRY_ACCESS_TOKEN and pass it exactly as the current action documentation requires.

Pin third-party GitHub Actions to reviewed versions or commit SHAs according to the repository security policy. Publish only from a tagged, tested revision.

## Release checklist

1. Install into a clean ComfyUI environment.
2. Confirm backend registration and frontend asset loading.
3. Run node tests and a representative workflow.
4. Validate pyproject.toml and Registry ownership.
5. Check licenses for bundled code, models and assets.
6. Build the release artifact from tracked files.
7. Publish with the official action and verify the Registry entry.
8. Install the published version and rerun the smoke workflow.

Keep API compatibility claims tied to tested ComfyUI versions. Avoid claiming support for comfy_api.latest without continuous testing.
