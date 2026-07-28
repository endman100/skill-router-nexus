# Tool Recipes

## HyperFrames

Use HyperFrames when the video project is already motion-heavy or visual polish
matters.

Implementation notes:

- Create an opener scene as a separate composition section.
- Reveal text by slicing visible characters from the timing plan at each frame.
- Trigger typing click SFX from the plan's `sfx_events`, aligned to character
  appearance times.
- Animate only the newly appearing character with subtle opacity/blur if needed.
- Add a black rectangle/background layer for the full scene.
- Keep any grain subtle and procedural.
- Export the opener alone first, then compose it with the body.

## Remotion

Use Remotion when the project is already React/Remotion-based.

Implementation notes:

- Drive all timing from `useCurrentFrame()` and `fps`.
- Keep text states in an array generated from the opener plan.
- Compute visible text from `typing_events` so characters appear one by one.
- Use Remotion audio sequencing for click SFX and keep click timestamps tied to
  the same typing events.
- Use `interpolate()` only for subtle entry blur/opacity and transition out.
- Export a still frame at the first readable beat and final hold for QC.

## ffmpeg

Use ffmpeg for simple utility openers or draft previews.

Implementation notes:

- Use a black `color` source.
- For a real typing effect, render image frames or use a text-layer pipeline;
  ffmpeg `drawtext` alone is too limited on systems without `drawtext`.
- Generate synthetic click SFX or place a short click sample according to
  `sfx_events`.
- Prefer ffmpeg for utility previews, not complex word replacement.
- Verify output duration, resolution, and frame rate with `ffprobe`.
