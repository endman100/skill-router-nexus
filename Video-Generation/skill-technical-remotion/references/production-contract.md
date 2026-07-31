# Production Contract

Read this file before creating the project layout, timing schema, or delivery checklist.

## Input contract

Use the approved script plus a canonical minimal `narration.json`:

```json
[
  {
    "text": "核准文字的第一個停頓單位，",
    "pause_after_ms": 280
  },
  {
    "text": "下一個停頓單位。",
    "pause_after_ms": 900
  }
]
```

Every object must contain exactly `text` then `pause_after_ms`. Do not add IDs, scene/page fields, captions, `tts_text`, file paths, seeds, hashes, or comments. Treat every deliberate audible pause as one item and retain its punctuation. For Traditional Chinese, the default deliberate boundaries are `，；：。！？`; `、` remains inside an item unless the editor explicitly approves physical silence there. The concatenated `text` values must reconstruct the approved script exactly after layout-only line breaks are removed.

Treat each `pause_after_ms` as a required minimum. When editorial pacing needs more time, keep the canonical file unchanged and create a separate `pacing-overrides.json`:

```json
{
  "schema_version": 1,
  "policy": "minimum-plus-editorial-extra",
  "max_extra_pause_ms": 600,
  "units": [
    {"unit_index": 4, "extra_pause_ms": 180, "reason": "mechanism-comprehension"}
  ]
}
```

Every addition must be non-negative, bounded, selective, and justified. The effective physical silence is `pause_after_ms + extra_pause_ms`; an override can never reduce or replace the canonical minimum.

Keep non-canonical information separate:

- `scenes.json`: page ID, chapter, summary caption, and contiguous one-based narration-unit ranges;
- `pronunciation-overrides.json`: one-based `unit_index` plus pronunciation-only `tts_text`;
- generated production manifest: disposable IDs, scene fields, paths, seeds, and hashes required by downstream tools.

The selected-WAV assembly manifest must map each source unit once with `id`, contiguous one-based `unit_index`, `path`, and optional derived `page_id`. It must not duplicate `text` or `pause_after_ms`; the assembler reads both only from canonical `narration.json`.

Run `scripts/prepare_minimal_narration.py validate` before materializing metadata or calling TTS. Run `scripts/materialize_narration_manifest.py` to create derived metadata. Never edit a generated manifest as the source of truth.

## Canonical artifacts

| Artifact | Required contents |
|---|---|
| `narration.json` | only canonical `text` and required integer `pause_after_ms` per deliberate pause unit |
| `pacing-overrides.json` | optional one-based unit index, non-negative editorial addition, reason, and maximum addition policy |
| `scenes.json` | contiguous scene/page ranges and visual labels, separate from canonical wording |
| `pronunciation-overrides.json` | optional TTS-only aliases keyed by one-based narration-unit index |
| `voice.config.json` | provider, model, voice ID, reference paths and hashes, reference transcript, synthesis settings, pause policy |
| `voice_manifest.json` | sentence seeds, prompt IDs, segment hashes and durations, pause policy, final WAV hash, fallback status |
| `candidate_selection_manifest.json` | all sentence candidates, Qwen3 transcripts, pronunciation comparison, mean token log-probability, selected winner |
| `final-narration.wav` | lossless mastered narration used by both Qwen and Remotion |
| `pause-timing.json` | sentence/page IDs, segment ranges, physical silence ranges, page-gap visual allocation, final WAV hash |
| `asr-listen-check.json` | model, audio hash, completeness and truncation checks, pronunciation notes |
| `qwen-forced-aligner-raw.json` | model, source media, audio hash, exact script, raw aligned units |
| `captions.json` | phrase text with start/end timestamps and frame ranges |
| `captions.srt` | portable captions derived from the same phrase timeline |
| `animation-cues.json` | scene ID, semantic cue name, timestamp, frame, matched script phrase |
| `visual-animation-cues.json` | canonical time, visual time, lead seconds, derived frame, and renderer policy source |
| `sentence-animation-map.json` | one record per derived narration-unit ID with scene ID, semantic target, visible motion/state change, and aligned timing source |
| `sentence-animation-qc.json` | expected unit IDs, mapped unit IDs, duplicates, orphans, coverage ratio, and pass/fail status |
| `visual-semantic-qc.json` | one manually reviewed record per narration unit with narration, intended meaning, observed before/after change and evidence, asset relevance, reviewer note, and pass/fail status |
| `stills-manifest.json` | exact frame numbers, labels, evidence paths and hashes decoded from the candidate final MP4, plus that MP4's SHA-256 |
| `filmstrip-manifest.json` | contiguous per-scene decoded review ranges, sample rate of at least 2 fps, filmstrip paths and hashes, plus the reviewed MP4's SHA-256 |
| `official-assets.json` | official source page and direct URL, retrieval date, local derivative, trim/transform, byte count, SHA-256, `why_this_asset`, `explained_by_sentence_ids`, `visible_window_sentence_ids`, and `visible_label` |
| `motion-stability-qc.json` | contiguous 1× review ranges plus layout-shift, alternating-entry, bounce, flicker, and loop findings |
| `timing.generated.json` | duration, audio hash, scene ranges, captions, canonical cues, visual cues, and page-gap allocation consumed by Remotion |
| `caption-qc.json` | coverage, overlaps, fragments, reading speed, warnings, status |
| `sync-validation.json` | stream probes, start times, durations, hashes, cue provenance, decode result, failures |

