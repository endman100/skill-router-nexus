# Runtime integration

Use this reference for model loading, execution resources, artifact downloads, or an upstream compatibility package.

## Loading and paths

- Register the model category with ComfyUI `folder_paths`, then use its enumeration and resolution helpers for both default directories and paths loaded from `extra_model_paths.yaml`. Do not parse that YAML independently or maintain a parallel path registry.
- Revalidate path-like combo values at the load boundary; UI choices are not a security boundary.
- Support local paths only within intended model roots unless the interface explicitly and safely supports absolute paths.
- Keep construction cheap. Resolve and load large artifacts on the first downstream operation that needs them.
- Fingerprint local artifacts and relevant configuration so cache reuse changes when observable model state changes.

For remote model repositories, expose repository, revision, cache, and local-only controls only when they affect behavior. When programmatic access is available, a missing selected artifact must be downloaded automatically from an explicit model-loader execution. Pin the requested revision, limit the transfer to required artifacts, download through an incomplete or temporary target, validate available hashes or metadata, and publish the final files atomically into a registered model directory. Do not download during import, startup, background polling, or unrelated node execution.

Test an empty-cache download, cache hit, interrupted or corrupt download, offline mode, gated or authenticated access, and discovery from `extra_model_paths.yaml`. If automatic retrieval is technically unavailable or access fails, provide the exact repository, revision, filenames, and registered destination needed for manual installation.

## Device, dtype, and memory

Treat storage dtype, compute dtype, device placement, quantization, and offloading as correctness concerns.

- Reuse ComfyUI model-management, patcher, quantization, attention, and optimized-operation facilities where their contracts fit.
- Keep device and memory policy out of model math.
- Avoid unconditional casts, transfers, and CPU staging allocations.
- Do not claim FP8, BF16, FP16, quantized, CPU, CUDA, ROCm, MPS, XPU, DirectML, or NPU support without an executed path or authoritative support evidence.
- If one stage requires a different dtype from another, make the boundary explicit and test both stages.
- Scope large temporary caches to one execution. Release or offload models through ComfyUI ownership rather than custom global caches.

Test load, unload, reload, repeated execution, low-memory behavior, cancellation, and switching between model configurations. Measure peak memory when memory behavior is part of the claim.

## Dependencies

Declare only packages imported by the integration or its pinned runtime. Do not assume optional ML libraries ship with ComfyUI, and do not let dependency installation replace the target ComfyUI Torch stack unexpectedly.

Never call pip, conda, shell installers, or package-rewriting logic from node import or execution. Installation belongs in package metadata, requirements, or an explicit documented setup step outside ComfyUI execution.

When a compatibility fork is required:

1. keep the fork source reviewable;
2. pin the node pack to an immutable commit or immutable package version;
3. explain the compatibility delta;
4. test the fork against the target ComfyUI runtime; and
5. keep model weights separate from the compatibility package.

## Runtime boundary

Normalize upstream return conventions at the adapter. ComfyUI nodes should receive stable, documented shapes and types rather than handling upstream tuple, list, or dict variants throughout the graph.

Avoid patching a loaded model directly from node code. Use the model patcher or a dedicated integration-owned model class. Do not inspect the identity of an optimized backend implementation; depend on its documented callable contract and result.
