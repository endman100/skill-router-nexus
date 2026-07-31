---
name: skill-technical-remotion
description: Use when a finalized narration script must become a stable-layout Remotion or HTML/PPT-style explainer video and the user requires a strict pause-unit narration JSON, Qwen3-TTS voice cloning with minimum-plus-editorial pacing, Qwen word-level synchronization, accurate subtitles, official technical preview assets, one visible semantic animation per narration unit, or a 9:16 vertical technical Short.
---

# Skill Technical Remotion

## Overview

Build source-independent explainer videos from one approved script, one strict minimal narration JSON, and one canonical final narration WAV. Generate and select audio first, derive captions and canonical semantic cues from Qwen timestamps, derive a separate speech-anticipating visual-cue layer, then render and verify the Remotion composition.

## Keep article writing outside this skill

- Accept an approved script, transcript, or structured narration as the production input. Do not silently rewrite approved wording.
- When the request is a concise Traditional Chinese Short introduction for an AI model, software feature, developer tool, or other technology and no approved script exists, **REQUIRED CONDITIONAL SUB-SKILL:** use `skill-writing-technical-shorts` for the article. Resume this skill only after that script is complete.
- For other article formats, use the writing skill selected for that format. Do not copy writing formulas into this skill.
- Keep research citations outside spoken narration. Preserve the display script and minimal narration separately from TTS-only pronunciation aliases and provider-specific control text.

## Required production skills

- **REQUIRED SUB-SKILL:** use `tts-skill` whenever narration must be generated or replaced. Its configured Qwen3-TTS VoiceClone profile is the default unless the user explicitly overrides it.
- **REQUIRED SHORT SUB-SKILL:** use `remotion-video-creation` for Remotion implementation rules whenever the output is a Short. A Short defaults to 1080×1920 (9:16); do not let a landscape template or sub-skill override that format.
- **REQUIRED LANDSCAPE SUB-SKILL:** use `plan-geometric-explainer-video` only for non-Short landscape explainers that need its 16:9 geometric grammar. Do not route a Short through its 16:9 output contract.
- **REQUIRED COMPLETION SKILL:** use `verification-before-completion` before declaring the video finished.

Read `../../TTS-and-Voice-AI/tts-skill/references/qwen3-default-voice.json` before using the default voice. Use the complete 17.28-second lossless full-prompt FLAC declared by that profile with its exact transcript and `x_vector_only=false`. Verify its hash, audio format, duration, model, and ComfyUI node before synthesis. Do not transcode, trim, denoise, or substitute the reference.

Do not reopen historical motion-reference videos merely to imitate another creator's style. Current official product or research assets requested for technical evidence are allowed only through the provenance workflow below; otherwise work from the current script, final audio, timing artifacts, brand rules, and supplied production assets.

## Production workflow

