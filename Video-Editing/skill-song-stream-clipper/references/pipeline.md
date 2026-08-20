# Production Pipeline

This is the canonical production workflow for converting a mixed conversation-and-singing stream into individual verified song clips and, only when requested, restrained MV-Lite finished videos. Treat each stage as an artifact gate: do not consume a file until its row count, schema, and source run have been checked.

This workflow contains no annotation UI, accepted-range collection, model fitting, or training evaluation. Ranker development is documented separately in `end-boundary-ranker-training.md` and is not required to process a new source.

## Modular Script Map

Use `scripts/run_pipeline.py` as the normal entry point. It resolves the canonical run-directory layout, invokes each production stage, validates declared outputs, and updates `run_manifest.json`. Use `--dry-run` to inspect every command before execution and `--resume` to skip stages whose complete declared artifact set already exists.

| Script | Responsibility | Primary artifact |
|---|---|---|
| `prepare_media.py` | Stage the untouched master, extract 16 kHz mono WAV, and compute normalized 20 ms RMS buckets | `source/audio_16k_mono.wav`, `source/waveform_20ms.json` |
| `asr-router` (Agent boundary) | Select and execute locked Qwen3 recognition plus forced alignment | `asr/qwen3_full_asr_phrases.csv`, `asr/qwen3_full_asr_words.csv` |
| `validate_asr_artifacts.py` | Validate the Router-produced Qwen artifact set before downstream use | validated ASR gate |
| `run_music_detection.py` | Score 3-second windows at a 1-second hop and average overlapping observations | `music_detection/music_probability_avg_by_second.csv` |
| `discover_songs.py` | Ask Codex CLI for a lyric-derived candidate title list from fixed 3-minute windows | `song_discovery/labels.txt` |
| `label_phrases.py` | Label and conservatively repair every phrase with exactly `talk` or a concrete title | `phrase_labels/labeled_phrases.csv` |
| `build_intervals.py` | Merge eligible same-title runs and reject short, sparse, low-music, or incompletely covered intervals | `intervals/song_intervals.csv` |
| `refine_starts.py` | Place starts from lyric, music onset, ASR occupancy, and a nearby local RMS trough | `boundaries/starts/song_intervals_with_starts.csv` |
| `refine_ends.py` | Apply a compatible prebuilt ranker or deterministic MusicDetection plus ASR fallback | `boundaries/final/song_cut_intervals.csv` |
| `cut_clips.py` | Re-encode frame-accurate clips, probe them, and emit verification results | `clips/clip_manifest.csv` |

Shared modules `pipeline_utils.py` and `codex_runtime.py` contain file/probe helpers and the local Codex CLI launcher. `run_manifest.py` owns the run record. No production script imports or invokes ranker fitting.

Optional finishing uses two additional independent scripts after the extraction gate:

| Script | Responsibility | Primary artifact |
|---|---|---|
| `render_mv_lite.py` | Build lyric captions and a fixed-scale x/y camera plan, run periodic person detection, and render selected songs | `batch_render_summary.json` |
| `audit_mv_lite.py` | Verify streams, duration, audio alignment, subtitles, motion, black frames, and visual contact sheets | `batch_qc_summary.json` |

Runtime requirements are Python 3.10 or newer, FFmpeg/FFprobe, and NumPy. Read the ASR Router Qwen3 guide for recognition runtime requirements. MusicDetection requires PyTorch, librosa, huggingface-hub, and safetensors. Optional ranker inference requires joblib plus the estimator's compatible runtime. MV-Lite finishing requires OpenCV, Ultralytics, FontTools, SciPy, and `opencc-python-reimplemented`. Never install or switch model revisions silently; record the environment and revisions in the run manifest.

Reference invocation around the Router boundary:

```powershell
python scripts/run_pipeline.py `
  --video <master-video> `
  --run-dir <run-directory> `
  --stop-after media_preparation

# Agent invokes asr-router here with the locked Qwen constraints.

python scripts/run_pipeline.py `
  --video <master-video> `
  --run-dir <run-directory> `
  --from-stage asr `
  --music-precision bf16 `
  --resume
```

## 1. Media Preparation

Keep the highest native source resolution available. Never upscale. Download only audio/video media and metadata needed for provenance; do not download or inspect comments, chapters, descriptions, or viewer timestamps for recognition.

Create:

- `source/master.<container>`: untouched source master.
- `source/audio_16k_mono.wav`: PCM 16-bit, 16 kHz, mono.
- `run_manifest.json`: source URL or local path, source hash, duration, resolution, acquisition time, and commands.

Reference FFmpeg extraction:

```powershell
ffmpeg -y -i <master-video> -vn -ac 1 -ar 16000 -c:a pcm_s16le <audio_16k_mono.wav>
```

## 2. Full Qwen3 ASR

