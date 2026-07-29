---
name: skill-technical-remotion
description: Use when a finalized narration script must become a Remotion or HTML/PPT-style explainer video and the user requires Fish Audio S2 Pro voice cloning, Qwen word-level synchronization, accurate subtitles, or narration-triggered animations.
---

# Skill Technical Remotion

## Overview

Build source-independent explainer videos around one canonical final narration WAV. Generate audio first, derive every caption and semantic animation cue from Qwen timestamps, then render and verify the Remotion composition.

## Keep article writing outside this skill

- Accept an approved script, transcript, or structured narration as the production input. Do not silently rewrite approved wording.
- When the request is a concise Traditional Chinese Short introduction for an AI model, software feature, developer tool, or other technology and no approved script exists, **REQUIRED CONDITIONAL SUB-SKILL:** use `skill-writing-technical-shorts` for the article. Resume this skill only after that script is complete.
- For other article formats, use the writing skill selected for that format. Do not copy writing formulas into this skill.
- Keep research citations outside spoken narration. Preserve a display script separately from TTS-only pronunciation aliases and Fish control tags.

## Required production skills

- **REQUIRED SUB-SKILL:** use `tts-skill` whenever narration must be generated or replaced. Its configured Fish Audio S2 Pro voice is the default unless the user explicitly overrides it.
- **REQUIRED SUB-SKILL:** use `plan-geometric-explainer-video` for story-to-geometry mapping, visual grammar, motion grammar, Remotion implementation, and still-first review.
- **REQUIRED COMPLETION SKILL:** use `verification-before-completion` before declaring the video finished.

Read `../../TTS-and-Voice-AI/tts-skill/references/fish-s2-default-voice.json` before using the default voice. Use the single 60-second lossless WAV declared by that TTS profile as the complete Fish S2 cloning reference. Verify its hash, audio format, duration, and matching full transcript before synthesis. Do not derive or substitute an MP3 or shortened reference clip.

Do not reopen or retrace historical reference videos, URLs, creators, or timecodes. Work only from the current script, final audio, timing artifacts, brand rules, and supplied production assets.

## Production workflow

1. **Lock the display script.** Split it into meaning-based scenes. Store canonical `text` and optional TTS-only `tts_text`; captions must always use `text`.
2. **Generate scene audio.** Use `tts-skill`, retain lossless scene WAVs, concatenate production pauses, master one final WAV, and record voice ID, reference hashes, seeds, prompt IDs, output hash, and `used_fallback=false`.
3. **Listen before aligning.** Run unprompted `Qwen/Qwen3-ASR-0.6B` against the final WAV. Regenerate only defective scenes, rebuild the final WAV, and repeat the listen check. Lock the audio after content and ending completeness pass.
4. **Force-align the locked audio.** Run `Qwen/Qwen3-ForcedAligner-0.6B` with the exact display script. Use ASR only for timing; never replace approved product names or English tokens with recognition text.
5. **Build one timing truth.** Produce phrase captions, SRT, scene ranges, and named animation cues from the aligned units. Store the final-audio SHA-256 in raw and derived timing artifacts. Do not infer semantic timings from character count, scene percentages, fixed delays, or TTS segment lengths.
6. **Implement Remotion scenes.** Keep one top-level narration `<Audio>` beginning at frame zero. Convert seconds or named cues to frames at composition FPS. Use `useCurrentFrame()`, `interpolate()`, `spring()`, `<Sequence>`, or `<Series>`; do not use CSS animations or transitions.
7. **Review stills first.** Render entry, mid-state, and final-hold stills for every scene. Inspect safe margins, text wrapping, caption clearance, density, semantic states, and whether a cue fires only after its phrase begins.
8. **Render and verify.** Typecheck, render, decode the complete MP4, probe streams, validate start times and duration, inspect loudness and true peak, and require caption/cue QC to pass.

Read [references/production-contract.md](references/production-contract.md) before scaffolding the project or defining deliverables.

## Hard gates

- Never generate final timestamps before the final WAV is locked.
- Any audio change invalidates Qwen timing, captions, cues, render, and sync validation.
- Require one canonical narration track; video and audio must start at zero.
- Require complete unprompted ASR content, exact-script forced alignment, no caption overlap, and no hardcoded semantic start frames.
- Require `used_fallback=false`; stop instead of silently substituting a voice, provider, ASR model, or timing estimate.
- Require representative still review, successful TypeScript check, successful render, and full FFmpeg decode before delivery.

## Quick reference

| Input or stage | Canonical artifact | Consumers |
|---|---|---|
| Approved wording | `narration.json` | TTS, captions, storyboard |
| Locked voice | `final-narration.wav` | Qwen, Remotion, delivery |
| Qwen alignment | raw word timestamps | captions, scenes, named cues |
| Derived timing | timing JSON + SRT | Remotion components |
| Render | MP4 | sync, stream, decode, loudness QC |

## Common mistakes

- Animating before audio is locked: discard the timing and realign.
- Using ASR spelling as subtitles: retain the display script and use ASR timestamps only.
- Fixing pronunciation by changing captions: add a `tts_text` alias instead.
- Triggering effects at guessed seconds: bind each effect to a named aligned cue.
- Checking only one screenshot: inspect every scene at readable and final states.
- Treating a successful render as completion: require sync, stream, decode, caption, cue, audio, and fallback checks.