1. **Lock the display script and build the minimal narration.** Run `scripts/prepare_minimal_narration.py build`, then `validate`, before any TTS call. `narration.json` must be a non-empty array whose objects contain exactly `text` then `pause_after_ms`; no IDs, page fields, captions, `tts_text`, paths, seeds, or hashes are allowed. Make every deliberate audible pause one `text` item, retain the boundary punctuation, and allow no deliberate pause inside an item. For Traditional Chinese, split at `，；：。！？`; keep the enumeration mark `、` inside the item unless the editor explicitly wants physical silence there. Concatenating all `text` values must reproduce the approved script exactly after removing layout-only line breaks.
2. **Separate production metadata.** Store scene/page ranges and labels in `scenes.json`; store pronunciation-only wording in `pronunciation-overrides.json`. Run `scripts/materialize_narration_manifest.py` to derive disposable stable IDs, page metadata, and TTS aliases for legacy consumers. Never edit the derived manifest or copy its fields back into `narration.json`.
3. **Generate pause-unit candidates.** Use `tts-skill` to render one lossless WAV for every minimal narration item. For a quality-selected run, generate three candidates per pause unit with the approved voice recipe and distinct recorded seeds. Keep Traditional Chinese TTS input unless the user explicitly approves another pronunciation strategy.
4. **Select by pronunciation, then confidence.** Run unprompted `Qwen/Qwen3-ASR-1.7B`; do not use Whisper. First reject any candidate whose normalized pronunciation differs from its approved pause unit. For Chinese, compare normalized Pinyin syllable sequences while preserving canonical Latin/product-name tokens. Among pronunciation-equivalent candidates, select the highest Qwen mean token log-probability. Record every candidate, transcript, pronunciation result, score, seed, and winner in `candidate_selection_manifest.json`.
5. **Assemble deterministic but editorial pacing.** Treat every integer `pause_after_ms` in minimal `narration.json` as a mandatory minimum. Run `assemble_pcm_narration.py` with the selected unit WAV manifest and, when useful, a separate `pacing-overrides.json` whose records contain one-based `unit_index`, non-negative `extra_pause_ms`, and a concrete editorial reason. Compute effective silence as required minimum plus the addition; never shorten or replace the canonical value. Use additions selectively for difficult concepts, emphasis, official-preview reading, completed-scene holds, or the closing breath, not uniformly after every item. Encode page-gap and tail minima in their applicable narration items, allocate any page-ending addition to the completed-page hold, and never add a second global gap. Master one final WAV and record required, extra, effective, reason, reference hashes, seeds, output hash, and `used_fallback=false`.
6. **Listen before aligning.** Run unprompted Qwen3 ASR against the final WAV. Regenerate only defective pause-unit candidates, rebuild the final WAV, and repeat the listen check. Lock the audio after content and ending completeness pass.
7. **Force-align the locked audio.** Run `Qwen/Qwen3-ForcedAligner-0.6B` with the exact display script. Use ASR only for timing; never replace approved product names or English tokens with recognition text.
8. **Build canonical and visual timing layers.** Produce `pause-timing.json`, phrase captions, SRT, scene ranges, and named canonical animation cues from the locked WAV and aligned units. Keep canonical cue timestamps speech-aligned. Derive `visual-animation-cues.json` separately: lead titles by 0.60 seconds, regular semantic cues by 0.45 seconds, and late emphasis/warning cues by 0.30 seconds. Clamp only at scene start and require every semantic cue's actual lead to remain within 0.30–0.60 seconds. Store the final-audio SHA-256 in raw and derived timing artifacts. Do not infer semantic timings from character count, scene percentages, fixed delays, or raw TTS segment lengths.
9. **Build sentence-animation coverage.** Treat each minimal narration item as the enforceable sentence/beat unit. Create `sentence-animation-map.json` with exactly one record for every derived unit ID. Map each unit to at least one visible, semantically related animation or state change and a timing source. Prefer stable-anchor changes such as mask reveal, line draw, fill, highlight, blur-to-clear, crop change, or motion inside a fixed preview frame. Subtitle changes, the global progress bar, ambient background motion, page transition, or a recurring card merely flying in do not count. Produce `sentence-animation-qc.json` and require exact unit coverage with no duplicate or orphan IDs. Trigger coverage proves only that a cue exists; it does not prove that the picture expresses the narration. Record the concrete visible before-to-after change and affected component/state for every mapping. For negative narration such as "cannot see motion" or "cannot hear audio," show an absent, blocked, muted, or unavailable state rather than introducing a positive MOTION or AUDIO capability card.
10. **Resolve format before layout.** If the request is a Short, Reel, TikTok-style introduction, or other short-form social explainer, use 1080×1920 (9:16) by default. Use a horizontal composition only when the user explicitly requests landscape. Do not place a scaled 16:9 canvas inside a portrait frame; reflow hierarchy, diagrams, captions, and safe margins for the portrait canvas.
11. **Acquire technical preview assets when they improve understanding.** No asset quota applies: zero imported assets is valid. Prefer the named technology owner's official research page, documentation, press kit, repository, or product page. Save only images and short video excerpts that perform a clear explanatory job and are explicitly explained by one or more narration units. Source provenance is not semantic relevance. Record source page, direct asset URL, retrieval date, local derivative, transform/trim, byte count, SHA-256, `why_this_asset`, `explained_by_sentence_ids`, `visible_window_sentence_ids`, and `visible_label` in `official-assets.json`. Keep an asset visible only inside its mapped explanation window unless it remains directly relevant to the following narration. Label previews as official/source reference, keep embedded source video muted beneath the canonical narration, and never present a source clip as this production's own model output. Prefer a native diagram when a technical chart, collage, or screenshot would require extra narration to decode. If provenance, reuse, or semantic relevance is unclear, omit the asset or recreate the concept instead of importing it.
12. **Implement Remotion scenes with stable anchors.** Keep one top-level narration `<Audio>` beginning at frame zero. Use the required 0.90-second page gap as 0.15 seconds minimum completed-page hold, 0.45 seconds transition, and 0.30 seconds next-page pre-roll; add any page-ending editorial extra only to the completed-page hold. Read semantic start frames from the derived visual-cue map while captions continue reading canonical Qwen timestamps. Drive every sentence animation from its mapped aligned unit cue. Once a recurring panel, label, caption region, or preview viewport appears, keep its bounding box fixed unless moving that object is the meaning being explained. Do not alternate left/right entrances, repeatedly replace large sentence cards, shake warnings, pulse scale, or use low-damping bounce as the default beat. Use fixed-position mask reveals, local fills, path drawing, crossfades, or high-damping/no-overshoot interpolation; use content motion only inside a stable viewport. Make adjacent scenes visually cover their shared cut: use a hard cut, an actually overlapping crossfade, or persistent chrome/background. Never multiply an outgoing fade and a non-overlapping incoming fade into an unintended near-black gap. Use `useCurrentFrame()`, `interpolate()`, `<Sequence>`, or `<Series>`; do not use CSS animations or transitions.
13. **Review the rendered motion before finalizing.** Use independently rendered entry, mid-state, final-hold, and sentence-boundary stills only for fast iteration. Render a low-resolution full preview first, decode it, watch it at 1× speed, and run `scripts/build_motion_review.py` at no less than 2 fps to create one contiguous filmstrip per scene. Inspect portrait safe margins, text wrapping, caption clearance, density, per-unit visible change, cross-page residue, recurring bounding boxes, alternating direction, bounce, layout shift, flicker, source-media loops, and transition dead zones. After rendering the candidate final MP4, run `scripts/extract_review_stills_from_video.py` so final before/after frames for every sentence animation, representative states, and cue boundaries are decoded from that exact MP4 rather than re-rendered in a separate browser state. Make the script's visual lead match the renderer or supply explicit per-caption visual start times. Treat the MP4 as the source of truth if an independently rendered still disagrees with it. Manually inspect every narration unit's final-MP4 before/after pair and record the unit ID, narration, intended meaning, observed change, evidence hashes, asset relevance, reviewer note, and pass/fail status in `visual-semantic-qc.json`. A mismatch, inverted meaning, unexplained or over-persistent asset, unrelated content, or empty shell fails even when its trigger fired. Record watched ranges, filmstrip hashes, and temporal findings in `motion-stability-qc.json`; still coverage alone does not pass motion or semantic QC.
14. **Render and verify the delivered file.** Typecheck, render, decode the complete MP4, and probe streams, start times, duration, aspect ratio, sentence-animation coverage, motion stability, official-asset provenance, loudness, and true peak. Run FFmpeg `blackdetect=d=0.5` on the full candidate. If it reports a segment, extract a local 10 fps contact strip around that timestamp and either fix the transition or document why the darkness is intentional; do not waive it merely because the render succeeded. Rebuild the final-MP4 still manifest and motion filmstrips after every visual fix. Require caption/cue QC to pass, then copy the verified render to the delivery location and prove the copy SHA-256 equals the verified source render. Any pacing change creates a new canonical WAV and requires ASR, forced alignment, captions, cues, and render to be rebuilt from that WAV; only visual-only changes may preserve the prior audio and SRT hashes.

