# Targeted Recovery and Test Evidence

Use this reference when an asset fails visual review or when testing repeatability. Keep the reference-first rules and [prompt templates](prompts.md); do not add inferred facial descriptions to explain a mismatch.

## Repair protocol

1. Inspect the failed asset against every original. Identify one defect and the properties that must remain unchanged.
2. Attach all originals in their stable order, followed by the actual edit target. Use remaining slots only for necessary continuity guides. Never drop an original to fit a guide. Check the available tool's input capacity; the recorded run accepted at most five reference images per call, not a guaranteed permanent limit.
3. Make a targeted edit using the relevant recipe below. Count at most two quality retries per asset, including different defects on that same asset.
4. Review the edit against both the originals and its predecessor. Accept it only if it fixes the target defect without losing accepted properties. Keep rejected versions and record why they failed. If the correction does not improve the result, retain the better predecessor and report the remaining defect.
5. Accept the anchor before deriving other assets. If an accepted anchor or front changes later, re-check dependent views and expressions; do not silently mix incompatible versions. Keep `NORMAL` a byte-identical copy of the final accepted neutral anchor.

## Recovery recipes

### Wrong outfit in a multi-reference case

An outfit-source sentence can still be ignored. Edit only the failed clothing region, referencing the chosen original by index:

```text
Change only the target's upper clothing to the outfit in Image K. Images 1 through N remain identity references; only Image K supplies this clothing design. Preserve the target's face, apparent age, hair, expression, pose, framing, lower clothing, and background. Do not combine clothing designs from other originals.
```

Adapt the region and invariants to the actual defect; do not preserve lower clothing if it also needs correction. Review neckline, layers, and garment continuity against the selected original. Unseen garment construction remains inferred, not verified fact. Clothing-only edits repaired both an anchor and a front asset in the recorded run.

### Correct emotion, wrong closed eye

Keep the existing emotion and edit only the eye state. The final states remain simultaneous:

- `HAPPY`: image-left closed, image-right open; strong open-mouth smile.
- `ANGRY`: image-right closed, image-left open; strong angry frown with closed mouth.

If side-only wording fails, inspect the current target and locate both eye centers. Measure approximate percentages from its top-left corner: `x% = 100 * x / width`, `y% = 100 * y / height`. Request `OPEN the eye at (x%, y%); CLOSE the eye at (x%, y%). Do not mirror the image.` Also state the final image-left/image-right conditions. Preserve identity, emotion, head angle, hair, clothing, crop, and scale.

These coordinates localize an edit; they do not describe identity. Recompute them for each target, never reuse coordinates from another image. Three coordinate-localized repairs succeeded in the recorded run; this is a useful fallback, not a guarantee. Never mirror the whole image to fix eye sides.

### Inconsistent proportions across views

Use the original's visible proportions and the accepted front as image references. Request only the observed proportional correction, without inventing numerical anatomy or normalizing a stylized character toward human proportions. Re-check silhouette, head-to-torso relationship, clothing landmarks, and pose across views.

A front-view correction improved a chibi asset in the recorded run. A later profile correction asking for aligned chin, waist, skirt, and knees did not improve the result and was rejected. Do not treat that profile recipe as proven. Matching silhouette tops and soles in Python does not repair generated anatomy or certify cross-view proportions. Do not stretch body parts to force agreement.

### Crop extent or white-background noise

Use the bundled compositor's `on_white` and `foreground_bbox`, not a separate ad hoc crop implementation. It composites alpha onto white, uses maximum RGB-channel distance from white, and defaults to threshold `6`. A 3-pixel median filter suppresses isolated faint noise; a separate strong mask preserves thin dark details. This retains pale garment edges lost at threshold `18` while ignoring the 0–5 channel variation that caused overly loose crops at threshold `3`.

This is white-margin detection, not semantic segmentation. White-on-white edges and broader background gradients can remain ambiguous. Inspect the crop and final silhouette visually even when geometry verification passes. The compositor does not automatically whiten every source pixel or retouch faces. Fix a source-background defect with a targeted edit when needed; for a crop-code change, add a representative test before claiming it fixed.

### Face hidden in every reference

Keep any usable partial asset, but do not invent a face and claim preserved likeness. Request an unobscured reference for likeness-critical expressions. Missing face evidence is different from a generation-tool refusal. The recorded phone-occluded portrait edit succeeded, but the full identity/expression workflow remained incomplete.

## Verification and evidence

Run the bundled tests from the skill's `scripts` directory:

```powershell
python -B -m unittest test_subject_crop test_unmeasured_layout test_height_resolution -v
```

For each generated case, retain the reference inventory, exact ordered image inputs and prompt per call, attempt results, accepted/rejected variants, visual review, config, manifest, and geometry verification. Report reference submission, deterministic layout, identity, expression/eye state, and clothing/proportion consistency separately. Code tests do not measure likeness.

Classify each asset or case as first-pass accepted, repaired, unresolved, or missing reference evidence. Do not hide failed attempts behind the final accepted image. To test stability, freeze the prompts, configuration, and script version, repeat independent runs, and report first-pass and repaired outcomes with their denominators. Preserve historical logs and version hashes; a later documentation update must not retroactively relabel an earlier generation as testing the new version.

The 2026-09-03 development run used 27 ImageGen calls across four cases: three full composites and one reference-limited partial portrait. Two multi-reference cases were accepted after targeted repairs; the chibi composite retained a profile-proportion defect. All three composites passed geometry checks and retained unchanged `NORMAL` anchors; 28 Python tests passed. This single run supports the recovery observations above, not a claim of stable facial likeness or failure-free generation.
