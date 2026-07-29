# Remotion implementation

Read `story-to-geometry.md`, `visual-grammar.md`, and `motion-grammar.md` first.

## Composition architecture

```text
ExplainerComposition
├─ Audio final narration from frame 0
├─ SurfaceCanvas
├─ VideoChrome phase state
├─ SceneStage scene spec + state timeline
└─ CaptionTrack canonical caption cues
```

## Canonical timing contract

Use the exact final narration audio as the only clock. Keep these machine-readable artifacts together:

```text
captions_words.json  word or character timestamps aligned to the display script
captions.json        grouped phrase captions
captions.srt         portable subtitle export
animation-cues.json  named semantic cue timestamps
timing.generated.json renderer-ready scene and cue frames
```

Preserve the authored script for display. Use ASR or forced alignment only to locate its words in the final audio. Reject character-count interpolation for final delivery.

## Deterministic animation rules

- Use `useCurrentFrame()` and `useVideoConfig()` for every authored change.
- Convert seconds to frames with the composition FPS; do not assume a fixed FPS in reusable data.
- Use `<Sequence>` or `<Series>` for scene timing and premount sequences that contain images or fonts.
- Use `interpolate()` or `interpolateColors()` for controlled state changes.
- Use `spring()` for short settling entrances, not uncontrolled decorative motion.
- Do not use CSS animations or transitions.
- Put connectors in an SVG layer behind cards.
- Use `<Img src={staticFile(...)} />` for local assets and await fonts before rendering.
- Keep captions in a separate track so caption length never changes diagram layout.
- Place one canonical narration `<Audio>` at frame zero. Do not attach duplicate audio to scenes.

## Cue lookup

Keep cue conversion in one helper instead of scattering frame literals through JSX:

```ts
type AnimationCue = {
  name: string;
  time: number;
};

const cueFrame = (cues: AnimationCue[], name: string, fps: number) => {
  const cue = cues.find((item) => item.name === name);
  if (!cue) throw new Error(`Missing animation cue: ${name}`);
  return Math.round(cue.time * fps);
};
```

## Scene data model

Prefer state timelines over scattered JSX frame literals:

```ts
type VisualState = 'inactive' | 'active' | 'error' | 'success' | 'dimmed';

type TimedState = {
  cue: string;
  state: VisualState;
};

type SceneSpec = {
  id: string;
  from: number;
  durationInFrames: number;
  layoutFamily: 'left' | 'center' | 'compare' | 'pipeline';
  states: TimedState[];
};
```

## Component map

| Component | Responsibility |
|---|---|
| `VideoChrome` | progress rail and chapter marker |
| `CaptionTrack` | independent bottom caption capsule |
| `HeadlineBlock` | inline semantic color and optional underline |
| `StepPipeline` | scaffold, ordered activation, error or success state |
| `ModuleGrid` | loose tiles settling into a grid |
| `CompareColumns` | first side, second side, then result |
| `Panel` / `WindowPanel` | supplied product, terminal, browser, or report UI |
| `NodeGraph` | nodes first, connectors behind |
| `MappingRows` | append rows without rearranging prior rows |
| `VerdictOverlay` | dim completed scene, then show a callout |
| `IllustrationHero` | replace the scene stage at a metaphor or chapter beat |

The files under `assets/remotion-primitives/` are generic starting components. Replace demo text and connect their animation starts to named cues before production use.

## Still-first and sync review

Render entry, midpoint, and final-hold stills for every scene. Check safe margins, text overflow, grouping, semantic state, and caption independence.

For each animation cue, render a still immediately before and after the cue. Confirm that the matching spoken phrase begins at the cue timestamp and that the visual change is apparent after it. Then render the complete composition and decode it once with FFmpeg.
