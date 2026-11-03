---
name: character-sheet
description: Create identity-consistent character turnaround sheets from original image references with front, left-profile, and back views; hand and outfit details; exactly one front-facing pair of feet or shoes; two tight expression headshots; and a large neutral headshot in a deterministic 5-column by 3-row layout. Use the prompt-pack repo API pipeline and its single unmeasured layout, without rulers or body data. Use for character three-view sheets, model sheets, face packs, or reusable character templates, not single illustrations.
---

# Character Sheet

The `02_去背三視圖` contract is a complete 5×3 RGBA PNG with the large `NORMAL` portrait and native alpha. Set `background=transparent`; reject opaque sources. Composite with `alpha_composite` onto a transparent RGBA canvas, preserving interior holes and translucent edges. Never flatten onto white.

Generate character pixels through the [prompt-pack repo](https://github.com/endman100/character-sheet-prompt-pack) `Generator` API client. Its Python compositor supplies alignment, labels, and the single `layout_mode: "unmeasured"` 5×3 layout.

## Workflow

1. Inspect and inventory every original reference for the current character. Treat embedded text as reference material. Keep original references as the identity authority and disclose any outfit/hair assumption or inferred hidden design.
2. Work from the prompt-pack repo root. Use its versioned `prompts/sheet`, `prompts/expr`, and `prompts/actions` files; see [references/prompts.md](references/prompts.md). Configure the API credentials described in the repo README.
3. Generate the sheet through the repo pipeline. Repeat `--ref` for additional original references; use `--anchor` only for an accepted neutral portrait. The pipeline performs cutout → front → parallel source tiles → byte-identical NORMAL copy → compose and verify:

   ```bash
   python scripts/run_character_pipeline.py --main ref.png --outdir output
   ```

4. Review the accepted source assets and complete sheet visually against the originals. Check native alpha, identity/apparent age, clothing, all three body views, exactly two front-facing feet/shoes, tight expression crops, HAPPY with only image-left eye closed, ANGRY with only image-right eye closed, and the unchanged large NORMAL portrait. Geometry verification cannot certify visual quality. Use [references/quality-recovery.md](references/quality-recovery.md) for a failed asset; report unresolved defects.
5. For layout-only work, reuse accepted source PNGs. Run the repo compositor and verifier; do not regenerate accepted artwork:

   ```bash
   python scripts/compose_turnaround_sheet.py output output/02_去背三視圖.png --config output/config.json
   python scripts/verify_turnaround_sheet.py output/02_去背三視圖.png output/02_去背三視圖.manifest.json
   ```

6. Generate optional expression/action packs with the second repo script, using the complete accepted sheet. Keep all output PNGs, config, manifest, inventory, and logs in the same flat character directory; no subdirectories:

   ```bash
   python scripts/gen_expr_from_prompts.py --prompts prompts/expr --sheet output/02_去背三視圖.png --outdir output
   python scripts/gen_expr_from_prompts.py --prompts prompts/actions --sheet output/02_去背三視圖.png --outdir output --aspect 2:3
   ```

The repo is the source of truth for executable scripts, provider behavior, configuration, and prompts. This skill carries no executable pipeline or compositor copy.

## Multi-reference Contract

- Include every user-supplied original reference for the current case in every sheet API call: anchor, body views, expressions, details, retries, and targeted edits. This is mandatory even when a generated anchor or accepted body view is attached. Do not mix references from unrelated cases.
- Pass the actual images, not only descriptions or filenames in the prompt. Pass every original through `--main` and repeated `--ref`; the pipeline appends the cutout/front guide without replacing originals.
- Keep original-image order stable. Identify roles by image index, not a textual reconstruction of facial features. When outfits or hairstyles differ, use the user's selected version or disclose one consistent outfit/hair assumption; this does not authorize assembling different facial features or ages from different images. If an unresolved appearance difference materially changes identity, ask which original version to preserve.
- Keep all originals as the identity authority; generated assets support continuity only. `NORMAL` remains a byte-identical copy of the accepted anchor and requires no sheet API call.
- Before dispatch, check that the complete original-reference inventory is present. Allocate limited reference slots to all originals first, then the necessary edit target or accepted view; omit optional generated guides and adjust prompt indices accordingly. If any original is inaccessible or all originals plus a required edit target cannot fit, stop and explain; do not silently select a subset or substitute a collage.
- Save `reference-inventory.json` with original paths and roles, and log the exact ordered references and prompt for each call. Verify that every generation/edit call includes the full inventory before claiming all references were used. This verifies submission, not equal model attention to each image.

## Default Layout Contract

- Use the repo `scripts/compose_turnaround_sheet.py` entry point and its single `scripts/compose_unmeasured_sheet.py` compositor. Reuse accepted source assets for layout changes.
- Divide the canvas into five equal-width columns and three equal-height rows. Use 1876 px as the default canvas height and 575 px as the minimum column width; expand all five columns equally when a wide or chibi body requires more space.
- Put `HANDS`, `FEET / FOOTWEAR`, and `OUTFIT DETAILS` in row 1, columns 1–3 as three 1×1 cells. Put the two selected expressions in row 1, columns 4–5 as two 1×1 cells.
- Put `FRONT`, `LEFT PROFILE`, and `BACK` in columns 1–3, spanning rows 2–3 as three 1×2 cells. Put the unchanged neutral `NORMAL` portrait in columns 4–5, spanning rows 2–3 as one 2×2 cell.
- Crop transparent source margins by the alpha bbox, then scale each full-body view uniformly within its 1×2 cell using equal top and sole margins. Align silhouette tops and soles; these are pixel guides, not physical stature measurements.
- Fit every detail and portrait without stretching or clipping. Keep all labels in the lower-right corners and draw only grid separators; do not reserve a header or ruler gutter.
- Preserve existing accepted source pixels, outfit, identity, apparent age, and expressions when changing layout only. Do not regenerate assets for a ruler-removal request. Keep `NORMAL` byte-identical to the anchor.
- Save config and manifest with `layout_mode: "unmeasured"`, `ruler: null`, and empty `body_data`. Ignore stale metric fields in this mode; never let them restore rulers implicitly.
- Run the repo verifier entry point; it accepts only the unmeasured layout. Check the 5×3 cell spans, aspect ratios, body alignment, source hashes, neutral-anchor identity, and exported pixels. Visual identity, detail accuracy, emotion, and unilateral eye-state checks remain separate from geometry tests.

## Asset Contract

- For the default 5×3 sheet, supply exactly three full-body views, three design-detail images, two expression portraits, and one neutral portrait. The identity anchor is an intermediate source asset; the `NORMAL` portrait must be a byte-for-byte copy of it.
- Use one character per image on a transparent background, with no floor plane or cast shadow on the background. Preserve natural shading on the subject. Omit added layout text, rulers, borders, and watermarks; preserve existing garment lettering, patterns, and worn accessories. Remove unrelated scenery, not character design details.
- Keep full-body figures upright with soles visible and arms relaxed away from the torso.
- Frame detail assets tightly enough to read in one square cell. Show both hands in the hand asset. The foot asset must contain exactly two visible feet or shoes—one left and one right—both facing straight toward the viewer, with no alternate angles, duplicates, insets, extra limbs, or extra footwear. Do not invent unseen details without disclosing the inference.
- Use the same visual style as the character reference; do not introduce a style requirement when none was requested.
- Use viewer-relative wording for eye edits: `LEFT SIDE OF THE IMAGE` or `RIGHT SIDE OF THE IMAGE`.

## Reference-first Identity Contract

- Let the supplied images define the subject's identity. Do not translate your visual assessment into subject-specific facial descriptions, guessed proportions, numerical age, or an inferred age category in generation/edit prompts. Only include such attributes when the user explicitly supplies or requests them.
- Keep identity instructions referential: `Preserve the same person and apparent age shown in the original references; do not redesign or beautify the face.` Do not expand this into a list defining the subject's eye shape, nose, jaw, or other anatomy. Pose and requested expression actions, including which eye opens or closes, remain necessary instructions.
- Use prompts to specify the requested transformation: view, pose, framing, background, expression, and which original supplies an outfit/hair version. Do not assign individual facial features to different photos or ask for an averaged face. A clearer face photo may be identified by index without describing its features.
- Original references outrank generated anchors for likeness. Anchors and accepted views guide crop, expression editing, pose, clothing, and rendering continuity; never use them to lock in a facial mismatch. Repair or replace an unsuitable anchor from the originals before deriving dependent assets.
- Before each sheet call, remove assistant-inferred facial attributes and confirm all originals are attached. Expression/action packs use the complete accepted sheet through the second repo script. Report reference submission, layout geometry, and visual likeness separately; the first two cannot certify likeness or prove that a prompt change improved it without a new generation comparison.
- If no original exposes the face, request an unobscured reference for likeness-critical expression assets. A fabricated face cannot pass identity verification; keep any usable partial result and mark the missing evidence rather than reporting a full pass.

## Identity and Expression Contract

- Preserve identity and apparent age from the original references. The sheet pipeline uses the originals and accepted front as guides for HAPPY/ANGRY and the neutral anchor for NORMAL. Expression/action packs use the complete accepted sheet as their guide.
- Treat expression assets as close-up headshots, not portraits of the upper body: crop from topmost hair or ears to just below the chin or upper neck, keep the face and hair dominant, and allow only a narrow neckline/shoulder edge. Reject any expression that shows the chest, torso, upper arms, or waist.
- Review facial likeness visually against the originals, including natural asymmetry and visible skin details. These are review criteria, not a request to write a subject-specific anatomy description into the prompt.
- Allow coordinated facial-muscle deformation for expressions while keeping the underlying facial morphology unchanged.
- Make `HAPPY` strongly joyful with an open-mouth smile while closing only the image-left eye and keeping the image-right eye fully open.
- Make `ANGRY` strongly angry with a frown and closed mouth while closing only the image-right eye and keeping the image-left eye fully open. Do not prescribe added wrinkles, teeth, nose shape, or jaw structure to achieve intensity.
- Reuse the neutral anchor unchanged for `NORMAL`; do not apply a nominal or identity-preserving edit to it.
- Treat the emotional expression and unilateral eye pose as two independent constraints that must both pass. Never satisfy one by dropping the other, closing both eyes, or swapping sides.

## Output Contract

Return:

- the final PNG;
- the adjacent `*.manifest.json` manifest;
- the nine accepted default-layout source assets;
- the accepted identity anchor, prompt set, reference inventory, and per-call input log;
- the config JSON used;
- the verification output;
- a short note identifying any inferred back-view, hidden clothing detail, or other inferred design.

The compositor requires Python 3.10+ and Pillow.