Read [references/production-contract.md](references/production-contract.md) before scaffolding the project or defining deliverables.

## Hard gates

- Never generate final timestamps before the final WAV is locked.
- Any audio change invalidates Qwen timing, captions, cues, render, and sync validation.
- Require the exact two-field `narration.json` schema and exact approved-script reconstruction before TTS. Any missing pause boundary, extra key, rewritten word, or stale metadata mapping fails.
- Require physical PCM silence in the final WAV: every narration item's `pause_after_ms` is a lower bound. Any added silence must come from `pacing-overrides.json`, be non-negative and reasoned, and be recorded as required + extra = effective. A pause tag, hidden reduction, inferred default, or duplicated global gap does not pass.
- Require Qwen3 ASR rather than Whisper for candidate selection and listen checks. A candidate must pass pronunciation equivalence before confidence ranking.
- Never overwrite canonical Qwen cue timestamps to make animation feel synchronized. Derive a separate visual timestamp and require a 0.30–0.60-second semantic lead.
- Treat visual-only timing changes as renderer changes: do not regenerate audio or rerun ASR; prove the WAV and SRT hashes are unchanged. Treat any editorial-pause change as an audio change and realign everything.
- For Short output, require a true 1080×1920 9:16 composition unless the user explicitly requests another orientation. A letterboxed or scaled-down landscape canvas does not pass.
- Require exactly one sentence-animation mapping for every minimal narration item and at least one visible semantic change per mapping. Captions, global progress, ambient loops, and page transitions do not satisfy this gate by themselves.
- Require every narration unit to pass `visual-semantic-qc.json`. Trigger-only QC, an unreviewed before/after pair, inverted meaning, unrelated content, or an empty shell does not pass.
- Fail recurring beat motion that alternates entrance directions, relocates a stable panel, uses low-damping bounce, shakes or scale-pulses by default, or makes the viewer reacquire the same information region every sentence.
- Require a 1× continuous-motion review and `motion-stability-qc.json`; before/after stills cannot prove temporal stability.
- Require final `stills-manifest.json` evidence to be decoded from the candidate delivery MP4, and require its video SHA-256 to match that MP4. Independently rendered browser stills are iteration aids, not final evidence.
- Require contiguous per-scene filmstrips sampled at no less than 2 fps and recorded in `filmstrip-manifest.json`.
- Fail any unintended FFmpeg `blackdetect=d=0.5` interval, especially a transition gap created by compounded non-overlapping fades.
- Require `official-assets.json` for every downloaded source image or clip, muted source-video audio, visible source labeling, and local deterministic assets for final rendering. Official provenance is not semantic relevance: fail any imported asset without an explicit explaining narration unit and bounded visible window.
- Do not begin the next page's narration until completed-page hold, transition, and next-page pre-roll are finished.
- Require one canonical narration track; video and audio must start at zero.
- Require complete unprompted ASR content, exact-script forced alignment, no caption overlap, and no hardcoded semantic start frames.
- Require `used_fallback=false`; stop instead of silently substituting a voice, provider, ASR model, or timing estimate.
- Require representative still review, successful TypeScript check, successful render, and full FFmpeg decode before delivery.
- Require the copied delivery MP4 SHA-256 to equal the final render SHA-256.

