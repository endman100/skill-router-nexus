# ImageGen Prompt Templates

Use these concise English templates. Add only user-requested changes and image-index roles; keep style unspecified unless the reference or user establishes one. Do not infer facial descriptions, proportions, numerical age, or age categories; include such attributes only when explicitly supplied or requested by the user. The original images supply identity; text specifies the transformation. Requested emotion and eye opening/closure are actions, not identity descriptions.

These prompts produce isolated source assets, not a final layout. Default to the bundled unmeasured Python layout: no rulers, height labels, `(SET)`, body data, or heading. For layout-only changes reuse accepted assets; do not call ImageGen again or change apparent age, clothing, or proportions.

In every generation/edit template, Images 1 through N are ALL original references for this case, in stable order. Attach them as actual image inputs on every call. Replace placeholders with concrete indices and only name inputs actually attached. Generated assets are additional guides, never identity authorities over the originals. If outfits or hairstyles differ, identify one version by image index; do not splice facial features or age cues across photos. State: `Use clothing and hairstyle exclusively from Image K; the other originals are identity references, not alternative clothing designs.` Verify this before accepting the anchor. When slots are limited, retain all originals and the necessary target/view before optional generated guides.

## Neutral identity anchor

Reuse a suitable original neutral portrait before generating one. If a change is necessary, attach all originals and request only the missing pose, expression, framing, or background changes below. If needed, identify the clearest face photo by index; do not describe its anatomy.

```text
Use case: identity-preserve
Asset type: neutral portrait source for a character turnaround sheet
Input images: Images 1 through N are all original references of the same subject. <Only if needed: outfit/hair from Image K; clearest face reference is Image J.>
Primary request: Create one exact frontal head-and-upper-shoulders neutral portrait of the same subject on a pure uniform white background.
Constraints: preserve the same person and apparent age shown in the originals; do not redesign, beautify, or retouch the face. Preserve the referenced hair, clothing neckline, and rendering treatment. Head level and facing straight ahead, both eyes naturally open, mouth closed and relaxed.
Avoid: head rotation, perspective exaggeration, added labels, border, watermark. Preserve garment lettering and natural shading on the subject; no cast shadow on the white background.
```

Compare the portrait with the originals before accepting it. It is a framing and expression-editing guide, not proof of likeness; the originals remain the identity authority for subsequent calls.

## Front full-body view

```text
Use case: identity-preserve
Asset type: isolated character turnaround source asset
Input images: Images 1 through N are all original references and define identity. Image N+1 is the accepted neutral portrait, used only as a consistency guide. <If needed: outfit/hair from Image K.>
Primary request: Create one full-body FRONT view of the same character.
Composition: upright neutral turnaround pose, entire body visible from the topmost hair or accessory to the soles, arms relaxed slightly away from the torso, feet visible, centered, orthographic-like presentation.
Scene/backdrop: pure uniform white background; no floor plane.
Constraints: preserve the same person and apparent age shown in the originals; do not redesign or beautify the face. Preserve the reference's head-to-torso proportions without normalizing stylized anatomy. Preserve hairstyle, accessories, outfit, colors, and rendering treatment. Do not invent decorative garment details. Complete unseen clothing minimally and consistently.
Preserve existing garment lettering, patterns, worn accessories, and natural shading on the subject. Omit unrelated scenery, background cast shadows or reflections, added labels, rulers, borders, and watermarks. Do not crop the head or feet.
```

## Dependent profile or back view

