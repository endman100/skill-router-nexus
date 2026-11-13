---
name: minimax-h3-dance-mv
description: >-
  Plan, write, review, or revise MiniMax H3 dance music-video prompt packs from
  supplied music and visual references. Use for choreography, synchronized body
  and camera timelines, independent audio-sliced segments, and dance-MV QA.
  For generic H3 field syntax or running the Ref2VA rewriter, use the related skills.
---

# MiniMax H3 Dance MV

A compact reference wrapper for AI Dance Paradise (@LoveUolanda)'s dance-MV
production method. Use it to turn a song into complete movement phrases and
independently usable segment prompts, or diagnose weak dance footage. Prompt
planning alone does not request video generation.

Related: [H3 prompt syntax](../h3-prompt-writing/SKILL.md), [Ref2VA rewriter operation](../minimax-h3-prompt-rewriter-ref2va/SKILL.md), [narrative storyboarding](../h3-storyboard/SKILL.md).

## Original source and access

- Author: AI Dance Paradise, [@LoveUolanda](https://x.com/LoveUolanda).
- Original public method: [H3_Dance_MV_Production_Skill_Rev1.0.md](https://github.com/LoveRain1997/h3-prompt-journal/blob/main/case-studies/2026-11-dance-mv-production-skill/H3_Dance_MV_Production_Skill_Rev1.0.md), Rev.1.0, 2026-11-05, in the author's `LoveRain1997/h3-prompt-journal` repository.
- Obtain the full method by opening that file and selecting **Raw / Download**, or reading [the raw Markdown](https://raw.githubusercontent.com/LoveRain1997/h3-prompt-journal/main/case-studies/2026-11-dance-mv-production-skill/H3_Dance_MV_Production_Skill_Rev1.0.md). It is a production-method document without skill frontmatter, rather than a packaged `SKILL.md` installation.
- Corresponding [X article](https://x.com/LoveUolanda/status/2118383132206604739), posted 2026-11-05. This wrapper paraphrases the public method; consult the original for dance-style vocabularies, technical movement stages, and longer examples. No upstream assets are bundled.

## Workflow

Music structure → MV concept → visual motif → dance vocabulary → action chains
→ body mechanics → camera path → shots → transition hooks → complete segment
prompts → generation review → targeted revision.

1. Inventory actual images, audio, lyrics, beat data, cut manifests, and any
   available movement library. Record required elements and exclusions; inspect
   assets rather than inferring their contents from filenames.
2. Verify duration, BPM, beat/bar/phrase lengths, first-downbeat offset, musical
   sections, breaks, and vocal events. Beat length is `60 / BPM`; calculations
   do not establish unmeasured musical events. Prefer a verified cuts manifest.
3. Choose the MV type, principal dance style, visual motif, cast, and fixed
   visual world. Map the song's energy curve before selecting movements.
   Lyrics inform mood and theme, not an obligatory sequence of props or mime.
4. Split at phrases or natural action releases, then design each segment's
   groove, principal chain, optional accents, movement route, and end state.
   Avoid severing a technical move; musical structure takes priority over equal lengths.
5. Give body and camera one LOCAL timeline: preparation, onset, expansion,
   peak, and recovery. Select shot coverage and one main editorial mechanism
   per boundary, then write every segment fully.
6. Audit before generation; score actual outputs afterward. Diagnose assets,
   timing, choreography, camera, continuity, or wording before blaming randomness.
   Fix the affected layer while preserving correct settings, then recheck
   duration, audio boundaries, and neighboring transitions.

## Operating rules

- **Complete dancing:** combine sustained groove, an action chain, and small
  expressive accents. State entry posture, supporting foot and weight, force
  source, path, main visible result, inertia, braking/recovery, and next entry.
  Connect states without resetting to neutral after every move. Modern groove
  and classical breath/sleeve mechanics need distinct movement vocabularies.
- **Density:** describe everyday actions briefly; specify support, timing, and
  recovery for standard chains; give jumps, turns, and floor work their complete
  technical stages. Fast music needs energy, not a new independent move on every
  beat. Reduce competing actions when a time window cannot contain them.
- **Physical camera:** specify placement, height, distance, optical axis,
  foreground/background relationship, visible consequence, path, and stopping
  condition. Prefer physical relationships over abstract angle names or degree
  numbers. True overhead means directly above and perpendicular to the floor.
  Prepare the framing before a major accent; synchronize movement peaks and
  recovery. Show support, footwork, turns, and landings with adequate full-body
  coverage; avoid prolonged orbiting around a motionless dancer.
- **Segment length:** aim for about **10–15 seconds**, subject to the actual
  task and platform limit. The author's recent example used 18 independent
  segments of roughly 11–14 seconds. Do not force these counts onto other songs.
- **Reference roles:** declare actual supplied inputs and conflict priorities.
  The four-image example assigns Picture 1 to identity/outfit, Picture 2 to
  composition/camera language, Picture 3 to blocking/routes, and Picture 4 to
  the real environment. Pictures 2–3 must not import their people or locations;
  routes must fit Picture 4. Three-image and single-image projects need their own
  explicit mapping; one image may lock identity, environment, or both.
- **Prop ledger:** record each permitted prop's source, count, position, first
  and last appearance, handling permissions, and continuity. Preserve the
  referenced costume and environment; do not invent objects from lyrics.
- **Audio slices:** supply only the matching slice as `<Audio 1>` for each
  segment. Match output duration to it; preserve vocals, instruments, tempo,
  dynamics, and timing. Request no replacement, restart, loop, retiming, extra
  music, dialogue, or physical/ambient sounds unless explicitly wanted.
- **Time and speech:** GLOBAL time belongs in the production index; each H3
  shot uses LOCAL time starting at `00:00.000`. Record original offset, slice
  filename, local duration, and musical location outside the executable prompt.
  Singing remains soundtrack unless lip-sync is requested. Actual spoken lines
  retain their language inside `<d>[Language] ...</d>` and need stable, readable
  faces; do not confuse vocals with spoken dialogue.
- **Independent prompts:** repeat all necessary identity, costume, environment,
  reference-role, cast, aspect-ratio, duration, and audio rules in every segment.
  Never substitute “same as above.” Use English execution prose; omit internal
  movement-library IDs. Design cross-segment matches through direction, shape,
  action phase, or existing foreground occlusion; do not assume inherited frames.

## Short prompt skeleton

This condenses the author's directing skeleton, not an API schema. If an executor
requires strict Ref2VA fields, place these decisions in its supported structure;
the related syntax skill covers that translation. Replace placeholders and omit
unprovided labels in the actual prompt.

```text
Create [duration] seconds of [aspect ratio] dance-MV footage.
LOCAL clock starts at 00:00.000; preserve supplied <Audio 1>.
SUBJECT DEFINITIONS: <Subject 1> [identity source and cast]
REFERENCE ROLES: [supplied Picture labels, roles, priorities]
GLOBAL CONTINUITY AND VISUAL LOCK: [outfit, environment, props]
MUSIC AND PERFORMANCE RULES: [dance style, groove, vocal rules]
DIRECTING CONCEPT: [one sentence]
ACTION AND CAMERA TIMELINE — LOCAL TIME:
[start–end] SHOT 01: [purpose, physical viewpoint, framing]
[support → force → path → peak → recovery → next entry]
[camera onset, path, peak framing, recovery on the same clock]
[CUT only where motivated; repeat for subsequent shots]
END STATE / EDITORIAL HOOK: [body state, direction or shape]
overall_soundscape: Preserve <Audio 1>; no unrequested sounds.
non_diegetic_music: <Audio 1> only; no restart or alteration.
```

## QA and revision

Before generation, verify audio/timing evidence, reference responsibilities,
visual locks and ledger, style and chain completeness, movement capacity,
full-body coverage, physical camera synchronization, motivated cuts, standalone
prompt completeness, language, and audio fidelity.

After generation, score **each of these ten items from 1–5**: 1 = clear failure,
3 = broadly usable with defects, 5 = meets the stated target. The author gives
no overall passing-score threshold.

| Item | Target for 5 |
| --- | --- |
| 1. Character consistency | Identity, face, costume, and cast stay stable. |
| 2. Scene consistency | Layout, colors, lighting, and permitted objects remain stable. |
| 3. Rhythm synchronization | Onsets, peaks, and recoveries follow the actual music. |
| 4. Action completeness | Principal phrases finish naturally rather than loop or pose. |
| 5. Physical credibility | Support, weight, contact, and inertia are convincing. |
| 6. Dance style | Movement logic clearly expresses the chosen style. |
| 7. Camera quality | Physical paths have purpose and synchronize with movement. |
| 8. Shot readability | Important footwork, mechanics, and visual accents are visible. |
| 9. Transition value | Adjacent segments offer clear editable matching points. |
| 10. Commercial finish | The sequence conveys deliberate direction and rhythmic design. |

For example, repair missed footwork through shot coverage, late camera movement
through earlier preparation, and repeated swaying through a complete weight-shifting
chain. Prefer specific positive paths and reduced overload over accumulating negatives.

## Limits

The numerical guidance is the author's empirical production baseline, not a
universal model constraint. The source reports the author's own works, including
*Index's Morning Trouble* and classical-dance projects, without controlled
experiments or quantified success rates. Their images, verified audio cuts,
manifests, and movement libraries affect reproducibility; do not assume those
assets or the cited library revision are available. Prompt instructions express
targets, not guarantees of exact beat alignment, unchanged audio, or continuity.
