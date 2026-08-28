---
name: h3-prompt-writing
description: Write production-ready MiniMax H3 audiovisual video prompts for T2VA, I2VA, FL2VA, L2VA, and full-reference Ref2VA. Use when users mention MiniMax H3, H3 prompt, 文生影片, 圖生影片, 首幀, 首尾幀, 尾幀, 參考生成, or ask to rewrite text, images, videos, or audio into H3's required prompt fields, shot timing, speaker tags, and reference labels.
---

# MiniMax H3 Prompt Writing

Convert a user's creative brief and reference assets into a self-contained MiniMax H3 prompt. Produce the prompt; do not call a generation API unless the user separately requests generation.

## Required Inputs

- Determine the effective video duration before writing. Use the duration supplied by the caller or host; if neither provides one, ask the user. Accept 1–15 seconds.
- Inventory only media that is actually available. Never invent or cite a label for an unprovided asset.
- Treat a reference-video soundtrack as reference media only when its corresponding reference video is available. Treat standalone reference audio as reference media by itself.

## Workflow

1. Inventory the supplied text, pictures, videos, audio, target duration, aspect ratio, and dialogue.
2. Resolve the input mode from the available media using the priority rules below. Honor an explicitly selected mode and ignore media outside it; reject only when that mode's required input is missing.
3. Preserve the user's story, required actions, reference relationships, dialogue, lyrics, and visible text. Add only concrete details that make the audiovisual timeline executable.
4. Write the selected format exactly. Keep field names, field order, labels, and time notation unchanged.
5. Run the final checklist before returning the prompt.

## Select the Mode

| Mode | Inputs and purpose |
| --- | --- |
| `T2VA` | Text only; construct the complete visual and audio timeline. |
| `I2VA` | One opening image; begin at that first frame and develop forward. |
| `FL2VA` | Opening and ending images; describe a continuous path between them. |
| `L2VA` | One ending image; infer a plausible opening and converge on that last frame. |
| `Ref2VA` | Any explicit reference image, video, paired reference-video soundtrack, or standalone reference audio; define and track reusable subjects, frames, source videos, and audio relationships. |

Resolve the mode in this order:

1. Use Ref2VA if any explicit reference image, reference video, paired reference-video soundtrack, or standalone reference audio is available. First and last frames may also be concrete keyframe anchors in this mode.
2. Otherwise use FL2VA when both first and last frames are available.
3. Otherwise use I2VA when only the first frame is available.
4. Otherwise use L2VA when only the last frame is available.
5. Otherwise use T2VA.

Match every cut, action, line, and final-frame alignment to the effective duration.

## Number Media Labels

- Number pictures in presentation order: first frame, last frame, then reference images. Use `<Picture 1>`, `<Picture 2>`, and so on.
- Number reference videos independently as `<Video 1>`, `<Video 2>`, and so on.
- Number paired reference-video soundtracks and standalone reference audios together, in presentation order, as `<Audio 1>`, `<Audio 2>`, and so on.
- Keep every label's meaning stable across the complete prompt.

## Shared Writing Rules

Write structural prose in English. Preserve dialogue, lyrics, and visible scene text in their original language.

### Shots and timing

- Start with `[Shot 1]` and omit its timestamp.
- Start each later shot with `[Shot N] At MM:SS.mmm, ...` using sequential numbers and strictly increasing cut times.
- Keep every cut time inside the effective duration.
- Use a cut only when it adds a new subject state, viewpoint, space, or time. Use camera motion for a modest framing change.
- For FL2VA, prefer a single continuous shot unless the user explicitly requests cuts.

### Visual description

For each shot, establish composition, subjects, appearance, positions, environment, lighting, actions, state changes, camera behavior, and synchronized sound. Describe what can be seen or heard rather than using unsupported abstractions such as "cinematic" or "beautiful" alone.

At the start of Shot 1, name the visual medium or style and the opening composition. Keep character identity, clothing, colors, props, screen direction, and spatial relationships consistent across shots.

### Camera behavior

Write camera movement as natural prose. Combine the useful parts of:

