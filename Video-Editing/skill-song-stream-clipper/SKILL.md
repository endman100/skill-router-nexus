---
name: skill-song-stream-clipper
description: Extract complete per-song MP4 clips from long singing streams or song-relay videos with multilingual Qwen3 ASR, Codex lyric-based labeling, MusicDetection, boundary refinement, and verified FFmpeg cuts; optionally finish verified clips as restrained MV-Lite videos with lyric-only subtitles and fixed-scale smooth x/y framing. Use when a long stream mixes songs with conversation and the result must not rely on YouTube comments, chapters, descriptions, or viewer timestamps.
---

# Song Stream Clipper

## Scope

Turn one long-form singing stream into one verified MP4 per retained song. That is the default completion point. Continue into MV-Lite finishing only when the user explicitly requests a finished presentation rather than raw per-song clips.

Never use YouTube comments, chapters, descriptions, or viewer-provided timestamps as recognition evidence. Derive song identity from sung lyric content. Keep Chinese output in Traditional Chinese; preserve English and Japanese writing systems.

The production workflow must not depend on an annotation UI, accepted-range collection, model fitting, or other training operations. Those are development activities, not stages for processing a new source.

## Required Workflow

Read [references/pipeline.md](references/pipeline.md) before running a new source. Read [references/data-contracts.md](references/data-contracts.md) before modifying scripts or exchanging CSV or JSON files. Read [references/boundary-methodology.md](references/boundary-methodology.md) when generating or auditing cut points.

Use [scripts/run_pipeline.py](scripts/run_pipeline.py) to orchestrate the business
stages. It pauses at the Agent-owned ASR boundary: prepare media first, invoke
`asr-router`, then resume so the runner can validate and consume the Router
artifacts. It records every stage in `run_manifest.json`.

1. Create an isolated run directory for the source video, retain the untouched master, and initialize `run_manifest.json` with [scripts/run_manifest.py](scripts/run_manifest.py).
2. Extract 16 kHz mono WAV audio with FFmpeg.
3. Invoke `asr-router` with `preferred_provider=qwen3`,
   `fallback_allowed=false`, and word alignment. Do not split recognition by
   language; the router owns the Qwen invocation and model details.
4. Run MusicDetection over the entire audio with a 3-second window and 1-second hop. Average overlapping observations by timeline position.
5. Give Codex fixed 3-minute ASR windows and discover candidate song titles from lyrics only.
6. Give Codex every ASR phrase and the candidate title list. Label every phrase as exactly `talk` or one concrete song title while repairing obvious ASR errors.
7. Build contiguous song intervals. Merge brief same-title gaps and detector-supported continuous music. Reject short or low-music runs.
8. Refine starts from the first lyric, continuous music onset, preceding ASR, and a nearby smoothed-volume trough.
9. Refine ends with a compatible prebuilt end-boundary ranker, or use the deterministic ASR plus MusicDetection fallback when no compatible model exists.
10. Cut the source master with [scripts/cut_clips.py](scripts/cut_clips.py). Re-encode for frame-accurate boundaries; do not upscale.
11. Inspect `clip_manifest.csv`. The clip-extraction task is complete only when every requested interval has one verified MP4 with audio, video, and duration error within tolerance.

## Optional MV-Lite Finishing

