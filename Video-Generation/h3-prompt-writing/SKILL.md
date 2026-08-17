---
name: h3-prompt-writing
description: Write MiniMax H3 video generation prompts for T2VA, I2VA, FL2VA, L2VA, and Ref2VA. Use when rewriting multimodal requests into H3 prompt structures, composing integrated_multimodal_description, overall_soundscape, and non_diegetic_music, aligning keyframes, or defining reference labels for images, videos, and audio.
---

# H3 Prompt Writing

## Required Inputs

- Determine the effective video duration before writing. Use the duration supplied by the caller or host; if neither provides one, ask the user. MiniMax H3 durations must be 1–15 seconds.
- Inventory only media that is actually available. Do not invent or cite a media label for an unprovided asset.
- Treat a reference-video soundtrack as reference media only when its same-numbered reference video is also available. A standalone reference audio is reference media by itself.

## Workflow

1. Resolve the input mode from the available media using the rules below.
2. For T2VA, I2VA, FL2VA, or L2VA, read `references/base-en.txt` completely and follow its final prompt structure.
3. For Ref2VA, read both `references/base-en.txt` and `references/ref-en.txt` completely. The full-reference guide defines the six-section output, while the base guide supplies the shared shot, camera, dialogue, sound, and timing rules.
4. Map every available asset to its canonical H3 label before drafting.
5. Write the final prompt with the exact fields, section order, labels, and timing notation required by the selected guide.
6. Validate the output against the checklist below before returning it.

## Mode Resolution

Apply these rules in order:

1. If any reference image, reference video, paired reference-video soundtrack, or standalone reference audio is available, use Ref2VA. First and last frames may also be used as concrete keyframe anchors in this mode.
2. Otherwise, if both first and last frames are available, use FL2VA.
3. Otherwise, if only the first frame is available, use I2VA.
4. Otherwise, if only the last frame is available, use L2VA.
5. Otherwise, use T2VA.

When the caller explicitly selects a mode, honor it and ignore media outside that mode. Reject the request only when a required input is missing.

## Media Labels

- Number pictures in presentation order: first frame, last frame, then reference images. Use `<Picture 1>`, `<Picture 2>`, and so on.
- Number reference videos independently as `<Video 1>`, `<Video 2>`, and so on.
- Number paired reference-video soundtracks and standalone reference audios together, in presentation order, as `<Audio 1>`, `<Audio 2>`, and so on.
- Keep every label's meaning stable across all sections of the final prompt.

## Base Modes

- T2VA: build the full audiovisual timeline from text.
- I2VA: start from the first frame and develop forward from it.
- FL2VA: describe the continuous path between the first and last frames.
- L2VA: infer a plausible opening and converge to the supplied last frame.

Use `integrated_multimodal_description`, `overall_soundscape`, and `non_diegetic_music` in the order shown in `references/base-en.txt`.

## Full-Reference Mode

Ref2VA rewrites use `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, and `non_diegetic_music` in that order. Reference labels stay consistent across all sections.

Read `references/ref-en.txt` for label rules, retention analysis, and complete examples.

## Output Rules

- Write rewrite sections in English; preserve dialogue, lyrics, and visible scene text in their original language.
- Describe each shot by composition, subjects, environment, actions, camera, sound, and the exact point where referenced content appears.
- Avoid plot summaries, unresolved reference labels, and timing that does not match the requested duration.
- Return only the final H3 prompt. Do not add an explanation, a mode announcement, a Markdown code fence, or executor-specific state tags unless the caller explicitly requests them.

## Validation Checklist

- The selected mode matches the available media and the user's intent.
- Every `<Picture N>`, `<Video N>`, `<Audio N>`, and `<Subject N>` label resolves to the same asset or subject everywhere it appears.
- The required fields are present once and remain in the exact order defined by the selected guide.
- Shot numbers are sequential, later-shot timestamps are strictly increasing, and no timestamp exceeds the effective duration.
- Dialogue, lyrics, and visible text preserve the user's exact wording and original language.
- The result contains only the final prompt and no unsupported claims about generated media or completed tool actions.