- Type: `Zoom In`, `Zoom Out`, `Push In`, `Pull Out`, `Pan Left`, `Pan Right`, `Truck Left`, `Truck Right`, `Tilt Up`, `Tilt Down`, `Pedestal Up`, `Pedestal Down`, `Arc Shot`, `Tracking Shot`, `Static Shot`, `POV`, `Roll Clockwise`, `Roll Counterclockwise`, `Shake Slightly`, or `Shake Strongly`.
- Amplitude, only when meaningful: `with small amplitude` or `with large amplitude`.
- Speed, only when meaningful: `at slow speed` or `at fast speed`.

Example: `The camera pushes in with small amplitude at slow speed toward the letter in her hands.`

### Speech, lyrics, and visible text

- Assign stable vocal-source IDs `(S1)`, `(S2)`, and so on in order of first vocal event. Give no ID to a silent character.
- Put only the language tag and exact spoken or sung words inside `<d>`: `<d>[Mandarin] 你終於來了。</d>`.
- Preserve the user's wording and punctuation. Do not translate dialogue, lyrics, or visible text.
- Describe a first-time speaker's identity, voice, action, and delivery outside `<d>`.
- For a voiceover, use `says in an off-screen voiceover` and state that the corresponding on-screen character's lips remain closed.
- When a line crosses a cut, place `<scenetrans>` at the connecting points and state that the audio continues across the cut.
- Use `<cutoff>` when speech is truncated by the video's end.
- Put visible signs, subtitles, labels, and other on-screen text in English double quotation marks.

### Sound layers

- Put dialogue, singing, diegetic music, and shot-synchronized sound in the timeline description.
- Write `overall_soundscape` as one paragraph of 1–4 English sentences covering ambience, physical sounds, and nonverbal human sounds. Do not repeat dialogue or singing there. Use `N/A` only for explicitly requested complete silence.
- Write `non_diegetic_music` as 1–3 English sentences covering audience-only instrumentation, tempo, rhythm, and dynamics. Put `N/A` when there is no audience-only music. Do not describe diegetic music here.

## Base Modes: T2VA, I2VA, FL2VA, L2VA

### Alignment instruction

For T2VA, omit an alignment instruction.

For I2VA, place this exact pattern first:

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
```

For FL2VA, place this exact pattern first and replace the placeholders:

```text
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.
```

For L2VA, place this exact pattern first and replace the placeholders:

```text
How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.
```

Use the actual final shot number for `N`. Format `S.SS` as the effective duration with exactly two decimal places. Follow the alignment instruction with one blank line.

### Core output

Always write these three fields in this order:

```text
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

For keyframes, connect the image to the timeline explicitly:

- I2VA: first-frame anchor → action onset → continuous development → result or reaction.
- FL2VA: first-frame state → observable intermediate changes → narrowing differences → exact last-frame state.
- L2VA: plausible preceding state → explicit transition path → gradual convergence → exact last-frame landing.

Do not merely repeat static descriptions of the supplied images. Describe the visible motion and state changes that connect them.

## Full-Reference Mode: Ref2VA

Use Ref2VA when the task needs explicit reference definitions and retention relationships. Write all six sections in this order:

```text
subject_definitions:
...

summary:
...

retention_analysis:
...

detailed_description:
...

overall_soundscape:
...

non_diegetic_music:
...
```

### Define references

Assign each label once and keep its meaning stable across all six sections:

| Label | Use |
| --- | --- |
| `<Subject N>` | Reusable visible content: person, animal, object, environment, clothing, prop, style, action, expression, or pose. |
| `<Picture N>` | A concrete first frame, keyframe, last frame, edited keyframe, composition anchor, or storyboard anchor. |
| `<Video N>` | A whole source video used for editing, continuation, camera movement, cuts, rhythm, or temporal structure. |
| `<Audio N>` | A standalone audio signal used by copy or reference. |

Use `<Subject N>` for content extracted from an image or video. Do not create a separate `<Picture N>` or `<Video N>` entry when the asset merely supplies that subject and has no independent frame or structural role. Number each label family independently.

