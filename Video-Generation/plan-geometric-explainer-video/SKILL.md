---
name: plan-geometric-explainer-video
description: Plan, storyboard, and implement source-independent 16:9 geometric motion-graphics explainers in Remotion from technical, educational, or science narration. Use when converting abstract ideas into cards, flows, comparisons, hierarchies, state changes, modular diagrams, subtitles, and narration-driven animation cues. Work only from the current task's script, final audio, timing data, and supplied production assets; do not require or retrace external videos, creators, channels, URLs, timecodes, or provenance corpora.
---

# Plan Geometric Explainer Video

Turn narration into a restrained geometric scene system, then implement it as deterministic Remotion animation.

## Keep the workflow source-independent

1. Use only the script, final narration audio, timing artifacts, brand rules, and production assets supplied for the current task.
2. Do not browse for, reopen, identify, or retrace an earlier video, creator, channel, timestamp, or design corpus.
3. Treat links mentioned in prior conversation as historical context, not required inputs.
4. Do not create evidence IDs, provenance ledgers, comparison atlases, or citations for the visual grammar.
5. If the current request explicitly asks to analyze a new reference, use a dedicated reference-analysis workflow outside this skill. Return here only after the user approves a source-independent design specification.

Run the portability gate after editing this skill or copying its assets:

```bash
python scripts/validate_portability.py
```

## Load only the needed guides

- Read `references/story-to-geometry.md` before choosing a diagram family.
- Read `references/visual-grammar.md` when defining layout, type, color, density, and caption treatment.
- Read `references/motion-grammar.md` when defining entrances, state changes, emphasis, and exits.
- Read `references/remotion-implementation.md` before writing or changing Remotion code.
- Read `references/voice-production.md` whenever narration must be generated or replaced.
- Reuse the generic components under `assets/remotion-primitives/` when they fit the scene.

## Follow the production workflow

### 1. Lock the content spine

Require a narration script, transcript, or chapter outline. Split it into meaning beats and assign each beat one primary job:

- identify or define;
- enumerate;
- show sequence or causality;
- compare;
- show hierarchy or containment;
- show state change, failure, or recovery;
- demonstrate with a supplied UI or asset;
- summarize or conclude.

Do not select shapes until the beat has one primary job.

### 2. Establish the canonical clock

When final narration audio exists, use it as the only production clock.

- When narration must be generated, use the default Fish Audio S2 Pro voice profile in `references/voice-production.md` unless the user explicitly selects another voice.
- Align the exact display script to word or phrase timestamps from the final audio.
- Preserve the original script for captions; use ASR only to obtain timing.
- Store one canonical caption timeline and derive scene cues from it.
- Trigger semantic animation with named cue timestamps, not estimated character counts or duplicated frame literals.
- Permit duration estimates only in an explicitly labeled scratch preview.

### 3. Map story beats to geometry

Use `references/story-to-geometry.md`. Prefer one dominant structure per scene. Keep geometry stable while the narration describes a state change; replace the scene when the conceptual model changes.

Record each scene as:

```text
scene_id | narration range | semantic job | diagram family | cue keys |
neutral state | triggered changes | final hold | exit | production notes
```

### 4. Build the storyboard around named cues

For every scene, specify:

1. the neutral starting frame;
2. the first readable state;
3. every cue-triggered change;
4. the final held state;
5. the exit or transition;
6. any required user-supplied image or UI asset.

Name the changing property: opacity, position, scale, connector length, border color, fill color, progress width, or group arrangement. Do not write vague directions such as “make it dynamic.”

### 5. Establish visual tokens

Start from `references/visual-grammar.md`, then apply user brand constraints. Keep semantic color roles stable across scenes. Measure long text before fixing card dimensions.

### 6. Implement deterministically in Remotion

- Drive authored animation from `useCurrentFrame()` and `useVideoConfig()`.
- Express timing in seconds or named cues, then convert to frames with the composition FPS.
- Use `<Sequence>` or `<Series>` for scene timing and premount media-heavy sequences.
- Use `interpolate()` for controlled state changes and `spring()` for short settling entrances.
- Do not use CSS animations or CSS transitions.
- Keep one top-level final narration audio track beginning at frame zero.
- Keep captions independent from diagram layout.
- Load local fonts before rendering and use `<Img>` with `staticFile()` for local images.

### 7. Review with stills before rendering

Render entry, midpoint, and final-hold stills for every scene. Check:

- alignment and safe margins;
- information density;
- text hierarchy, wrapping, and overflow;
- primitive count and grouping;
- semantic color states;
- whether the intended state change is understandable without narration;
- whether cue-triggered changes occur after the matching spoken phrase begins.

### 8. Verify the final video

Require all of the following before delivery:

- `python scripts/validate_portability.py` passes;
- every semantic animation start resolves from the canonical cue timeline;
- caption alignment and overlap checks pass;
- representative stills contain no clipped or overflowing content;
- the Remotion typecheck and render exit successfully;
- the final video and audio both start at zero;
- video duration covers the final narration duration;
- FFmpeg decodes the complete output without errors.

## Return this deliverable set

Produce:

1. a semantic storyboard;
2. a visual token sheet;
3. a cue-to-animation map;
4. canonical caption and animation timing artifacts;
5. a Remotion scene/component map;
6. representative stills;
7. the rendered video and validation report when implementation is requested.

Do not include a source ledger, reference atlas, creator analysis, URL list, timestamp citations, or comparison frames in the handoff.
