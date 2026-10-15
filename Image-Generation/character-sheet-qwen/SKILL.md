---
name: character-sheet-qwen
description: Create character sheets using local ComfyUI Qwen Image 2.1 only. Use for Qwen turnarounds, expressions, a full-sheet-first generation with targeted repairs, or the archived split-asset composition variant.
---

# Character Sheet with Qwen Image 2.1

Generate every new character pixel with local ComfyUI Qwen Image 2.1. Use Python/Pillow for crops, copies, labels, and deterministic composition. Require Python 3.10+ and Pillow. Keep the original character-sheet skill unchanged.

## Select the requested workflow

Default to the user-retained full-sheet-first direction: follow [sheet-first.md](references/sheet-first.md) and use `scripts/qwen_sheet.py`. Generate a whole sheet directly from originals before any asset extraction or repair. Do not run the anchor/split-asset steps below for that mode. Keep its raw first pass and repair candidates distinct. Use the split-asset variant below only when explicitly requested; its frozen v1 release remains unchanged.

The retained quality version includes [full-sheet.workflow.json](assets/sheet-first/full-sheet.workflow.json), its API graph, a blank layout guide, the tested checkpoint configuration and exact case prompts under `references/sheet-first-retained/`. Replace `reference-original.png` with the user's image and copy the bundled `character-sheet-qwen-layout-guide.png` to ComfyUI input before using the UI graph. Adapt the angel-specific prompt to new characters; never silently impose its hairstyle or clothing. Read [quality checks](references/sheet-first-quality.md). The user's acceptance on 2026-10-15 retains this version for reuse; it does not establish universal likeness or reliability.

## Prepare

