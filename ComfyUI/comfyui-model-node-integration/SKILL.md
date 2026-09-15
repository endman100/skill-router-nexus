---
name: comfyui-model-node-integration
description: Integrate upstream image, audio, video, 3D, language, or multimodal models as native ComfyUI custom-node packs. Use for node boundaries, runtime adaptation, quality parity, example workflows, and distribution; not for workflow-only assembly.
---

# Integrate an upstream model into ComfyUI

Build the smallest native node surface that preserves upstream behavior and quality.

## Core rules

- Verify the target ComfyUI API, upstream revision, weights, supported capabilities, and an executable baseline from primary sources.
- License review and compliance are outside the agent's scope and are handled manually by the user. Do not research, infer, validate, or change licensing; preserve user-supplied license files and metadata verbatim. This exclusion also applies when using other packaging or research skills.
- Except for the versioned `comfy_api` namespace and immutable upstream or model revisions needed for reproducibility, target and test the newest released dependency versions. Avoid stale pins and unnecessary upper bounds. In `pyproject.toml`, use minimum-only `>=` constraints wherever possible. Actively remove the need for `<` or `!=` by updating the adapter or upstream compatibility fork; retain either constraint only when safe compatibility cannot be achieved, the failure is reproduced, and the reason is documented.
- Treat the installed ComfyUI runtime as the dependency authority. If an official upstream inference package or SDK conflicts with current ComfyUI dependencies and a narrow adapter cannot resolve it, fork only that upstream package and make the smallest compatibility update needed for current packages. Never fork or modify ComfyUI to accommodate the upstream package. Preserve model behavior and verify parity against the official implementation.
- Prefer native ComfyUI types and existing loaders, conditioning, samplers, schedules, codecs, preview, and save nodes. Add a custom node only for model-specific work.
- Reuse ComfyUI's established input names, meanings, defaults, ranges, widgets, and socket types whenever the upstream parameter is equivalent. Do not add aliases or rename a different concept merely to look native.
- Keep released node IDs, input IDs, output types, and output order stable. Change labels or add search aliases for presentation without silently breaking saved workflows.
- For diffusion or flow models, use the native `MODEL`, `CONDITIONING`, `LATENT`, `GUIDER`, `SAMPLER`, and `SIGMAS` graph wherever the update equations and tensor contracts match. Customize only the incompatible part.
- Add custom sampler or schedule provider nodes when the upstream method cannot be reproduced by core providers. Prefer native `SAMPLER` or `SIGMAS` outputs so they remain composable with ComfyUI's sampling executor.
- Keep loading lazy and use ComfyUI model paths, dtype/device policy, memory management, caching, unloading, progress, and cancellation.
- Fingerprint external models, configuration, dtype, and every other observable non-socket input deterministically. Distinguish ComfyUI data lists from tensor batches, and make lazy branches load only the resources they actually consume.
- Preserve the upstream algorithm. A compatible socket does not justify changing sampling math, conditioning, tensor layout, or decode behavior.
- Do not advertise editing, reference, inpainting, control, or conversion unless the upstream model supplies that conditioning path.
- Declare dependencies at install time; never use `eval`, `exec`, obfuscation, or runtime package installation. When programmatic access is available, implement first-use automatic weight download from an explicit model-loader execution, limited to a fixed revision and file manifest; verify available checksums, write through a temporary target, and publish files atomically. Cancellation or failure must not leave a valid-looking partial artifact.
- Resolve models through ComfyUI `folder_paths`, including paths configured by `extra_model_paths.yaml`; do not hardcode a single model directory or build a separate path system. Revalidate every path-like value at the actual read or write boundary instead of trusting a combo widget.
- Prefer schema descriptions, English input tooltips, labels, and node help over custom JavaScript. Add frontend code only when the native schema cannot express the required interaction; then test the newest frontend and declare a minimum `comfyui-frontend-package` version when needed.
- Ship multiple ready-to-run workflows covering the recommended path and other genuinely supported, tested modes or graph compositions. Do not count trivial parameter-only copies or unsupported features.
- Do not add GitHub Actions or other hosted CI workflows for automated custom-node testing. Run required tests locally or manually and record the commands, environment, and results. Add publishing automation only when the user explicitly requests it.

## Checklist

### Audit

- [ ] Record the target ComfyUI/API version and inspect the installed environment.
- [ ] Inventory dependency versions and test the newest releases. Optimize adapters or upstream compatibility forks until `pyproject.toml` can use minimum-only `>=` constraints; justify any unavoidable pin, `<`, or `!=` with a reproduced failure.
- [ ] Pin the upstream code and model revisions and confirm required hardware.
- [ ] If an official upstream inference package or SDK conflicts with current ComfyUI, first try a narrow adapter; otherwise fork only that upstream package, never ComfyUI, and test its changed paths against upstream.
- [ ] Run one official baseline and document supported versus unsupported capabilities.
- [ ] Read [upstream-audit.md](references/upstream-audit.md).

### Design and implement

