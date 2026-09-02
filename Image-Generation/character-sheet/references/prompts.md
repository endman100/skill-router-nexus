# ImageGen Prompt Templates

Use English prompts for generation stability. Add only user-supplied character facts and reference roles; keep style unspecified unless the reference or user establishes one.

## Full-body view

```text
Use case: identity-preserve
Asset type: isolated character turnaround source asset
Input images: Image 1 is the authoritative character reference.
Primary request: Create one full-body <FRONT / LEFT PROFILE / BACK> view of the same character.
Composition: upright neutral turnaround pose, entire body visible from the topmost hair or accessory to the soles, arms relaxed slightly away from the torso, feet visible, centered, orthographic-like presentation.
Scene/backdrop: pure uniform white background; no floor plane.
Constraints: preserve identity, apparent age, body proportions, hairstyle, accessories, clothing design, colors, and rendering treatment from the reference. Preserve the original outfit unless the user explicitly requests another outfit. Reproduce only visible garment details; do not invent badges, school emblems, logos, printed text, pocket stripes, or decorative trim. Keep pose suitable for alignment with the other views.
Avoid: perspective exaggeration, dynamic pose, cropped head or feet, shadow, reflection, props, text, ruler, measurement marks, borders, watermark.
```

Generate each view separately. If the reference does not show the back, infer the minimum coherent back construction and disclose that inference.

## Facial-expression source

```text
Use case: identity-preserve
Asset type: facial-expression source asset for a character turnaround sheet
Input images: Image 1 is the authoritative face reference.
Primary request: Create a centered front-facing head-and-upper-shoulders crop with <EXPRESSION>.
Scene/backdrop: pure uniform white background.
Constraints: preserve exact character identity, facial proportions, head angle, hairstyle, hair accessories, clothing neckline, colors, rendering treatment, crop, and scale used by the other facial assets.
Avoid: head rotation, perspective distortion, extra accessories, text, border, watermark.
```

## Targeted facial edit

```text
Use case: precise-object-edit
Asset type: facial-expression source asset for a character turnaround sheet
Input image: this image is the edit target.
Primary request: Change only <ONE FACIAL FEATURE>.
Constraints: preserve the exact same character identity, facial proportions, front-facing head angle, gaze, all unedited facial features, hairstyle, accessories, clothing, crop, scale, white background, rendering treatment, linework, colors, and lighting. Do not redraw any other feature.
Avoid: text, border, watermark.
```

For side-specific eye edits, write both the visual side and the invariant:

```text
Close the eye on the LEFT SIDE OF THE IMAGE as viewed by the viewer. Keep the eye on the RIGHT SIDE OF THE IMAGE fully open and unchanged. This is viewer-relative, not the character's anatomical left.
```

## Default three-face package

- Face 1: natural open mouth; both eyes unchanged.
- Face 2: eye on the left side of the image fully closed; the other eye unchanged.
- Face 3: eye on the right side of the image visibly half closed; the other eye unchanged.

Keep the primary emotion labels chosen by the user. Facial-feature variations do not require renaming existing labels unless requested.
