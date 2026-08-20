# Data Contracts

Use UTF-8 or UTF-8 with BOM for CSV files. Timestamps are floating-point seconds from the beginning of the untouched source master.

## Phrase ASR

Required columns:

| Column | Meaning |
|---|---|
| `index` | Stable phrase identifier |
| `start_seconds` | Phrase start |
| `end_seconds` | Phrase end |
| `text` | Raw multilingual ASR text |

Require `0 <= start_seconds < end_seconds`, sorted by start time. Word-level ASR follows the same timing convention and adds a token or word text column.

## Music Detection

Required semantic fields, even when implementation column names differ:

| Field | Meaning |
|---|---|
| window start | Start of the 3-second detector window |
| window end | End of the detector window |
| music probability | Continuous probability in `[0, 1]` |

Never discard the continuous score after thresholding.

Require complete per-second coverage over every candidate lyric interval. A high mean calculated from a partial detector timeline is invalid and must be rejected as incomplete coverage.

## Labeled Phrases

Required columns:

| Column | Meaning |
|---|---|
| original phrase id | Join key back to phrase ASR |
| `start_seconds` | Unchanged source timestamp |
| `end_seconds` | Unchanged source timestamp |
| `text` | Original ASR text |
| `repaired_text` | Conservative corrected text |
| `song_label` | Exactly `talk` or a concrete song title |

Reject missing rows, duplicate identifiers, reordered output, new timestamps, and labels outside the allowed set.

## Candidate Song Intervals

Minimum columns:

| Column | Meaning |
|---|---|
| `interval_no` | One-based stable order |
| `song_label` | Concrete song title |
| lyric start | First retained lyric phrase start |
| lyric end | Last retained lyric phrase end |
| phrase row count | Number of labeled lyric phrases |
| mean music probability | Mean detector score over the interval |

Keep rejected runs in separate audit CSV files with rejection reasons.

## Final Cut Intervals

The bundled cutter requires these defaults:

| Column | Type | Meaning |
|---|---|---|
| `interval_no` | integer | Unique output order |
| `song_label` | string | Output title |
| `cut_start_seconds` | float | Final inclusive start |
| `cut_end_seconds` | float | Final exclusive end |

The cutter accepts alternate column names through CLI flags. Require positive duration, unique interval numbers, non-negative starts, and ends within source duration plus probe tolerance.

Recommended audit fields:

- `raw_lyric_start_seconds`
- `raw_lyric_end_seconds`
- `start_method`
- `end_method`
- `start_confidence`
- `end_confidence`
- `mean_music_probability`
- `manual_review_status`

## Clip Manifest

`scripts/cut_clips.py` writes:

- Requested interval number, title, start, end, and expected duration.
- Actual probed duration and absolute duration error.
- Audio/video presence, dimensions, encoder used, output path, and log path.
- `verified` or `failed_verification` status.

Treat a nonzero cutter exit code or any non-verified row as an incomplete run.

## Canonical Run Layout

`scripts/run_pipeline.py` writes one isolated directory per source:

```text
run-dir/
  run_manifest.json
  source/
  asr/
  music_detection/
  song_discovery/
  phrase_labels/
  intervals/
  boundaries/starts/
  boundaries/final/
  clips/
```

Do not point two sources at the same run directory. `prepare_media.py` rejects an existing staged master when its content differs from the requested source.

## Optional MV-Lite Render Plan

Use a machine-readable JSON plan when a verified clip enters MV-Lite finishing. Required semantic fields:

| Field | Meaning |
|---|---|
| source video and audio | Highest native-resolution master assets |
| source start and end | The verified continuous song interval |
| output resolution and fps | Values no greater than the native source |
| fixed crop width and height | Constant crop dimensions for the whole song |
| fixed scale | Constant scale; dynamic zoom must be false |
| camera keyframes | Timestamped x/y centers or offsets with easing |
| detector summary | Sample count, coverage, confidence, and fallback status |
| subtitle artifact | Lyric-only captions using aligned timestamps |
| layout profile | Protected and masked livestream UI regions |
| overlays | Optional title and credit events only |
| image correction | Must be absent or explicitly `none` |

Require every camera keyframe to remain inside crop-safe bounds. The final render summary must record maximum planned per-frame displacement and acceleration, subtitle count and overlap count, audio-alignment checks, duplicate-frame checks, and black-frame checks.
