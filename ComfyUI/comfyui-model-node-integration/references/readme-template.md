# Custom-node README template

Use this structure for the repository `README.md`. Fill every section with concise, verified project-specific information. Remove instructional placeholders from the finished README. Do not add Known Limitations, Credits, or license sections; the user handles that content separately.

## Title and summary

    # <Project name>

    <One sentence describing the upstream model and what this ComfyUI node pack enables.>

State the primary modality, main capability, and the most important native ComfyUI integration in no more than one short paragraph.

## Original project

Link the authoritative upstream repository, model card or weights, and the exact release or commit used for the integration. State that this repository is a ComfyUI integration. If an upstream compatibility fork is used, link it and summarize its base revision and narrow compatibility purpose; never describe ComfyUI itself as the fork target.

## Project goals and features

Explain the integration goal, user-facing features, native ComfyUI types or nodes reused, lazy loading, supported dtype or device paths, automatic model download, and `extra_model_paths.yaml` support. Include a compact feature table when several capabilities need comparison. Do not claim a feature without upstream support and executed evidence.

## Integration approach

Describe how the official pipeline maps into ComfyUI. Prefer a compact table:

| Upstream stage | Custom node or adapter | Native ComfyUI node/type | Reason |
| --- | --- | --- | --- |
| `<stage>` | `<implementation>` | `<native contract>` | `<why this boundary exists>` |

Explain any custom sampler, schedule, conditioning, latent, codec, or upstream compatibility fork only to the depth needed to understand correctness and composability.

## Installation and model setup

Document the verified Manager or Registry installation identifier when available, manual installation, minimum ComfyUI and Python versions, newest tested runtime and dependencies, model locations, first-use automatic download behavior, manual fallback, gated access, and `extra_model_paths.yaml` setup. Do not include secrets or tokens in workflow files or command examples.

## How to use

Give the shortest successful path from loading the recommended template to obtaining the output. Identify the inputs most users should edit, the model or dtype selection, the Queue action, and the output location or preview. Include a labeled workflow image when it materially improves clarity.

## Nodes

List each custom node once:

| Node | Purpose | Main inputs | Outputs | Notes |
| --- | --- | --- | --- | --- |
| `<node>` | `<one sentence>` | `<inputs>` | `<outputs>` | `<important behavior>` |

Keep detailed parameter descriptions in node tooltips and help pages. Mention the native ComfyUI node that replaces a custom save, preview, encode, decode, sampler, or schedule node when applicable.

## Example workflows

List every shipped `example_workflows` template with its purpose, prerequisites, editable inputs, and expected terminal output:

| Workflow | Purpose | Required models | Edit these inputs | Expected output |
| --- | --- | --- | --- | --- |
| `<file>` | `<use case>` | `<models>` | `<inputs>` | `<output>` |

Explain how to load the workflows from ComfyUI's Template Browser. Include only workflows that have been opened, queued, and verified.

## Implementation results versus official results

Summarize the matched test method and link or embed reviewable artifacts. Record official and ComfyUI revisions, weights, inputs, seeds, settings, dtype, device, hardware, metric, predefined threshold, and result.

| Case | Comparison boundary | Metric | Threshold | Observed difference | Result | Artifacts |
| --- | --- | --- | --- | --- | --- | --- |
| `<case>` | `<tokens/latents/final output>` | `<metric>` | `<limit>` | `<value>` | `Pass/Fail` | `<links>` |

Use exact equality only when both paths share deterministic operations and inputs. Otherwise state the justified tolerance. Never replace measured results with an unsupported statement that outputs are identical.