1. Inventory and inspect every original reference for this case. Keep stable original order and use originals as the identity authority; generated guides support continuity only. Resolve outfit/hair differences by user choice or a disclosed consistent assumption. If every reference hides the face, request a visible face for likeness-critical portraits and preserve useful partial work.
2. Read [backend.json](references/backend.json), [backend.md](references/backend.md), and [prompts.json](references/prompts.json). Inspect system_stats, object_info, and queue counts on the selected instance (default http://127.0.0.1:1120). Confirm configured models and node inputs exist. No substitution, LoRA, download, or server restart is implicit.
3. Reuse a suitable neutral frontal original as identity anchor with crop/scale only. Otherwise generate the anchor with all originals. Compare directly with originals before acceptance. Save identity-anchor.png and copy it byte-for-byte to expression-3.png for NORMAL. Never regenerate NORMAL.

For a manually editable starting graph, open [front.workflow.json](assets/front.workflow.json) in ComfyUI and select the original in LoadImage before queueing. [front.api.json](assets/front.api.json) is its API counterpart; its placeholder filename must be replaced. Prefer the client below for complete multi-reference logs and repeated asset generation.

## Generate and review

Run scripts/qwen_asset.py for one candidate at a time. Without --run it writes API graph, ordered inventory, request/provenance and performs live schema validation without upload or queue submission. Use absolute script paths when outside this skill.

```powershell
python scripts/qwen_asset.py --references <original1.png> <original2.png> --asset front --guide <accepted-anchor.png> --output <case-dir>/front.png
python scripts/qwen_asset.py --references <original1.png> <original2.png> --asset front --guide <accepted-anchor.png> --output <case-dir>/front.png --run
```

| Asset | Output filename | Required guide | Visual acceptance |
|---|---|---|---|
| anchor | identity-anchor.png | none | Same identity/apparent age, neutral frontal face, tight crop |
| front | front.png | accepted anchor when available | Whole body/soles; reference outfit and proportions |
| profile | profile.png | accepted front | Exact left profile; same outfit/proportions |
| back | back.png | accepted front | Exact rear view; consistent hidden construction |
| hands | detail-hands.png | accepted front | Both hands and distinctive design features |
| feet | detail-feet.png | accepted front | Exactly two feet/shoes, one left/one right, both straight front |
| outfit | detail-outfit.png | accepted front | Readable defining garment/accessory construction |
| happy | expression-1.png | accepted anchor | Strong open-mouth joy; image-left eye closed, image-right open |
| angry | expression-2.png | accepted anchor | Strong closed-mouth angry frown; image-right eye closed, image-left open |

Accept anchor before front/expressions and front before profile/back/details. Inspect each candidate visually before acceptance; successful inference is not approval. Prepare independent accepted-front tasks together when useful; let ComfyUI serialize GPU execution and retain other users' jobs.

Start with `--width 768 --height 1344` for body views and 1024×1024 for portraits/details; adjust only after reviewing framing and source detail. The tested base-model configuration and case-specific rear-view alternative are recorded in backend.md. Neither configuration guarantees a first-pass result.

Attach ALL originals in stable order, followed by the guide or actual edit target, on EVERY call including retries. The client uses actual image slots and checks live capacity (up to 16). Stop before upload if all required inputs do not fit; never drop originals or substitute a collage. Optional guides can be omitted to fit; originals and required targets cannot. Logs retain exact ordered paths, hashes, server input names, prompts, seed, graph, model config, prompt ID and history. This proves submission, not equal attention or likeness.

If a detail request retains an unwanted full body, crop the requested feature from the inspected accepted front and append it using a second `--guide <crop.png>` flag. Keep the original and full front attached; identify their indices and the crop's role explicitly in the instruction file. Use cropping/uniform scaling only, and retain crop provenance. The crop guides framing, not a new design or replacement for originals.

Keep rendering, clothing, apparent age, proportions and asymmetry from references. Use referential identity instructions; do not invent facial anatomy, numerical age or body measurements. --outfit-reference K selects clothing/hair exclusively from original K. Keep white backgrounds and natural subject shading; preserve garment lettering/accessories. Add no labels, rulers, borders or floor shadows. Headshots span topmost hair/ears to chin/upper neck, face/hair occupying 80–90%, at most a narrow neckline edge. Reject chest/torso/upper arms or bust framing. A more important weapon/tail/wing detail can replace a default detail through an explicit instruction file.

For failed assets, read [recovery.md](references/recovery.md). Retain rejected versions and make at most two targeted quality retries per asset with all originals. Use --asset repair --guide <failed.png> --instruction-file <one-change.txt> and a NEW output filename. Recheck dependent assets when an accepted anchor/front changes. --resume with the same output/log monitors a recorded job after timeout; never auto-resubmit an uncertain job.

When a correction succeeds locally but degrades unrelated pixels, use `scripts/composite_region.py <clean-base.png> <corrected.png> <new-output.png> --box LEFT TOP RIGHT BOTTOM --feather 3`. Inspect both equal-sized inputs first. Include the union of the old and new feature silhouettes in the rectangle, with its boundary in unchanged areas. The script only composites already generated Qwen pixels; it saves the feathered mask and source hashes. Inspect seams, leftover old features, and anatomy afterward. Keep NORMAL unchanged. See [recovery.md](references/recovery.md) for the tested case.

## Compose and verify

Copy [config.example.json](references/config.example.json) to the case directory and set filenames for accepted assets. Reuse the bundled compositor copied from character-sheet.

```powershell
python scripts/compose_turnaround_sheet.py <case-dir> <case-dir>/character-sheet.png --config <case-dir>/config.json
python scripts/verify_turnaround_sheet.py <case-dir>/character-sheet.png <case-dir>/character-sheet.manifest.json
```

Use the unmeasured 5×3 grid: top row hands/feet/outfit/happy/angry; lower two rows front/profile/back plus unchanged NORMAL spanning the right two columns. Default height 1876 px/minimum column width 575 px; expand equally for wide figures. Align tops and soles without stretching. Ruler null/body_data empty. This variant supports unmeasured output only; route explicit metric requests separately.

Inspect final identity, eye states, emotions, readable details, outfit/proportions, background and clipping. Geometry tests do not certify visual accuracy. Run bundled tests with python -B -m unittest discover -s scripts -p "test_*.py" -v.

If broad near-white noise causes oversized source bounds, inspect the asset and save a separate tight content crop with generous edge margins. Retain the uncropped original and its hashes; record crop boxes in case provenance and point config.json to the new crop files. Preserve aspect ratio and every character feature. Recompose and reverify after crop changes; do not alter earlier input logs or replace files used by earlier calls.

Deliver PNG, adjacent manifest, nine accepted assets, anchor, config, each candidate's .request.json/.api.json/.inventory.json/.history.json when run, verification output, visual review, and rejected attempts. Disclose inferred back/hidden details. Distinguish schema validation, real inference, geometry and visual acceptance. Without supplied character references, deliver the skill/workflow and state that character-quality acceptance awaits a case.