```text
Use case: identity-preserve
Asset type: isolated character turnaround source asset
Input images: Images 1 through N are all original references and define identity. Image N+1 is the accepted front full-body asset, guiding outfit, proportions, pose family, scale, and rendering. <Only if attached: Image N+2 is the neutral portrait framing/continuity guide.>
Primary request: Create one full-body <LEFT PROFILE / BACK> view of the same character.
Composition: upright neutral turnaround pose, entire body visible from the topmost hair or accessory to the soles, arms relaxed slightly away from the torso, feet visible, centered, orthographic-like presentation. Match the accepted front asset's figure scale and vertical crop.
Scene/backdrop: pure uniform white background; no floor plane.
Constraints: preserve the same person and apparent age shown in the originals; do not redesign or beautify the face. Preserve the referenced hairstyle and outfit. Match the accepted front's proportions and clothing continuity without copying facial drift. Infer only the minimum coherent hidden construction.
Preserve existing garment lettering, patterns, worn accessories, and natural shading on the subject. Omit unrelated scenery, background cast shadows or reflections, added labels, rulers, borders, and watermarks. Do not crop the head or feet.
```

Generate each view separately. Disclose inferred hidden details.

## Facial-expression source

```text
Use case: identity-preserve
Asset type: facial-expression source asset for a character turnaround sheet
Input images: Images 1 through N are all original references and define identity. Image N+1 is the accepted neutral portrait to edit, supplying pose, outfit, crop, and scale.
Primary request: Create a centered front-facing head-and-upper-shoulders crop with <EXPRESSION>.
Scene/backdrop: pure uniform white background.
Constraints: preserve the same person and apparent age shown in the originals; do not redesign, beautify, or retouch the face. Keep the target's head angle, hairstyle, clothing, rendering, crop, and scale. Allow the facial-muscle movement needed for the requested expression.
Avoid: head rotation, perspective exaggeration, added accessories, added labels, border, watermark. Preserve garment lettering and natural shading on the subject; no cast shadow on the white background.
```

### Strong-expression default package

- `HAPPY`: `Strongly happy, with an open-mouth smile. Simultaneously close only the LEFT eye in image coordinates; keep the RIGHT eye fully open. Both the joy and the one-eye closure must be clearly visible. Do not swap sides or close both eyes.`
- `ANGRY`: `Strongly angry, with a frown and closed mouth. Simultaneously close only the RIGHT eye in image coordinates; keep the LEFT eye fully open. Both the anger and the one-eye closure must be clearly visible. Do not swap sides or close both eyes.`
- `NORMAL`: copy the accepted neutral identity anchor unchanged. Do not call ImageGen.

Use this package unless the user names different expressions. Expression intensity may deform the relevant facial muscles, but must not alter the underlying identity. Inspect both generated expression assets at full size and reject any result that loses the emotion, closes the wrong eye, closes both eyes, or fails to keep the opposite eye visibly open.

## Targeted facial edit

```text
Use case: precise-object-edit
Asset type: facial-expression source asset for a character turnaround sheet
Input images: Images 1 through N are all original references and define identity. Image N+1 is the expression asset to edit.
Primary request: Change only <THE REQUESTED EXPRESSION OR EYE STATE>.
Constraints: preserve the same person and apparent age shown in the originals. Keep the target's emotion except for the requested change, head angle, gaze of the unedited eye, unedited facial features, hair, outfit, crop, scale, white background, and rendering unchanged.
Avoid: added labels, border, watermark. Preserve original garment lettering and patterns.
```

For side-specific eye edits, write both the visual side and the invariant:

```text
Close the eye on the LEFT SIDE OF THE IMAGE as viewed by the viewer. Keep the eye on the RIGHT SIDE OF THE IMAGE fully open and unchanged. This is viewer-relative, not the character's anatomical left.
```

Use targeted facial edits when the first expression generation has the correct emotion but the wrong unilateral eye state. Edit the accepted expression asset rather than regenerating the whole face: make one eye-state correction, preserve the emotion and every other feature, then re-check both simultaneous requirements.

If viewer-left/right wording still fails, locate the two eyes on the inspected edit target and give their approximate percentage coordinates measured from its top-left corner: `OPEN the eye at (x%, y%); CLOSE the eye at (x%, y%). Do not mirror the image.` Compute these positions anew for that target, never copy case-specific coordinates. This is edit localization, not a facial identity description. Keep the original references attached, retain the emotion, and stay within the two-retry limit. Record first-pass failures separately from repaired outputs; neither successful submission nor a few successful repairs proves repeat-run stability.
