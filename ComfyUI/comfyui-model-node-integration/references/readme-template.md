# Custom-node README template

Write the repository `README.md` for a first-time user, not for the implementer. The first screen should answer what the pack does, how to install it, and which workflow to open. Keep schemas, environment dumps, complete metrics, hashes, and reproduction logs in focused documents such as `docs/MODEL_SETUP.md` and `docs/VALIDATION.md`.

Use the following order unless the modality needs a small adjustment. Keep paragraphs short, tables to two or three columns, and terminology consistent with labels visible in ComfyUI. Prefer fewer than about 1,000 prose words for a pack of ordinary complexity; move excess detail to focused docs. Remove instructional placeholders from the finished README. Do not add Known Limitations, Credits, or license sections; the user handles that content separately.

## Title and summary

    # <Project name>

    <One sentence naming the upstream model and the result users can create in ComfyUI.>

Follow with a compact link row such as Install, Quick start, Workflows, Original project, and Model setup. Avoid opening with API versions, socket inventories, or implementation history.

## What it does

Use four to six plain-language bullets covering:

- the primary user result;
- meaningful supported modes or editing paths;
- important native ComfyUI composition;
- first-use automatic download and local or `extra_model_paths.yaml` support; and
- tested dtype, device, or memory options users may need.

Add one short scope sentence for commonly confused external or unsupported capabilities. Do not mix third-party pipeline features into the model's own capability list.

## Reviewable results

When the modality produces inspectable media, embed a few representative matched cases. Label **Official pipeline** and **ComfyUI node** unambiguously and place them side by side when practical.

- Use normal upstream defaults or recommended quality settings and natural completion, not short regression caps.
- Show only the paired outputs and a concise case label on the front page.
- Put difference artifacts, metric tables, hashes, environment details, and reproduction commands in the linked validation report.
- Collapse multiple cases so the page remains scannable.
- Use a GitHub-renderable, browser-playable format. Verify the published page and every media URL in the target browser; do not assume raw HTML attributes or compact audio controls will survive GitHub rendering.
- If a fixed video player would otherwise be blank, add a lightweight useful visual such as a waveform without altering the underlying audio.

Skip this section only when the output cannot be meaningfully embedded; provide clearly named artifact links instead.

## Install

State the minimum tested ComfyUI and Python versions, approximate model storage, and recommended hardware in one short paragraph. Then provide:

1. the verified Manager or Registry identifier, if directly installable;
2. a manual clone and dependency command as fallback;
3. the required restart; and
4. what the first Model Loader execution downloads.

Link detailed local paths, offline behavior, gated access, dtype, memory, and `extra_model_paths.yaml` configuration to model setup documentation. Never claim a Registry or Manager state that was inferred only from upload success.

## Quick start

Give the shortest successful path in about four numbered steps:

1. open **Workflow Templates** and select the recommended template;
2. identify the two or three nodes or fields most users should edit;
3. keep tested defaults for the first run; and
4. Queue, preview, or save through the native terminal node.

Mention only one or two controls that a beginner may actually need for duration, size, or memory. Prefer “keep the workflow defaults” over repeating sampler, schedule, or token values in the quick start. Do not explain the whole graph here.

## Example workflows

Link every shipped workflow file and give it a simple choice-oriented description:

| Workflow | Choose it when you want to… |
| --- | --- |
| [`<recommended>`](`<workflow path>`) | `<shortest supported path; mark Start here>` |
| [`<alternate>`](`<workflow path>`) | `<genuinely different supported mode or composition>` |

All listed workflows must appear in ComfyUI's Template Browser, load without missing nodes, queue successfully, and reach a native preview, save, or output node. Put prerequisites or detailed terminal paths in separate workflow documentation when they would make this table noisy.

## Nodes

Tell users which few custom nodes they normally edit and that the remaining plumbing is already connected in the templates. Then list each custom node once:

| Node | What it is for |
| --- | --- |
| `<node>` | `<one plain-language sentence>` |

Keep socket types, full input lists, cache contracts, and implementation details in node tooltips or technical documentation. Name the native ComfyUI nodes reused for sampling, preview, save, or other standard operations in one short sentence.

## Model-specific editable data

Include this section only when users encounter a plan, score, prompt object, mask, control structure, or another unfamiliar intermediate. Explain what it represents, which mode a beginner should choose, how to edit it safely, and whether a readable output is only a preview or is also consumed downstream. Do not expose opaque tensors or derived tokens as fields users must edit.

## How the integration works

Use one compact paragraph to explain which official stages became model-specific nodes and which stages remain native ComfyUI nodes. Link a detailed node map or validation report rather than placing a large type-mapping table on the front page. Mention a compatibility fork only when one is actually used, linking its immutable base and narrow purpose.

## Verified against the official implementation

State the number and nature of tested cases, the comparison boundary, and the observed result in one short paragraph. Distinguish fast regression fixtures from representative normal-output cases. Link `docs/VALIDATION.md` for revisions, weights, settings, hardware, thresholds, per-case metrics, hashes, and reproduction commands.

Never claim exact equality unless measured deterministic outputs are exactly equal. Otherwise report the predefined tolerance and observed difference accurately.

## Troubleshooting

Include three to five short, actionable items for failures users can resolve, such as memory pressure, incomplete downloads, offline mode, corrupt artifacts, or accidentally replacing a required custom sampler or schedule. Avoid repeating unsupported-feature marketing here.

## Project links

Use a short list linking the authoritative upstream repository, model card or weights, and compatibility fork when one is used. State that the repository is a ComfyUI integration. Put exact code, model, integration, and test revisions in the validation report; the front page needs only the fork's narrow compatibility purpose. Never describe ComfyUI as the fork target.

Across the README, advertise hardware, dtype, backend, and Manager support only when that path was actually executed. Put implemented-but-untested paths in technical documentation rather than presenting them as verified user recommendations.
