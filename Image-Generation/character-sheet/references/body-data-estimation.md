# Body Data Estimation

Use this procedure only when one or more Body Data fields are missing. The result describes the accepted generated character representation, not a physical or clinical measurement of a real person.

## Required anchor

Obtain height from, in order of authority:

1. a value explicitly supplied by the user;
2. trustworthy source metadata or a visible calibrated scale;
3. an LLM visual estimate when at least one source image shows the complete upright figure from head or topmost hair to both feet or soles;
4. the default character-setting height of `160 cm` when no usable complete full-body reference exists.

Record the selected source in config as `height_source`: `user`, `scale`, `visual_estimate`, or `default`.

A scale-free full-body estimate is a low-confidence character-setting estimate, not a physical measurement. Judge overall proportions, apparent age, body build, camera perspective, and any ordinary environmental cues only as weak supporting evidence. Round to the nearest 5 cm and display it with `~`. Do not claim that body proportions alone prove absolute height.

Do not visually estimate height from a face-only, bust, seated, substantially cropped, strongly foreshortened, or severely perspective-distorted image. Use the `160 cm` default in those cases and label it as a default setting rather than an image estimate.

## Standard fields

Fill these fields in this order:

1. Weight
2. Shoulder width
3. Arm length
4. Foot length
5. Bust circumference
6. Waist circumference
7. Hip circumference
8. Outseam
9. Inseam

User-supplied values override estimates and remain unprefixed. Prefix every LLM image estimate with `~`.

## Estimation method

1. Use the accepted full-body front view as the vertical reference, the profile view for body depth, and the back view as a consistency check. Prefer the least distorted view for each landmark.
2. Map topmost hair or head to the soles using the resolved height. Estimate linear distances as proportions of that span:
   - shoulder width: acromion to acromion;
   - arm length: shoulder joint to wrist;
   - foot length: heel to longest toe;
   - outseam: natural waist to floor;
   - inseam: crotch to floor.
3. Estimate bust, waist, and hip circumference from the combined front width and profile depth. Treat these as lower-confidence values because a single rendered silhouette does not reveal a true cross-section.
4. Estimate weight only as a rough visual body-build value at the known height. Do not infer health, diagnosis, or fitness.
5. Round lengths and circumferences to whole centimeters and weight to a whole kilogram. Do not add decimal precision that the images cannot support.

## Plausibility checks

- `inseam < outseam < height`;
- limb and foot lengths must be plausible relative to height;
- bust, waist, and hip values must agree with both front width and profile depth;
- clothing volume, camera perspective, hidden landmarks, and stylization reduce confidence;
- if one field cannot be supported, write `<Field>: not reliably estimable` for that field only.

## Output format

Return only the list strings required by the compositor, for example:

```json
[
  "Weight: ~26 kg",
  "Shoulder width: ~31 cm",
  "Arm length: ~44 cm",
  "Foot length: ~19 cm",
  "Bust circumference: ~70 cm",
  "Waist circumference: ~60 cm",
  "Hip circumference: ~74 cm",
  "Outseam: ~73 cm",
  "Inseam: ~55 cm"
]
```

In the final delivery, disclose: `LLM visual estimate; not physical measurement.`