Enter this stage only after the clip-extraction completion gate passes and the user explicitly requests finished videos. Follow the target method in [references/pipeline.md](references/pipeline.md#11-optional-mv-lite-finishing).

Use [scripts/render_mv_lite.py](scripts/render_mv_lite.py) when final cut intervals and complete phrase labels already exist. It performs local subtitle preparation, character detection, fixed-scale x/y camera planning, and rendering without calling Codex. Then run [scripts/audit_mv_lite.py](scripts/audit_mv_lite.py) against the batch summary; do not accept renders only because FFmpeg exited successfully.

- Render from the native-resolution source master and preserve the source frame rate. Do not upscale beyond the source's highest native resolution.
- Preserve one continuous source-audio interval per song. Do not make internal audio cuts, change speed, replace the accompaniment, or alter the mix.
- Use periodic character detection only to establish a stable safe frame. Smooth detections; do not chase the character frame by frame.
- Keep crop and scale constant for the entire song. Allow only smooth horizontal and vertical camera motion; never use dynamic zoom.
- Burn lyric-only subtitles from repaired text and real aligned timestamps. Do not show talk captions or karaoke color changes.
- Preserve the source image tone. Do not apply brightness, contrast, gamma, saturation, LUT, denoise, sharpening, or other image correction.
- Add only restrained song-title and credit overlays when requested, then run the finishing QC gate.

Reference invocation:

```powershell
python scripts/render_mv_lite.py `
  --video <native-video-master> `
  --audio <continuous-source-audio> `
  --intervals <song-cut-intervals.csv> `
  --phrases <labeled-phrases.csv> `
  --model <person-detector.pt> `
  --output-dir <mv-lite-directory> `
  --interval-no <number>

python scripts/audit_mv_lite.py `
  --batch-summary <mv-lite-directory>/batch_render_summary.json `
  --source-audio <continuous-source-audio>
```

## Execution Rules

- Run the ASR Router Qwen stage and music-detection stage in parallel only when
  GPU memory permits; downstream stages depend on both.
- Use `gpt-5.6-terra`, normal/default service tier, high reasoning for song discovery, and medium reasoning for phrase labeling unless the runtime rejects that model.
- Process all ASR phrases. Do not sample, omit, or collapse rows before Codex labeling.
- Use song announcements only as `talk`; never use them to infer a title.
- Preserve repeated lyrics. Repair text, but do not invent missing sung spans or alter timestamps without alignment evidence.
- Record every command, input path, output path, model revision, parameter override, and validation result in the run directory.
- Keep intermediate artifacts. Never mix ASR outputs from different models or runs.
- Keep ranker development separate from production. Read [references/end-boundary-ranker-training.md](references/end-boundary-ranker-training.md) only when the user explicitly asks to train, recalibrate, or evaluate the ranker.

## Completion Gate

Run media preparation first:

```powershell
python scripts/run_pipeline.py `
  --video <highest-native-resolution-master> `
  --run-dir <isolated-run-directory> `
  --stop-after media_preparation
```

Then have the Agent invoke `asr-router` with `source=<run-dir>/source/audio_16k_mono.wav`,
`preferred_provider=qwen3`, `fallback_allowed=false`, and
`profile=word_timestamps`, writing the Qwen artifacts to `<run-dir>/asr/`.
Resume only after Router completion:

```powershell
python scripts/run_pipeline.py `
  --video <highest-native-resolution-master> `
  --run-dir <isolated-run-directory> `
  --from-stage asr `
  --resume
```

Use `--dry-run` to inspect the resolved business-stage commands and output paths.
The runner never executes an ASR provider adapter. When the Agent finishes the
Router call, record that command and its artifacts explicitly:

```powershell
python scripts/run_manifest.py init --manifest <run-dir>/run_manifest.json --source <source-url-or-path>
python scripts/run_manifest.py record --manifest <run-dir>/run_manifest.json --stage asr --status completed --command "<exact command>" --output <phrase-csv>
```

The runner invokes the final cutter. To rerun only that stage manually:

```powershell
python scripts/cut_clips.py `
  --video <master-video> `
  --intervals <song-cut-intervals.csv> `
  --output-dir <clips-directory> `
  --encoder auto
```

Require all of the following:

- The process exits with code `0`.
- `clip_manifest.csv` has exactly one row per requested interval.
- Every row has `status=verified`, `has_video=True`, and `has_audio=True`.
- No clip exceeds source duration or has a non-positive duration.
- The user can inspect the MP4 files and their song-title filenames.

Technical verification does not prove semantic boundary quality. Report whether starts and ends were manually reviewed, deterministic, or ranker-selected.

For an explicitly requested MV-Lite deliverable, also require:

- Output resolution and frame rate do not exceed the native source.
- Audio is present, continuous, duration-matched, and aligned to the requested source interval.
- Dynamic zoom is disabled and the camera plan contains only bounded x/y movement.
- Subtitle events contain lyrics only, have valid intervals, remain inside the safe area, and do not overlap.
- No color or tonal correction filter is present in the render plan.
- Black-frame, duplicate-frame, crop-boundary, and motion-continuity checks pass.

## Current Defaults

Use the parameter set in [references/pipeline.md](references/pipeline.md) as the reproducible baseline. Change a parameter only when the source behavior justifies it, and record the override instead of silently changing the baseline.