Invoke `Speech-Recognition/asr-router` once over the complete audio with
`preferred_provider=qwen3`, `profile=word_timestamps`, and
`fallback_allowed=false`. Read the Router's Qwen3 provider guide for its model,
aligner, chunking, precision, and output rules. Consume both phrase-level and
word-level artifacts and retain the raw alignment payloads for audit. Neither
`run_pipeline.py` nor another business script may resolve or execute the Qwen
adapter; the `asr` runner stage only validates artifacts already returned by the
Router.

## 3. Music Probability Timeline

Run `lab260/MusicDetection` over the complete 16 kHz mono audio.

| Parameter | Value |
|---|---:|
| window size | 3.0 s |
| hop size | 1.0 s |
| batch size | 48 |
| decision threshold | 0.5 |
| CUDA precision | BF16 |

Store every window probability. If deriving a per-second series, average all windows covering that second; do not keep only a hard Boolean classification.

## 4. Song Discovery With Codex

Partition phrase ASR by fixed 180-second timeline windows and group four windows per Codex invocation. Use `gpt-5.6-terra`, service tier `default`, and reasoning effort `high`.

Prompt constraints:

- Identify song titles from sung lyric semantics only.
- Ignore spoken title announcements, setup, UI text, comments, chapters, and metadata.
- Return Traditional Chinese for Chinese titles and notes. Preserve English and Japanese.
- Return uncertainty and short local evidence, but do not print full lyrics in terminal output.

Expected outputs include `discovered_song_titles.csv` and `labels.txt`.

## 5. Phrase Labeling and Repair

Send every ASR phrase to Codex in batches of 80 with the candidate song list. Use `gpt-5.6-terra`, service tier `default`, and reasoning effort `medium`.

Each output row must preserve input order and timestamps and contain:

- The original phrase identifier.
- Exactly one label: `talk` or one concrete candidate song title.
- `repaired_text` with conservative ASR correction.
- A confidence or short note when supplied by the labeling implementation.

Everything that is not sung lyric is `talk`, including song announcements, setup, laughter, humming without identifiable lyrics, instrumental-only passages, and conversation. Do not emit `lyric`, `setup`, `unknown_song`, or any other class.

## 6. Song Interval Construction

Start from consecutive equal song labels and apply these rules in order:

1. Merge runs of the same title when the intervening pause is at most 15 seconds.
2. Merge adjacent lyric runs when MusicDetection shows continuous music through the label break, using threshold 0.5, mean probability at least 0.6, and no low-music interruption longer than 2 seconds.
3. Reject an individual song run shorter than 30 seconds.
4. Reject an individual song run containing fewer than 3 phrase rows.
5. Reject a resulting interval whose mean music probability is below 0.6. This removes a cappella and rehearsal-like spans from this workflow.
6. Reject an interval when MusicDetection does not cover its complete lyric range; never calculate acceptance from a small covered subset.

Do not merge different concrete song titles merely because the detector says music is continuous.

## 7. Start Boundary Refinement

Use the rule in `boundary-methodology.md`. Baseline parameters:

| Parameter | Value |
|---|---:|
| search lookback | 60 s |
| music threshold | 0.5 |
| maximum music gap | 2 s |
| minimum continuous music run | 4 s |
| first-lyric tolerance | 5 s |
| ASR lookback | 15 s |
| ASR cluster gap | 3 s |
| ASR padding | 0.3 s |
| maximum trough distance before anchor | 5 s |
| RMS smoothing | 0.4 s |
| low-volume candidate percentile | 35 |

The selected cut must precede the first lyric and the connected continuous music onset. If an ASR cluster sits immediately before the onset, move the anchor to the start of that cluster so the complete non-lyric phrase remains in the clip. Search the ASR-free gap between the previous ASR cluster and this anchor, limited to five seconds before the anchor. Choose the qualifying low local trough nearest the anchor; use the window minimum only as a fallback.

## 8. End Boundary Refinement

When a compatible prebuilt ranker and feature schema are available, require model metadata with independent generalization evidence, then score candidate times every 0.25 seconds strictly after the raw last lyric through at most 90 seconds, clipped by the next song start and source duration. Select the highest score and the earliest time on an exact tie. Record the model identifier, feature-schema version, and source-data compatibility check.

When no compatible ranker exists, use the deterministic baseline:

- Search no more than 30 seconds after the last lyric.
- Detect a stable non-music run of at least 2 seconds.
- Use MusicDetection probability plus ASR occupancy to avoid cutting active lyric or speech.
- Keep 0.3 seconds of ASR safety padding and at least 0.6 seconds of safe gap.
- Mark the boundary method as deterministic fallback and lower its confidence. Do not describe detector stability as ranker confidence.

## 9. Precision Cutting

Provide `song_cut_intervals.csv` to `scripts/cut_clips.py`. Use the source master, not a proxy, unless the user explicitly requests proxy previews. The script re-encodes for frame-accurate cuts, preserves source dimensions, creates fast-start MP4 files, probes every output, and writes a manifest.

Do not use stream copy for final boundary work because keyframe placement can move the apparent cut.

## 10. Clip-Extraction Finish Definition

Version 1 ends when all retained song intervals have verified MP4 outputs. Record:

