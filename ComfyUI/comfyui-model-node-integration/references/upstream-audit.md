# Upstream audit

Use this audit before deciding architecture or node count.

## Establish the baseline

Record:

- authoritative repository, model card, release or commit, and official inference entrypoint;
- model architecture and execution stages;
- required weight files, auxiliary encoders, decoders, tokenizers, and expected directory layout;
- supported operating systems, accelerators, compute dtypes, quantization formats, and memory guidance;
- upstream installation constraints and dependency pins; and
- at least one executable official example with its inputs, seed or configuration, outputs, and timing.

Use the actual official code as the parity oracle. A hosted demo, screenshot, marketing claim, or third-party wrapper is not an executable specification.

## Build a capability matrix

Classify every relevant feature as:

| Status | Meaning |
| --- | --- |
| Native upstream | Explicitly supported by official code and weights |
| Composable | Can be expressed with existing ComfyUI nodes without changing semantics |
| Adapter required | Upstream supports it, but a model-specific boundary is needed |
| External | Requires a different model, service, or preprocessing system |
| Unsupported | No upstream conditioning or execution path implements it |

Keep external features separate. Segmentation, transcription, pose extraction, source separation, voice conversion, depth estimation, or captioning may be useful around a model without being capabilities of that model. Add such dependencies only when the user requests the expanded pipeline.

## Identify equality boundaries

Map the official pipeline into stages and note observable values that can be compared independently:

- parsed requests, token IDs, plans, masks, embeddings, or conditioning;
- initial noise or other seeded state;
- scheduler values and sampler updates;
- intermediate or final latents or features; and
- decoded tensors, images, frames, audio samples, meshes, text, or metadata.

Separate deterministic parity from stochastic repeatability. When two branches independently consume randomness, either control the complete RNG state or share the last common stochastic output before comparing downstream behavior.

## Decide whether to fork upstream

Fork only when a narrow compatibility change cannot live cleanly at the node adapter boundary. Typical reasons include incompatible dependency pins, hard-coded device behavior, an attention or backend call that must route through ComfyUI, or package metadata that would replace ComfyUI's runtime stack.

Keep a fork reviewable:

- start from a named upstream version or commit;
- make the smallest behavioral changes;
- preserve model math, tokenization, sampling, decoding, and state-dict keys unless the task explicitly changes them;
- add parity tests around every changed execution path; and
- pin consumers to an immutable commit rather than a moving branch.
