# Validation and release

Use this reference for completion claims, example workflows, packaging, or publication.

## Layered validation

Validate in increasing scope:

1. **Static package:** imports, compilation, technical metadata, dependency declarations, and absence of runtime installers.
2. **Registration:** extension loads, node IDs are unique and stable, schemas register, descriptions render, and frontend assets load when present.
3. **Contracts:** valid, invalid, empty, batched or list, dtype, device, serialization, and cache or fingerprint behavior at each node boundary.
4. **Resource lifecycle:** lazy load, download or offline branch, unload and reload, configuration switching, cancellation, and low-memory behavior.
5. **Stage parity:** compare deterministic intermediate boundaries with the official pipeline.
6. **End-to-end quality:** run representative use cases, edge cases, and each claimed mode on supported hardware.
7. **Workflow UX:** open saved UI workflows in the target frontend, inspect labels and tooltips, queue them, and confirm terminal outputs.

Use several cases when stochastic sampling, multiple modes, or dtype branches materially affect quality. Choose cases by coverage, not by an arbitrary fixed number. Record seeds, revisions, settings, hardware, timings, comparison boundaries, tolerances, and artifact hashes where useful.

For a stochastic or multimode generation pack, start with at least five matched cases spanning meaningful modes and add cases until the claimed surface is covered. A smaller deterministic integration may use fewer cases only with an explicit coverage rationale. Case count never substitutes for testing a distinct algorithm or conditioning path.

Use two evidence tiers when full generation is expensive:

- **Fast regression fixtures:** reduced tokens, steps, frames, resolution, or duration are acceptable for contract and deterministic parity checks, but label them clearly.
- **Representative outputs:** use upstream defaults or recommended production settings, allow natural end conditions, and cover each materially different claimed mode. These are the artifacts users should inspect in the README.

Do not use a short regression cap as evidence of normal output length or quality. When the upstream does not prescribe a fixed duration, record the stopping condition and naturally produced duration instead of inventing a recommendation.

Exact equality is appropriate only when both paths share the same deterministic inputs and operations. Otherwise use justified numeric tolerances plus modality-appropriate evaluation. Examples include pixel or latent errors, audio sample or spectral metrics, frame and timing alignment, geometry distances, token or logit comparisons, or task-level correctness.

For each parity case, hold the upstream and ComfyUI revisions, weights, inputs, seed, dtype, device, and generation settings constant unless that variable is the feature under test. Define the metric, comparison boundary, direction, and acceptance threshold before execution. A parity claim passes only when every required measurement is within its declared threshold; retain both outputs and the comparison report for review.

If stochastic stages cannot be replayed independently, compare both the complete seeded path and the deterministic suffix from the last common stochastic output. State which values were shared; do not imply that a downstream equality test alone proves upstream sampling parity.

Keep the README comparison simple: show a clearly labeled Official output beside the matched ComfyUI output. Put difference artifacts, full metric tables, environment dumps, hashes, and reproduction commands in the validation report unless the user explicitly requests them on the front page.

## Example workflows

Ship at least two ready-to-run workflows using public node schemas from the supported target version. One should be the recommended minimal graph; the others should demonstrate genuinely distinct supported modes or useful graph compositions. If the upstream exposes only one generation mode, use different real compositions such as a minimal path and an editable-intermediate path only when both are supported. Do not count copies that only change seed, dtype, or another parameter.

Include:

- the recommended minimal graph;
- alternate dtype, device, or advanced paths only when tested and useful;
- required model and custom-node dependencies;
- editable inputs with understandable defaults; and
- a core preview, save, or output path where available.

Validate every UI workflow JSON against the current schema and every node, input, and output against the target `/object_info`. Open and queue each workflow in the supported frontend, then confirm its documented terminal output. Opening a workflow without missing-node warnings is not proof that it executes.

Register examples in the package's supported template location and verify they appear in ComfyUI's Template Browser under an understandable package name. Inspect the actual canvas: user-editable fields must be identifiable without reading source code, notes must explain only non-obvious parameter groups, and parameterless plumbing nodes should not be surrounded by redundant guidance.

## README media

When final outputs are media, retain matched Official and ComfyUI artifacts in a browser-playable format and label the pair unambiguously. Use side-by-side presentation when the rendered platform supports it. For long collections, collapse individual cases so the README remains scannable.

Test the rendered GitHub page in a target browser instead of assuming raw Markdown or HTML will behave identically. Verify that every media URL returns successfully and that controls can play the content; published links must not reference local-only files or unpushed assets. If the host forces a fixed video player area, include a lightweight informative visual such as a waveform rather than leaving a large blank surface. Keep source-quality artifacts and numeric metrics in the validation report; the README pair exists for quick human review.

Keep showcase assets within host limits. Exclude large documentation-only evidence from the Comfy Registry artifact with `.comfyignore` when it is not required at runtime, while keeping the GitHub URLs stable and reviewable.

## Package and Registry

Use `comfyui-node-packaging` for current metadata and Registry mechanics. Before publishing:

- choose an available, stable Registry node ID; remember that it is immutable after first publication;
- use semantic versions and a clear display name;
- exclude tests and development-only assets with `.comfyignore` while retaining examples and required runtime files;
- run the current Comfy CLI package validation and security checks;
- inspect the exact archive built from tracked files;
- install that archive in a clean supported ComfyUI environment.

Do not add GitHub Actions or other hosted CI workflows for automated custom-node testing. Run validation locally or manually and retain reproducible commands and results. When automated Registry publishing is explicitly requested, keep it release- or tag-scoped, separate it from test automation, use the official publish action and a repository secret, and pin actions when repository policy requires it.

After publication, verify the Registry page, version status, Manager cache entry, documented install ID, dependency installation, node registration, and a smoke workflow from the installed package. Distinguish a successful upload from Registry extraction or indexing and from actual Manager installation.

## Delivery

Report:

- supported and intentionally unsupported features;
- custom nodes added and which core nodes they compose with;
- tested ComfyUI, upstream, and runtime revisions and hardware;
- exact validation results and artifact locations;
- install and model-download behavior;
- tested platform boundaries; and
- Registry or Manager status only when directly verified.
