---
name: comfyui-troubleshooter
description: Diagnose current ComfyUI startup, custom-node, workflow, model, memory, API, frontend, and output-quality failures with evidence from logs, schemas, inventories, and minimal reproductions.
---

# Troubleshoot ComfyUI

Diagnose before changing files or installing packages.

## Evidence collection

Collect:

- exact error text and full relevant traceback
- ComfyUI commit/release and frontend version
- Python, PyTorch, accelerator, driver and device
- custom-node package versions
- workflow JSON format and failing node ID/class_type
- /object_info entry for the failing class
- model filename, category, source and hash when relevant
- reproduction steps and whether a clean core workflow works

Redact secrets and private paths before sharing logs.

## Failure branches

### Startup or import failure

Find the first relevant exception, identify the importing package, compare its declared dependencies to the environment, and test with that custom node disabled. Do not upgrade the entire environment as a first response.

### Prompt validation failure

Compare every reported class_type and input against /object_info. Distinguish UI workflow JSON from API prompt JSON. Fix the smallest mismatch and resubmit.

### Missing model

Confirm the loader's model category, extra_model_paths.yaml, exact filename and file integrity. Do not rename arbitrary models to satisfy a workflow.

### CUDA or memory failure

Record dimensions, batch size, frame count, dtype, attention mode and loaded models. Reduce one pressure source at a time. Clear the queue or unload models through supported controls before restarting the process.

### Frontend failure

Use an uncached reload, inspect browser console/network logs, check frontend compatibility and disable the suspected extension. Avoid prototype monkeypatch fixes.

### Wrong or poor output

First verify that the intended model, VAE, text encoders, scheduler, conditioning and seed were actually used. Compare with a minimal official workflow before changing prompt wording.

## Resolution standard

For every proposed fix, state:

- evidence linking it to the failure
- exact reversible change
- expected observation
- rollback
- verification command or workflow

Do not present community anecdotes as confirmed fixes. Link the original issue or release and note affected versions.

## Sources

- https://docs.comfy.org/troubleshooting/overview
- https://docs.comfy.org/development/comfyui-server/comms_routes
- https://github.com/Comfy-Org/ComfyUI/issues
