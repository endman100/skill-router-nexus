---
name: comfyui-node-lifecycle
description: Implement and debug the current ComfyUI custom-node execution lifecycle, including validation, caching, fingerprints, lazy inputs, list processing, progress, and intermediate output.
---

# ComfyUI node lifecycle

Reason about execution in this order:

1. Schema registration
2. Input connection and validation
3. Cache/fingerprint comparison
4. Lazy-input resolution
5. Execution
6. Typed and UI output delivery

## Caching

ComfyUI caches graph execution. For data-dependent invalidation, implement the documented fingerprint hook for the API version in use. The fingerprint must be deterministic for equivalent observable inputs.

Use not_idempotent only when identical inputs may legitimately produce different results. It prevents some reuse between equivalent nodes but does not promise that every cache layer is disabled.

Do not return time, random values or mutable global state from a node advertised as idempotent.

## Validation

Use the documented validation hook only for checks that can run before execution. Return actionable messages tied to the invalid field. Keep resource existence checks race-safe because files can change after validation.

## Lazy inputs

Declare an input lazy and implement check_lazy_status. Return only the names still required for the current branch. Ensure execute handles every branch and never reads an unresolved lazy value.

## Lists and batches

ComfyUI data lists and tensor batches are different concepts. Set list-input/list-output behavior only when the node intentionally consumes or produces execution lists. Test zero, one and multiple items.

## Progress and intermediate output

Use ProgressBar or the current progress API for long operations. Set has_intermediate_output only when the node emits runtime state intended to persist or display before final completion. Verify frontend behavior on the target release.

## Sources

- https://docs.comfy.org/custom-nodes/v3_migration
- https://docs.comfy.org/custom-nodes/backend/lists
- https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_api/latest/_io.py

## Completion check

Run identical inputs twice, changed inputs once, each lazy branch, validation failure, cancellation, and one list/batch case. Confirm actual execution counts rather than inferring cache behavior from UI appearance.