## Quick reference

| Input or stage | Canonical artifact | Consumers |
|---|---|---|
| Approved wording | approved script + two-field `narration.json` | TTS, captions |
| Editorial pacing | `pacing-overrides.json` | PCM assembly, page holds, timing QC |
| Scene mapping | `scenes.json` | derived manifest, storyboard, timing |
| Pronunciation aliases | `pronunciation-overrides.json` | TTS only |
| Derived production metadata | generated narration manifest | legacy TTS/timing consumers |
| Locked voice | `final-narration.wav` | Qwen, Remotion, delivery |
| Qwen alignment | raw word timestamps | captions, scenes, named cues |
| Canonical timing | timing JSON + SRT + `animation-cues.json` | captions, provenance |
| Visual timing | `visual-animation-cues.json` | Remotion animation triggers |
| Sentence motion coverage | `sentence-animation-map.json` + `sentence-animation-qc.json` | Remotion, still review, delivery QC |
| Visual semantic audit | `visual-semantic-qc.json` | per-unit meaning and asset-relevance delivery gate |
| Final-MP4 frame evidence | `stills-manifest.json` | exact per-unit before/after and cue-boundary review |
| Decoded motion review | `filmstrip-manifest.json` | contiguous per-scene temporal inspection |
| Official previews | `official-assets.json` + local derivatives | fixed preview viewport, provenance QC |
| Motion stability | `motion-stability-qc.json` | continuous-playback delivery gate |
| Render | MP4 | sync, stream, decode, loudness QC |