## Timing rules

1. Validate that `narration.json` has exactly two keys per item, has no internal deliberate pause boundary, and reconstructs the approved script.
2. Validate `scenes.json` covers every one-based narration-unit index exactly once and `pronunciation-overrides.json` refers only to valid units.
3. Materialize stable production IDs and scene metadata without changing the canonical file.
4. Generate one lossless WAV per pause unit. When quality selection is enabled, generate three candidates per unit. Run `Qwen/Qwen3-ASR-1.7B`, reject candidates that fail normalized-pronunciation equivalence, then rank survivors by Qwen mean token log-probability. Never use Whisper for this gate.
5. Run `tts-skill/scripts/assemble_pcm_narration.py` with the minimal narration, selected-WAV manifest, and optional `pacing-overrides.json`. Add every required integer `pause_after_ms` plus the recorded non-negative editorial addition as real PCM silence. Store required, extra, effective, and reason fields for every unit. Page-gap and tail minima are already encoded in their applicable items; never infer a missing pause or add either gap twice. Allocate a page-ending addition only to the completed-page hold.
6. Hash the assembled final WAV and store the same hash in `pause-timing.json` before Qwen processing.
7. Run unprompted Qwen3 ASR as a listen check; do not treat its transcript as approved copy.
8. Run Qwen ForcedAligner against the exact display script.
9. Preserve raw zero-duration aligned items for audit, but derive safe phrase ends from adjacent valid boundaries.
10. Group aligned units into readable phrases without splitting English product names; emit no caption during a deliberate silence gap.
11. Resolve scene boundaries from `scenes.json`, aligned speech, and physical pause ranges in `pause-timing.json`.
12. Resolve canonical semantic cues by matching approved cue phrases in the aligned display script.
13. Derive a separate visual cue map from canonical cues. Default to 0.60-second title lead, 0.45-second regular lead, and 0.30-second late-emphasis lead. Keep every actual semantic lead within 0.30–0.60 seconds after scene-start clamping.
14. Store timestamps in seconds and derived frames; seconds remain authoritative when FPS changes.
15. Build one sentence-animation record for every minimal narration item. A record must identify the visible semantic element or state change and derive its trigger from the aligned unit or canonical cue. Do not count captions, global progress, ambient loops, or page transitions as the unit's sole animation.
16. Use independently rendered stills only for iteration. Render and decode a low-resolution complete preview, create contiguous per-scene filmstrips at no less than 2 fps with `scripts/build_motion_review.py`, and watch the preview or per-scene clips at 1×.
17. After rendering the candidate final MP4, use `scripts/extract_review_stills_from_video.py` to decode the before/after pair for every narration unit plus representative states and cue boundaries from that exact MP4. Record its SHA-256 in `stills-manifest.json`; do not substitute browser-rendered stills as final evidence.
18. Manually review every final-MP4 pair. Coverage alone does not prove semantic agreement. Record the intended meaning, observed change, evidence paths and hashes, asset IDs and relevance, reviewer note, and pass/fail result in `visual-semantic-qc.json`; a negative statement visualized as a positive capability, unexplained asset, unrelated content, or empty shell fails.

For synthesized narration, target complete script coverage. Any unmatched meaningful phrase, missing scene, truncated ending, caption overlap, or unresolved cue is a failure.

## Remotion contract

