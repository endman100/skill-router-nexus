# ImageGen prompt set

Exact ordered inputs are in `call-log.json`.

## identity-anchor

Use case: identity-preserve
Asset type: neutral portrait source for a character turnaround sheet
Input images: Image 1 is the sole original reference and is the authority for identity, apparent age, hairstyle, outfit neckline, proportions, colors, and rendering treatment.
Primary request: Create one exact frontal head-and-upper-shoulders neutral portrait of the same character on a pure uniform white background.
Composition: centered, head level, facing exactly straight ahead, both eyes naturally open, mouth closed and relaxed.
Constraints: preserve the same character and apparent age shown in Image 1; do not redesign, beautify, mature, or retouch the face. Preserve the hairstyle, cat ears, hair ornaments, sailor-style clothing neckline, and the soft 3D anime rendering treatment from Image 1.
Avoid: head rotation, perspective exaggeration, added accessories, text, labels, borders, watermark, scenery, or cast shadow. Preserve natural shading on the subject.

## front

Use case: identity-preserve
Asset type: isolated character turnaround source asset
Input images: Image 1 is the sole original reference and defines identity, apparent age, outfit, hairstyle, proportions, colors, and rendering. Image 2 is the accepted neutral portrait, used only as a consistency guide.
Primary request: Create one full-body FRONT view of the same character.
Composition: upright neutral turnaround pose, entire body visible from the topmost ear and hair to the sandal soles, arms relaxed slightly away from the torso, feet visible, centered, orthographic-like presentation.
Scene/backdrop: pure uniform white background; no floor plane.
Constraints: preserve the same character and apparent age shown in Image 1; do not redesign or beautify the face. Preserve the stylized head-to-torso proportions, cat ears, very long hair, sailor-style white dress, collar, bow, shoulder accents, wrist accessories, mismatched ankle accents, sandals, colors, and soft 3D anime rendering. Match Image 2's face without overriding Image 1. Complete only hidden details minimally.
Avoid: scenery, cast shadows, reflections, extra props, labels, rulers, borders, watermarks, cropped ears, hair, or feet.

## left-profile

Use case: identity-preserve
Asset type: isolated character turnaround source asset
Input images: Image 1 is the sole original reference and defines identity. Image 2 is the accepted front full-body asset, guiding outfit, proportions, pose family, scale, and rendering. Image 3 is the neutral portrait continuity guide.
Primary request: Create one full-body LEFT PROFILE view of the same character, showing the character's left side.
Composition: exact 90-degree left-facing profile, upright neutral turnaround pose, entire body visible from the topmost ear and hair to the sandal soles, arms relaxed slightly away from the torso, feet visible, centered, orthographic-like presentation. Match Image 2's figure scale and vertical crop.
Scene/backdrop: pure uniform white background; no floor plane.
Constraints: preserve the same character and apparent age shown in Image 1. Preserve the cat ears, very long hair, sailor-style white dress, collar, bow, shoulder accents, wrist accessory, mismatched ankle accents, sandals, colors, stylized proportions, and soft 3D anime rendering. Match Image 2's clothing continuity and do not introduce facial drift. Infer only the minimum coherent hidden construction.
Avoid: three-quarter view, scenery, cast shadows, reflections, extra props, labels, rulers, borders, watermarks, cropped ears, hair, or feet.

## back

Use case: identity-preserve
Asset type: isolated character turnaround source asset
Input images: Image 1 is the sole original reference and defines identity. Image 2 is the accepted front full-body asset, guiding outfit, proportions, pose family, scale, and rendering. Image 3 is the neutral portrait continuity guide.
Primary request: Create one full-body BACK view of the same character, facing directly away from the viewer.
Composition: exact rear orthographic-like view, upright neutral turnaround pose, entire body visible from the topmost ear and hair to the sandal soles, arms relaxed slightly away from the torso, feet visible, centered. Match Image 2's figure scale and vertical crop.
Scene/backdrop: pure uniform white background; no floor plane.
Constraints: preserve the same character and apparent age shown in Image 1. Preserve the cat ears, very long hair, sailor-style white dress, shoulder accents, wrist accessory, mismatched ankle accents, sandals, colors, stylized proportions, and soft 3D anime rendering. Match Image 2's outfit and hairstyle continuity. Infer only the minimum coherent hidden back construction; keep the long hair parted enough to show a plausible simple back of the dress.
Avoid: turning the head toward camera, three-quarter view, visible face, scenery, cast shadows, reflections, extra props, labels, rulers, borders, watermarks, cropped ears, hair, or feet.

## happy-first-pass

Use case: identity-preserve
Asset type: facial-expression source asset for a character turnaround sheet
Input images: Image 1 is the sole original reference and defines identity. Image 2 is the accepted neutral portrait to edit, supplying pose, outfit, crop, and scale.
Primary request: Create a centered front-facing head-and-upper-shoulders crop with a strongly happy open-mouth smile. Simultaneously close only the eye on the LEFT SIDE OF THE IMAGE as viewed by the viewer; keep the eye on the RIGHT SIDE OF THE IMAGE fully open. Both the joy and the one-eye closure must be unmistakable. Do not swap sides or close both eyes.
Scene/backdrop: pure uniform white background.
Constraints: preserve the same character and apparent age shown in Image 1; do not redesign, beautify, or retouch the face. Keep Image 2's head angle, hairstyle, cat ears, accessories, clothing, rendering, crop, and scale. Allow only the facial movement needed for the requested expression.
Avoid: head rotation, perspective exaggeration, added accessories, text, labels, border, watermark, or cast shadow.

## happy-eye-repair

Use case: precise-object-edit
Asset type: facial-expression source asset for a character turnaround sheet
Input images: Image 1 is the sole original identity reference. Image 2 is the expression asset to edit.
Primary request: Change only the eye states in Image 2. CLOSE the eye centered near (41%, 52%) on the LEFT SIDE OF THE IMAGE as viewed by the viewer. OPEN the eye centered near (61%, 52%) on the RIGHT SIDE OF THE IMAGE. Do not mirror the image.
Final required state: image-left eye closed; image-right eye fully open; strongly happy open-mouth smile unchanged.
Constraints: preserve the same character and apparent age shown in Image 1. Keep Image 2's joyful emotion, open mouth, head angle, hairstyle, cat ears, accessories, clothing, crop, scale, white background, colors, and rendering unchanged.
Avoid: altering anything except the two eye states, swapping sides, closing both eyes, head rotation, added text, border, or watermark.

## angry

Use case: identity-preserve
Asset type: facial-expression source asset for a character turnaround sheet
Input images: Image 1 is the sole original reference and defines identity. Image 2 is the accepted neutral portrait to edit, supplying pose, outfit, crop, and scale.
Primary request: Create a centered front-facing head-and-upper-shoulders crop with a strongly angry expression, a clear frown, and a closed mouth. Simultaneously close only the eye on the RIGHT SIDE OF THE IMAGE as viewed by the viewer; keep the eye on the LEFT SIDE OF THE IMAGE fully open. Both the anger and the one-eye closure must be unmistakable. Do not swap sides or close both eyes.
Scene/backdrop: pure uniform white background.
Constraints: preserve the same character and apparent age shown in Image 1; do not redesign, beautify, or retouch the face. Keep Image 2's head angle, hairstyle, cat ears, accessories, clothing, rendering, crop, and scale. Allow only the facial movement needed for the requested expression.
Avoid: open mouth, smile, head rotation, perspective exaggeration, added accessories, text, labels, border, watermark, or cast shadow.
