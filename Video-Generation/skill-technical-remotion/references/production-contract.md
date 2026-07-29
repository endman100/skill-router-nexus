# Production Contract

Read this file before creating the project layout, timing schema, or delivery checklist.

## Input contract

Use a scene array with stable IDs:

```json
[
  {
    "id": "01",
    "chapter": "Definition",
    "caption": "One visual proposition",
    "text": "Approved display and caption wording.",
    "tts_text": "Optional pronunciation-only wording and Fish tags."
  }
]
```

Omit `tts_text` when it equals `text`. Never expose Fish tags or pronunciation aliases in captions.

## Canonical artifacts

| Artifact | Required contents |
|---|---|
| `voice.config.json` | provider, model, voice ID, reference paths and hashes, reference transcript, synthesis settings |
| `voice_manifest.json` | scene seeds, prompt IDs, segment hashes and durations, final WAV hash, fallback status |
| `final-narration.wav` | lossless mastered narration used by both Qwen and Remotion |
| `asr-listen-check.json` | model, audio hash, completeness and truncation checks, pronunciation notes |
| `qwen-forced-aligner-raw.json` | model, source media, audio hash, exact script, raw aligned units |
| `captions.json` | phrase text with start/end timestamps and frame ranges |
| `captions.srt` | portable captions derived from the same phrase timeline |
| `animation-cues.json` | scene ID, semantic cue name, timestamp, frame, matched script phrase |
| `timing.generated.json` | duration, audio hash, scene ranges, captions, and cue map consumed by Remotion |
| `caption-qc.json` | coverage, overlaps, fragments, reading speed, warnings, status |
| `sync-validation.json` | stream probes, start times, durations, hashes, cue provenance, decode result, failures |

## Timing rules

1. Hash the final WAV before Qwen processing.
2. Run unprompted Qwen ASR as a listen check; do not treat its transcript as approved copy.
3. Run Qwen ForcedAligner against the exact display script.
4. Preserve raw zero-duration items for audit, but derive safe phrase ends from adjacent valid boundaries.
5. Group aligned units into readable phrases without splitting English product names.
6. Resolve scene boundaries from speech timing plus explicit production pauses.
7. Resolve semantic cues by matching approved cue phrases in the aligned display script.
8. Store timestamps in seconds and derived frames; seconds remain authoritative when FPS changes.

For synthesized narration, target complete script coverage. Any unmatched meaningful phrase, missing scene, truncated ending, caption overlap, or unresolved cue is a failure.

## Remotion contract

- Use a single composition-wide audio element for `final-narration.wav`.
- Compute composition duration from final audio and a deliberate container tail allowance.
- Keep scene layout separate from caption layout.
- Drive semantic changes only from named cue frames.
- Render every scene at entry, mid-state, and final hold before the full MP4.
- Use supplied or generated images only when the storyboard explicitly requires them; geometric explainers should default to native HTML/CSS/SVG primitives.

## Delivery set

Deliver at minimum:

1. final MP4;
2. final lossless narration;
3. approved script;
4. SRT captions;
5. storyboard and cue map;
6. timing JSON;
7. voice manifest;
8. ASR listen-check and sync-validation reports;
9. representative stills or contact sheet;
10. reproducible source archive without `node_modules`, render cache, or temporary work directories.

## Verification thresholds

- final audio, raw alignment, derived timing, and delivered WAV hashes agree;
- audio and video streams begin at `0.000` seconds;
- video duration covers the full narration and only deliberate tail padding remains;
- output is 1920×1080 at 30 fps unless the user specifies otherwise;
- no caption overlaps or broken one-token fragments;
- no semantic cue uses a duplicated hardcoded frame literal;
- true peak does not exceed `-1.5 dBFS`;
- full MP4 decode exits successfully;
- source archive contains the composition, timing builder, voice configuration, and validation scripts, but no generated dependency tree.