## Common mistakes

- Animating before audio is locked: discard the timing and realign.
- Using ASR spelling as subtitles: retain the display script and use ASR timestamps only.
- Fixing pronunciation inside `narration.json`: add the alias to `pronunciation-overrides.json` instead.
- Triggering effects at guessed seconds: bind each effect to a named aligned cue.
- Starting visuals exactly when the word is heard: derive a 0.30–0.60-second anticipatory visual cue while preserving the canonical cue.
- Slowing page changes by moving narration: keep audio fixed and reallocate the physical page gap to hold, transition, and pre-roll.
- Treating one full sentence as one unit: split every deliberate `，；：。！？` pause into its own minimal narration item.
- Copying IDs, page labels, captions, aliases, or paths into `narration.json`: keep them in separate inputs or generated manifests.
- Trusting TTS punctuation or control text for pacing: assemble pause-unit WAVs with the exact per-item PCM silence and retain `pause-timing.json`.
- Treating `pause_after_ms` as both minimum and final duration: keep it as the lower bound and record selective additions separately with reasons.
- Reusing a 16:9 scene inside a portrait wrapper: rebuild the hierarchy for 9:16 instead of letterboxing or shrinking the landscape canvas.
- Letting several narration units share one unchanged diagram: assign every unit its own visible semantic reveal, highlight, connector, transformation, or state change and validate 100% coverage.
- Treating trigger coverage as semantic approval: inspect every unit's actual before/after state and record what changed.
- Showing a positive MOTION or AUDIO card for narration that says motion cannot be seen or audio cannot be heard: visualize the absence, mute, or blocked state.
- Forcing an image or clip into the video because it was downloaded or comes from an official source: use it only when the narration explicitly explains it.
- Leaving an empty shell while waiting for the next phase: use a meaningful current state or remove the container until its content is introduced.
- Making every unit animate by flying a replacement card from alternating sides: keep the information region fixed and animate the diagram state inside it.
- Inspecting only stills: watch the contiguous rendered motion at 1× to catch bounce, jitter, repeated reacquisition, and non-seamless loops.
- Trusting independently rendered stills as delivery evidence: decode the exact frames from the candidate final MP4 and bind their hashes to its SHA-256.
- Fading one scene out and the next scene in without overlap: this creates a near-black dead zone; use a hard cut, a real overlap, or persistent chrome.
- Checking only one screenshot: inspect every scene at readable and final states.
- Treating a successful render as completion: require sync, stream, decode, caption, cue, audio, and fallback checks.
- Copying a verified render without rechecking the destination: compare source and delivery SHA-256 values.