When one reference video supplies both video and audio, create `<Audio N>` only when its audio has an explicit copy or reference role. State shared provenance only when needed to prevent ambiguity.

Write one definition per tracked item. Name its source, role, and reference-critical attributes. When an audio reference maps to an actual speaker, reuse that speaker's global ID: `<Audio 1> is the voice-timbre reference for <Subject 1> (S1).`

### Summarize the task

Start `summary` with one bracketed combination of applicable task types, joined by ` + ` without duplicates:

- `keyframe completion`: an image is a concrete target-video frame.
- `reference generation`: an asset guides subject, scene, style, action, camera, or storyboard without being directly edited or continued.
- `video editing`: an existing video is directly modified.
- `video continuation`: new content continues an existing video.
- `audio reuse`: the same audio signal is copied in whole or part.
- `audio reference`: only timbre, content, texture, style, beat, or continuity is referenced.

Example prefix: `[video continuation + keyframe completion + audio reference]`.

Use only labels already defined in `subject_definitions`. For direct video editing, begin the paragraph after the prefix with `The target video is an edited version of <Video 1>.`

### Analyze retention

Write one line for every defined reference label and identify where it appears.

Use one of these fixed markers for visible content:

- `fully_preserved`: preserve the defined role completely.
- `partially_preserved`: retain the content while changing or omitting some defined attributes.
- `attribute_transfer`: transfer referenced attributes to a different identifiable target.
- `weak_reference`: retain only broad style, category, composition, or atmosphere.

Use one of these fixed markers for audio:

- `fully_copy`: reuse the complete source audio as the complete final track.
- `partially_copy`: copy only part of the timeline or selected layers, or modify the copied mix.
- `reference`: do not copy the signal; follow its timbre, rhythm, style, words, or sound texture.
- `weak_reference`: retain only a broad audio category or atmosphere.

Follow these patterns:

```text
<Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - ...
<Picture 1> ([Shot 1] first frame): fully_preserved - ...
<Video 1> (cut and pacing structure): weak_reference - ...
<Audio 1>: reference - ...
```

Judge retention against the role defined for that label. Newly added plot events or actions are not automatically losses of fidelity.

### Write the detailed timeline

Write `detailed_description` in playback order using the shared shot, camera, speaker, dialogue, and sound rules. Establish the overall style in one or two sentences before `[Shot 1]`. For generation tasks, target roughly 350–500 English words unless dialogue density or the user's requested brevity calls for a different length.

At the first clear appearance of a reference, state its relevant traits, frame position, and action. Reuse the same label later without redefining it. Cite frame anchors naturally, such as `the shot begins from <Picture 1>`, `the shot's keyframe corresponds to <Picture 2>`, or `the shot ends on <Picture 3>`.

When a referenced subject speaks, write `<Subject N> (Sx)`. If a verbal cue exists only inside directly reused music or a complete soundtrack, cite `<Audio N>` as the audible source and do not invent a speaker. For unintelligible reference speech, write `[unclear]` rather than guessing. When only a voice's timbre or delivery is referenced, do not copy the source dialogue unless the user requests it.

In `overall_soundscape` and `non_diegetic_music`, state an audio label's copy or reference relationship only in the matching audible layer. Keep complete dialogue and lyrics inside `<d>` in `detailed_description`.

## Final Checklist

Before returning the prompt, confirm every item:

- The selected mode matches the supplied assets and intended operation.
- The fields and sections are complete and in the required order.
- Every placeholder (`N`, `S.SS`, ellipses, or generic asset name) has been replaced.
- Shot numbers are sequential; timestamps increase and fit the total duration.
- Keyframe alignment reaches the supplied first and/or last frame at the correct instant.
- Every reference label is defined once, used consistently, and covered by retention analysis in Ref2VA.
- Speaker IDs are stable; dialogue, lyrics, and visible text preserve the source language and wording.
- Visual actions, camera behavior, diegetic sound, soundscape, and non-diegetic music do not contradict one another.
- Return only the finished H3 prompt. Add no explanation, mode announcement, Markdown code fence, or executor-specific state tag unless the caller explicitly requests it.
