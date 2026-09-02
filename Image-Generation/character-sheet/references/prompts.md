# ImageGen Prompt Templates

Use English prompts for generation stability. Add only user-supplied character facts and reference roles; keep style unspecified unless the reference or user establishes one.

## Neutral identity anchor

Use the clearest identity-bearing reference. For a real person, prefer the image with the least occlusion and perspective distortion.

```text
Use case: identity-preserve
Asset type: authoritative neutral identity anchor for a character turnaround sheet
Input images: Image 1 is the authoritative identity reference.
Primary request: Create one exact frontal head-and-upper-shoulders neutral portrait of the same subject on a pure uniform white background.
Constraints: preserve facial morphology, face shape, eye spacing, nose bridge, width, tip and nostril geometry, mouth width, jaw, chin, natural asymmetry, skin tone and texture, visible moles or marks, hairline, hairstyle, apparent age, clothing neckline, and rendering treatment. Use a level head, direct gaze, closed relaxed mouth, and neutral expression.
Avoid: beautification, retouching, facial symmetry correction, age change, makeup change, identity blending, head rotation, perspective distortion, text, border, watermark.
```

Accept this asset before generating other views. It is the sole face authority for expressions.

## Front full-body view

```text
Use case: identity-preserve
Asset type: isolated character turnaround source asset
Input images: Image 1 is the authoritative character reference. Image 2 is the accepted neutral identity anchor and controls the face.
Primary request: Create one full-body FRONT view of the same character.
Composition: upright neutral turnaround pose, entire body visible from the topmost hair or accessory to the soles, arms relaxed slightly away from the torso, feet visible, centered, orthographic-like presentation.
Scene/backdrop: pure uniform white background; no floor plane.
Constraints: use Image 2 as the face authority. Preserve apparent age, facial morphology, natural asymmetry, body proportions, hairstyle, accessories, clothing design, colors, and rendering treatment from the references. Preserve the original outfit unless the user explicitly requests another outfit. Reproduce only visible garment details; do not invent badges, school emblems, logos, printed text, pocket stripes, or decorative trim. Keep pose suitable for alignment with the other views.
Avoid: perspective exaggeration, dynamic pose, cropped head or feet, shadow, reflection, props, text, ruler, measurement marks, borders, watermark.
```

## Dependent profile or back view

```text
Use case: identity-preserve
Asset type: isolated character turnaround source asset
Input images: Image 1 is the accepted front full-body asset and controls body proportions, outfit construction, hair length, figure scale, pose family, and rendering treatment. Image 2 is the accepted neutral identity anchor and controls facial identity. Image 3 is the original character reference and is secondary evidence only.
Primary request: Create one full-body <LEFT PROFILE / BACK> view of the same character.
Composition: upright neutral turnaround pose, entire body visible from the topmost hair or accessory to the soles, arms relaxed slightly away from the torso, feet visible, centered, orthographic-like presentation. Match the accepted front asset's figure scale and vertical crop.
Scene/backdrop: pure uniform white background; no floor plane.
Constraints: preserve identity, apparent age, body proportions, hairstyle, accessories, clothing design, colors, and rendering treatment. Preserve the original outfit unless the user explicitly requests another outfit. Reproduce only supported garment details; if the back is hidden, infer the minimum coherent back construction.
Avoid: perspective exaggeration, dynamic pose, cropped head or feet, shadow, reflection, props, text, ruler, measurement marks, borders, watermark.
```

Generate each view separately. Disclose inferred hidden details.

## Facial-expression source

```text
Use case: identity-preserve
Asset type: facial-expression source asset for a character turnaround sheet
Input images: Image 1 is the accepted neutral identity anchor and the sole face authority.
Primary request: Create a centered front-facing head-and-upper-shoulders crop with <EXPRESSION>.
Scene/backdrop: pure uniform white background.
Constraints: preserve the same underlying facial morphology, face shape, eye spacing, nose geometry, mouth width, jaw, chin, natural asymmetry, skin tone and texture, visible marks, hairline, hairstyle, hair accessories, apparent age, clothing neckline, colors, rendering treatment, crop, and scale. Coordinated facial-muscle movement is allowed and required when necessary for the requested emotion.
Avoid: beautification, retouching, morphological redesign, head rotation, perspective distortion, extra accessories, text, border, watermark.
```

### Strong-expression default package

- `HAPPY`: `Create an unmistakably happy expression using a broad genuine open-mouth smile, clearly visible natural upper teeth, lifted mouth corners, raised cheeks, and subtle smile lines. Simultaneously close only the eye on the LEFT SIDE OF THE IMAGE as viewed by the viewer, and keep the eye on the RIGHT SIDE OF THE IMAGE fully open with a stable forward gaze. The happy emotion and the unilateral eye closure are two separate mandatory conditions; satisfy both. Do not close both eyes and do not swap sides. The emotion must read immediately at thumbnail size, not as a polite smile.`
- `ANGRY`: `Create an unmistakably angry expression using eyebrows drawn clearly downward and inward, a focused intense stare, tense lower eyelids and nose area, firmly pressed lips with lowered corners, and natural jaw tension. Simultaneously close only the eye on the RIGHT SIDE OF THE IMAGE as viewed by the viewer, and keep the eye on the LEFT SIDE OF THE IMAGE fully open with a stable forward gaze. The angry emotion and the unilateral eye closure are two separate mandatory conditions; satisfy both. Do not close both eyes and do not swap sides. Keep the mouth closed; do not scream.`
- `NORMAL`: copy the accepted neutral identity anchor unchanged. Do not call ImageGen.

Use this package unless the user names different expressions. Expression intensity may deform the relevant facial muscles, but must not alter the underlying identity. Inspect both generated expression assets at full size and reject any result that loses the emotion, closes the wrong eye, closes both eyes, or fails to keep the opposite eye visibly open.

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

Use targeted facial edits when the first expression generation has the correct emotion but the wrong unilateral eye state. Edit the accepted expression asset rather than regenerating the whole face: make one eye-state correction, preserve the emotion and every other feature, then re-check both simultaneous requirements.