- Count requested and count verified.
- Maximum duration error.
- Encoder used, including fallback.
- Boundary source for each clip: manual, ranker, or deterministic.
- Any interval excluded by duration, phrase-count, or mean-music rules.

Stop here unless the user explicitly requests MV-Lite finishing.

## 11. Optional MV-Lite Finishing

Run this stage only for verified song intervals and only when a finished presentation is requested. It is not part of the default clip-extraction completion gate.

### 11.1 Source and output contract

- Render from the highest native-resolution source master, not a proxy.
- Preserve the source frame rate and do not output a resolution above the native source. If the source tops out at 360p, the deliverable remains 360p.
- A fixed crop may be resampled back to the native frame dimensions, but do not use AI upscaling or claim reconstructed detail.
- Keep a clean clipped master, portable subtitle artifacts, the render plan, and the finished derivative.

### 11.2 Audio preservation

- Use one continuous source-audio interval from the final song start through the final song end.
- Do not make internal audio cuts, change speed, replace accompaniment, regenerate vocals, normalize loudness, denoise, compress, or remix the song.
- Re-encode only when required by the output container. Verify zero timeline offset and duration agreement against the source interval.

### 11.3 Character detection and stable framing

- Run a detector proven to locate the visible performer or avatar at periodic samples rather than every frame.
- Store timestamp, box, center, dimensions, and confidence for every sample.
- Reject implausible detections, fill short gaps conservatively, and smooth the retained center trajectory over several seconds.
- Use the smoothed trajectory only to define a safe framing center. Do not chase normal character animation frame by frame.
- Fall back to a fixed manually safe center if detector coverage or confidence is insufficient.

### 11.4 Fixed-scale camera motion

- Choose one crop size and one scale for the entire song. Set `dynamic_zoom=false` in the render plan.
- Permit only horizontal and vertical movement within crop-safe bounds.
- Combine sparse section keyframes with continuous low-frequency x/y drift so the frame is never mechanically static.
- Interpolate keyframes with a smooth ease curve that has continuous velocity and acceleration. Do not use step changes, linear snaps, or repeated short corrections.
- Bound per-frame displacement and acceleration, then validate both from the final camera plan.

### 11.5 Section-aware composition

- Derive broad intro, verse, chorus, instrumental, and tail regions from lyric density, ASR gaps, and the music timeline. Do not require visual scene analysis.
- Change framing intent only at broad section boundaries or long instrumental gaps. Do not move the camera for every phrase or beat.
- Keep section changes sparse and gradual; audio remains continuous throughout.

### 11.6 Livestream UI handling

- Create one layout profile per source program for fixed branding, native captions, chat, donation banners, and notification regions.
- Prefer a safe fixed crop when it can hide unwanted UI without clipping the performer.
- Otherwise use restrained fixed masks or bands. Do not let masks cover the performer, new subtitles, or required credits.
- Treat transient center-screen notifications as a reported limitation unless a deterministic mask can remove them without damaging the performance.

### 11.7 Lyric subtitles

- Build captions from repaired lyric text and timestamps anchored to final-audio word alignment.
- Include lyric rows only. Exclude talk, setup, laughter, announcements, and instrumental-only spans.
- Use static text without karaoke coloring or per-word color changes.
- Use a readable font family with complete Traditional Chinese, Japanese, and English coverage. Permit multiline layout and grow lines upward from a fixed safe anchor.
- Preserve a portable subtitle file and a clean master in addition to any burned-caption derivative.

### 11.8 Titles and credits

- When requested, show a restrained song-title card near the beginning and a short source or cover credit near the end.
- Keep overlays brief, legible, and outside the performer and subtitle safe regions.
- Do not add generated imagery, B-roll, decorative effects, or large animated panels by default.

### 11.9 Source-image preservation

- Preserve the source image tone and color.
- Do not apply brightness, contrast, gamma, saturation, hue, curves, LUTs, denoise, sharpening, restoration, grain, or other image correction.
- Limit pixel changes to crop/scale sampling, required UI masks, subtitles, and explicitly requested title or credit overlays.

### 11.10 Finishing QC

Require all of the following before reporting a finished result:

- Exact requested duration within encoder tolerance, expected resolution and frame rate, and both audio and video streams.
- Audio cross-correlation at the head, middle, and tail shows no material offset from the source interval.
- `dynamic_zoom=false`; crop dimensions remain constant; x/y positions stay within bounds.
- Planned and measured camera movement contain no jumps, frozen output caused by rendering, or excessive per-frame acceleration.
- Lyric subtitle intervals are valid, non-overlapping, fully visible, and clear of the performer.
- No unintended black frames or duplicate frames.
- The render command contains no color or tonal correction filter.

### 11.11 Local no-token execution

When existing song intervals and phrase labels have already passed the extraction gates, MV-Lite preparation and rendering does not call Codex. It does not rediscover titles or relabel phrases; it consumes those completed artifacts directly.

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

This no-token property applies only after title discovery, phrase labeling, interval construction, and boundary refinement are complete. A new unprocessed stream still needs the semantic discovery and labeling stages documented above.
