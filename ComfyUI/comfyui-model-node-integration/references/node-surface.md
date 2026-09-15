# Node surface design

Use this reference after the upstream capability matrix exists.

## Apply the boundary test

Create a custom node only when all of the following hold:

1. it performs a coherent operation users need to compose independently;
2. the operation is model-specific or cannot be represented faithfully by core nodes;
3. its inputs and outputs have stable contracts; and
4. exposing the boundary does not force users to manipulate undocumented internal state.

Remove nodes that only rename, pass through, save, preview, or wrap a core operation. Keep a one-shot convenience node only when the user experience justifies a second supported graph path and its behavior can stay consistent with the composable path.

## Prefer public native contracts

Select types from the installed public ComfyUI API. Common mappings include:

- diffusion or flow models to native model, conditioning, latent, sampler, and schedule contracts when mathematically compatible;
- pixels, masks, frames, waveforms, video, geometry, text, and structured metadata to the corresponding public media or data types;
- VAE or codec stages to core encode or decode nodes only when layout, scaling, sample rate, channels, tiling, and metadata contracts match; and
- editable domain state to a built-in structured type when possible, otherwise a documented custom type with an editor or adapter boundary.

Do not use a custom type merely to hide serializable data. Do not force an internal tensor into a generic string or JSON representation when precision, device, identity, or object behavior matters.

## Reuse parameter contracts

Inspect the current core node schemas before defining inputs. When an upstream parameter has the same behavior, reuse ComfyUI's canonical name, meaning, type, default, range, widget, and serialization contract. This commonly applies to concepts such as seed, steps, guidance, sampler, sigmas, denoise amount, conditioning, and latent input.

Do not create model-prefixed aliases for an equivalent core parameter. Conversely, do not reuse a familiar name when units, range, direction, scheduling, randomness, or side effects differ. Give genuinely model-specific inputs the smallest clear name and a short description of their semantics.

## Sampler and schedule compatibility

Determine compatibility from equations and tensor contracts, not model-family labels.

1. Write the upstream state update, time or sigma parameterization, prediction target, guidance rule, noise layout, and seeded RNG behavior.
2. Compare each part with core KSampler or custom-sampling contracts.
3. Reuse core sampler and schedule nodes if they can reproduce the update without hidden state or quality-changing conversions.
4. If only the update rule or schedule differs, expose the smallest custom sampler or schedule provider and keep the native sampling executor.
5. Use a separate execution node only when the model requires a non-representable loop, mutable state, autoregressive cache, streaming protocol, or multi-stage control flow.

Custom sampler and schedule provider nodes are valid integration boundaries when core providers cannot express the upstream method. Make them independently composable and return the public `SAMPLER` or `SIGMAS` contract whenever possible. Keep model loading, conditioning, latent creation, and decoding outside these providers unless the upstream equation genuinely requires that state.

Flow matching can often use ComfyUI's custom sampling graph, but that alone does not prove compatibility. The time parameterization, model prediction contract, guidance, solver, and noise ordering must also match.

When compatible, expose the current public `MODEL`, `CONDITIONING`, `LATENT`, `GUIDER`, `SAMPLER`, and `SIGMAS` contracts and retain ComfyUI's native sampling executor. If one contract differs, replace only that provider instead of duplicating the complete sampling pipeline.

## Modality-neutral graph design

Separate stages only when users can meaningfully branch, inspect, edit, reuse, or replace them. Examples include:

- request, plan, or conditioning preparation;
- model loading;
- encoding or tokenization;
- iterative generation or sampling;
- decoding or rendering; and
- model-specific postprocessing.

Use core preview and save nodes for terminal media when they accept the native output. Preserve batch dimensions, timing, sample rate, frame rate, coordinate systems, color ranges, channel layouts, and device or dtype contracts appropriate to the modality.

## UX contract

Give nodes, sockets, and non-obvious widgets short English descriptions. Use labels and placeholders that explain what users should enter, not internal variable names. Example workflows should demonstrate the recommended graph and one meaningful alternate path, without requiring disconnected outputs or unexplained fields.
