# Motion Contract

## Visual Rules

- Use a pure or near-black background: `#000000` to `#050505`.
- Use white or near-white foreground text: `#ffffff` to `#f4f4f5`.
- Add only subtle grain or star specks if the target video already uses a
  cinematic dark style.
- Avoid colored backgrounds, heavy gradients, horizontal neon-line fields, and
  full-screen colored flashes.
- Keep all text large enough for mobile viewing.

## Typography

- Use a clean sans-serif font.
- Prefer one strong line or two short lines.
- Use large display sizing: about 9-15% of frame height for the hero phrase.
- Keep letter spacing normal or slightly positive. Do not use compressed text.
- Avoid decorative, playful, serif, or handwritten fonts unless the video brand
  explicitly needs them.

## Motion Grammar

Default entry style:

- type characters one by one from an empty line to the full phrase
- pair each visible character with a quiet typing click
- add a very light opacity/blur soften on the newly appearing character only

Fallback entry styles, only if the user explicitly asks:

- opacity fade from 0 to 1
- blur-to-sharp reveal
- word snapping in from a short horizontal smear

Use one of these change styles:

- key word replacement
- phrase crossfade
- horizontal smear between nouns
- split-word spacing for the final phrase

For replacement states, clear or smear the previous phrase first, then type the
next phrase character by character. Do not crossfade the full replacement text
into view all at once.

Use one of these exits:

- white velocity wipe
- text smear into darkness
- fade to black
- hard cut after final hold

## Restraints

- Do not reveal a full line at once unless the user rejects the typing style.
- Do not use a typing speed faster than readability allows; stay near
  `10-16 chars/s` for Chinese and mixed Chinese/English.
- Do not click for spaces, line breaks, or punctuation-only pause frames unless
  the sound design needs a deliberate accent.
- Do not use more than 3 text states before the final hold.
- Do not make the opener feel like a slide. Motion must be minimal but alive.
- Do not call the result pixel-perfect or source-aligned.

## Typing SFX

- Use short, dry key-click sounds, not notification beeps.
- Keep typing clicks quiet: target about `-24 LUFS` to `-18 LUFS` relative to a
  normal voiceover mix, or about `-18 dB` to `-12 dB` peak for standalone openers.
- Slightly vary click gain and pitch so the sound is not mechanical.
- Start clicks exactly when the first visible character appears.
- Stop clicks during readable holds and transitions.
- If there is background music, duck clicks under the music rather than making
  them the lead sound.
