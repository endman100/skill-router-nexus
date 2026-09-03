# Body Data and Height Evidence

Use this reference only for explicitly requested measured output (`layout_mode: "measured"`). The default unmeasured layout skips all height inference, fallback values, rulers, and Body Data.

Describe the accepted character representation, not a clinical measurement of a real person. Preserve supplied measurements exactly; distinguish estimates from design choices.

## Resolve height

1. Use an explicit factual height (`user`) or trustworthy source metadata first.
2. Inspect original references for independent metric evidence: a labeled ruler, an object with verified dimensions, or a person of supplied height. Check that endpoints, subject extent, geometry, and scale are usable.
3. Use `scale` only when a justified metric calculation is possible. Otherwise a usable complete original full-body reference may support a low-confidence `visual_estimate`; save its rationale and uncertainty range and round to 5 cm.
4. For a cropped or highly stylized reference without metric evidence, use an explicitly selected `design_prior` when the user wants a practical character setting. State the assumption. Do not describe a proposed or accepted height as discovered fact.
5. With no supported inference or selected design setting, use the agreed `160 cm` fallback (`default`), explicitly identified as default.

Neither a complete silhouette nor a head-count ratio supplies absolute centimeters by itself. Do not map chibi/realistic drawing styles to fixed centimeter values. Generated legs, body views, rulers, shadows, or props add no independent evidence about the original subject's height.

## Reproducible evidence

Save `height-input.json`, then run:

```powershell
python scripts/estimate_character_height.py height-input.json --output height-estimate.json
```

The script separates three paths:

- `mode: scale`: use original-reference landmarks, a verified reference length, and compatible image geometry. It computes `height_cm = body_span_px / reference_span_px * reference_cm` and a pixel/length uncertainty interval. This simple ratio requires equal-scale, parallel measurement directions or a documented rectification. It is not a general perspective correction.
- `mode: design_prior`: use a supplied `height_cm` and explicit `reason`. Optional generated landmarks describe proportions only. The output says `not_measured` and keeps physical height unknown.
- `mode: unresolved`: record why metric scale is absent. Return no height; do not fabricate a conversion.

Record `reference_kind` (`original` or `generated`), source file paths/hashes, top/chin/sole y-coordinates when available, source of the known size, geometry assumptions, pixel uncertainty, and selected height source. Use the same accepted assets and saved inputs for reruns. If manually placed landmarks change, retain both versions and rerun; test plausible endpoint perturbations.

For a design prior, set `height_evidence_file: "height-estimate.json"` in the compositor config; the compositor requires matching height/source and records the evidence hash. For a subjective full-body `visual_estimate`, save the LLM rationale and range separately; this script is not a learned height predictor and does not validate that inference.

For `scale`, choose a consistent endpoint definition (e.g. topmost hair to soles for the sheet). Do not call hair-top-to-shoe-bottom span barefoot stature. Do not treat an unknown shoe, phone, head, or door as a precisely known size. Foreshortened, seated, cropped, or unequal-depth subjects need additional references or valid calibrated geometry; do not repair them by inventing scale.

Example design input:

```json
{
  "mode": "design_prior",
  "height_cm": 150,
  "reason": "User accepted a 150 cm character-setting trial; no metric reference exists.",
  "reference_kind": "generated",
  "landmarks": {"top_y": 68, "chin_y": 542, "sole_y": 1473}
}
```

Example scale input (illustrative test data, not this character):

```json
{
  "mode": "scale",
  "reference_kind": "original",
  "landmarks": {"top_y": 100, "sole_y": 800},
  "reference_span_px": 140,
  "reference_cm": 30,
  "reference_cm_error": 0.1,
  "pixel_error": 1,
  "geometry": "equal_scale",
  "reason": "Verified 30 cm vertical target in the same frontoparallel plane."
}
```

Geometry tests validate ruler placement, not height-estimation accuracy. Repeating the same input validates numerical reproducibility, not the correctness of the physical assumption. Only independent known-height data can validate height accuracy.

For perspective metrology and its remaining scale factor, see [Criminisi et al., Single View Metrology](https://robots.ox.ac.uk/~vgg/publications/2000/Criminisi00a/).

## Body Data

Fill Weight, Shoulder width, Arm length, Foot length, Bust circumference, Waist circumference, Hip circumference, Outseam, and Inseam. Preserve user values; prefix image-based estimates with `~`. Do not add false decimal precision.

Measure supported linear spans on accepted views relative to the selected height: shoulder-to-shoulder, shoulder-to-wrist, heel-to-toe, waist-to-sole, and crotch-to-sole. Check `inseam < outseam < height`. For circumferences, front width and profile depth are only weak evidence because clothing hides body cross-sections. Weight is not recoverable from stylized silhouettes; mark unsupported fields `not reliably estimable` rather than converting head count to kilograms.

With a `design_prior`, derived lengths are design dimensions, not measurements of the original subject. Recompute them when the chosen scale changes. Do not silently apply human anthropometry to exaggerated chibi proportions. Keep uncertainty and field provenance in the sidecar, not as redundant image text.

In delivery distinguish measured scale, low-confidence visual inference, and explicit character setting. Never say that aesthetics proved absolute height.