- [ ] Map every capability to a core node, adapter, required custom node, or unsupported item.
- [ ] Use native public types at graph boundaries; keep model-private state custom.
- [ ] Check current core node schemas before adding an input; reuse the canonical parameter contract when its semantics match, otherwise document the smallest model-specific parameter.
- [ ] Keep node IDs, input IDs, output types, and output order stable; use display names and search aliases for non-breaking presentation changes.
- [ ] For diffusion or flow, compare prediction, guidance, time/sigma, noise, solver, and RNG contracts and reuse the current ComfyUI sampling chain wherever equivalent.
- [ ] If the sampler or schedule differs, implement the smallest custom provider node with native `SAMPLER` or `SIGMAS` output and verify it against the upstream update rule.
- [ ] Confirm whether native sampler, schedule, encoder, decoder, preview, and save contracts are mathematically compatible.
- [ ] Implement deterministic cache fingerprints for external models, configuration, dtype, and other observable state; verify cache hits and invalidation after each relevant change.
- [ ] Distinguish ComfyUI data lists from tensor batches and test empty optional inputs, one item, multiple items, and supported mixed shapes or sizes.
- [ ] Implement lazy load, dtype/device selection, unloading, progress, and cancellation; verify unselected lazy branches do not load their models or retain VRAM.
- [ ] Register and resolve the model category through `folder_paths`; test both the default directory and an `extra_model_paths.yaml` location.
- [ ] When technically possible and access is available, implement and test user-triggered first-use automatic weight download from a fixed revision and manifest, with checksum or metadata validation, temporary files, atomic publication, cancellation cleanup, cache hit, offline, gated, interrupted, and corrupt-artifact cases; otherwise document the exact manual placement and access requirement.
- [ ] Revalidate model and output paths at the read or write boundary, including combo values and `extra_model_paths.yaml` locations.
- [ ] Confirm imports and execution contain no `eval`, `exec`, code obfuscation, or runtime pip/conda/subprocess installer.
- [ ] Add short English descriptions and tooltips for non-obvious nodes and inputs; use frontend JavaScript only for interactions the native schema cannot provide.
- [ ] Read [node-surface.md](references/node-surface.md) and, when loading models or weights, [runtime-integration.md](references/runtime-integration.md).

### Verify and release

- [ ] Test registration and each deterministic intermediate boundary before end-to-end generation.
- [ ] Run matched official and ComfyUI cases with the same revisions, weights, inputs, seed, dtype, device, and generation settings.
- [ ] Compare intermediate and final outputs with metrics and acceptance thresholds defined before execution; pass only when every measured difference is within its threshold.
- [ ] Test claimed dtype, device, memory, unload, cancellation, and failure behavior.
- [ ] Test against the newest released dependencies and frontend; declare tested minimum versions with `>=` and eliminate `<` or `!=` through compatibility work wherever safely possible.
- [ ] Provide at least two ready-to-run workflows: a recommended minimal graph plus genuinely distinct supported modes or useful compositions, with labeled inputs and terminal outputs.
- [ ] Validate and queue every shipped workflow against the target schemas and confirm its terminal output; do not use trivial parameter-only duplicates to satisfy the count.
- [ ] Verify dependency, weight, code, and asset provenance; test the documented installation path.
- [ ] Install the built artifact in a clean environment and test install, update, removal, backend registration, and any declared frontend compatibility without modifying ComfyUI core.
- [ ] Keep automated custom-node tests out of GitHub Actions and other hosted CI; retain reproducible local test commands and captured results instead.
- [ ] Write the repository README using [readme-template.md](references/readme-template.md), filling every required section with verified project-specific information.
- [ ] Read [validation-and-release.md](references/validation-and-release.md) before claiming parity or Manager/Registry compatibility.

## Definition of done

Do not declare the node pack complete until every applicable item has direct evidence:

- [ ] A capability matrix links the authoritative upstream repository and identifies supported, composable, external, and intentionally unsupported features.
- [ ] A final node map lists every custom node, its stable schema, and the native ComfyUI nodes and types it composes with.
- [ ] The built package installs in a clean environment with the newest tested dependencies, registers without errors, and does not modify ComfyUI core.
- [ ] Every shipped workflow loads from `example_workflows`, queues successfully, and produces its documented terminal output.
- [ ] Runtime evidence covers model discovery, `extra_model_paths.yaml`, automatic download or manual fallback, lazy branches, fingerprints, lists versus batches, supported dtype/device paths, memory release, cancellation, and actionable failures.
- [ ] A reproducible upstream-versus-ComfyUI report records revisions, weights, inputs, seeds, settings, hardware, metrics, thresholds, hashes or artifacts, and shows every required comparison within its predefined tolerance.
- [ ] The README follows [readme-template.md](references/readme-template.md) and covers the original repository, project goal and features, wrapping method, installation and use, nodes, workflows, and reproducible official-versus-ComfyUI results.
- [ ] Required tests were run locally or manually with recorded evidence; the repository contains no GitHub Actions or other hosted CI workflow for automated custom-node testing.
- [ ] The release artifact, installation instructions, and any claimed Registry or Manager status are tested directly rather than inferred from source-tree execution or upload success.

Use `comfyui-research` for volatile APIs, `comfyui-inventory` for an installed target, `comfyui-workflow-skill` for examples, and `comfyui-node-packaging` for release. Publishing, pushing, forking, large downloads, and auxiliary models require explicit scope or authorization.