- Resolve the delivery format before layout. A Short, Reel, TikTok-style introduction, or comparable short-form social explainer defaults to 1080×1920 (9:16); use landscape only when explicitly requested.
- Reflow the actual composition for portrait. Do not letterbox, crop, or merely scale a 16:9 canvas into a 9:16 wrapper.
- Use a single composition-wide audio element for `final-narration.wav`.
- Compute composition duration from final audio and a deliberate container tail allowance.
- Allocate the required 0.90-second page-gap minimum as at least 0.15 seconds of completed-page hold, 0.45 seconds of transition, and 0.30 seconds of next-page pre-roll. Add any editorial page-ending extra to the completed-page hold while keeping transition and pre-roll fixed.
- Finish the next page's entry animation before its first sentence begins.
- Make adjacent scenes visually cover their cut. Use a hard cut, an actually overlapping crossfade, or persistent chrome/background; never combine an outgoing fade and a non-overlapping incoming fade into an unintended near-black interval.
- Keep scene layout separate from caption layout.
- Drive semantic changes only from named visual cue frames derived from canonical Qwen cues.
- Drive at least one visible, semantically related animation or diagram state change for every narration unit recorded in `sentence-animation-map.json`.
- Keep recurring regions fixed. Prefer mask reveals, fills, path drawing, highlight, blur-to-clear, crop changes, or motion inside a fixed viewport. Do not satisfy coverage with alternating card entrances, repeated panel relocation, warning shake, scale pulse, or low-damping bounce.
- No asset quota applies. Put an official image or muted source-video excerpt inside a stable preview viewport only when mapped narration explicitly explains it; bound its visibility to `visible_window_sentence_ids`, label it as an official/source reference, render from a local deterministic copy, and validate it against `official-assets.json`. Provenance does not establish semantic relevance.
- Keep captions on canonical Qwen timing; visual anticipation must never shift subtitle or narration timestamps.
- Render a low-resolution full preview first, decode it, watch it or contiguous per-scene clips at 1×, and generate per-scene filmstrips at no less than 2 fps. After the final render, regenerate sentence before/after and cue-boundary evidence by exact frame selection from that MP4. Treat the final MP4 as the source of truth if browser stills disagree. Record the evidence and motion findings in `stills-manifest.json`, `filmstrip-manifest.json`, `visual-semantic-qc.json`, and `motion-stability-qc.json`.
- Use supplied or generated images only when the storyboard explicitly requires them; geometric explainers should default to native HTML/CSS/SVG primitives.

## Delivery set

Deliver at minimum:

1. final MP4;
2. final lossless narration;
3. approved script;
4. minimal `narration.json`, `scenes.json`, and pronunciation overrides;
5. SRT captions;
6. storyboard, canonical cue map, and visual cue map;
7. timing JSON;
8. voice manifest;
9. ASR listen-check and sync-validation reports;
10. final-MP4 exact-frame still manifest, representative contact sheets, and per-scene motion filmstrips;
11. sentence-animation map, coverage QC, and per-unit visual semantic audit;
12. pacing overrides, official-asset provenance and relevance, and motion-stability QC when used;
13. reproducible source archive without `node_modules`, render cache, or temporary work directories.

## Verification thresholds

- final audio, raw alignment, derived timing, and delivered WAV hashes agree;
- `narration.json` contains only `text` and `pause_after_ms`, contains one item per deliberate pause, and reconstructs the approved script;
- `pause-timing.json` matches the final WAV hash and records every required `pause_after_ms`, non-negative addition, effective silence, and reason exactly once, including page-gap and final-tail minima;
- every selected pause-unit candidate passes normalized-pronunciation equivalence and wins by Qwen confidence among passing candidates;
- audio and video streams begin at `0.000` seconds;
- video duration covers the full narration and only deliberate tail padding remains;
- Short output is 1080×1920 at 30 fps unless the user explicitly specifies another orientation; non-Short output follows the requested delivery format;
- sentence-animation coverage equals `1.0`, mapped IDs equal all derived narration-unit IDs, and duplicates/orphans are empty;
- `visual-semantic-qc.json` covers every derived narration-unit ID exactly once and every record passes; observed changes agree with narration, negative statements are not inverted into positive capabilities, and no reviewed frame contains an unrelated asset or empty shell;
- `stills-manifest.json` is decoded from the candidate final MP4, its video SHA-256 equals the delivered MP4, and every narration unit has ordered, non-identical before/after evidence;
- `filmstrip-manifest.json` covers every scene contiguously at no less than 2 fps and its video SHA-256 equals the delivered MP4;
- no caption overlaps or broken one-token fragments;
- no semantic cue uses a duplicated hardcoded frame literal;
- every non-page-enter visual cue leads its canonical cue by 0.30–0.60 seconds;
- every renderer page-gap allocation uses a completed-page hold of at least 0.15 seconds plus fixed 0.45-second transition and 0.30-second pre-roll, and exactly fits that page's effective physical silence;
- motion-stability QC confirms no recurring alternating entrance, large panel relocation, bounce, flicker, or abrupt media loop during watched 1× ranges;
- full-video FFmpeg `blackdetect=d=0.5` reports no unintended interval; inspect any match with a local 10 fps contact strip and fix compounded scene fades or document a genuinely intentional blackout;
- all imported official assets match `official-assets.json`, are explicitly explained by mapped narration, remain inside their bounded visible windows, have a recorded semantic-relevance decision, keep source video muted, and show visible source labels;
- visual-only rebuilds preserve final narration WAV and SRT SHA-256 values;
- true peak does not exceed `-1.5 dBFS`;
- full MP4 decode exits successfully;
- the copied delivery MP4 SHA-256 equals the verified source render SHA-256;
- source archive contains the composition, timing builder, voice configuration, and validation scripts, but no generated dependency tree.
