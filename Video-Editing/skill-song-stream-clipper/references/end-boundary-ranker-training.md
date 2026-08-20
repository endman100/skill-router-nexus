# End Boundary Ranker Training

This document is development-only. Do not insert these steps into the production pipeline for processing a new stream. An annotation UI may collect labels for this procedure, but the UI is never a production dependency.

## Scope

Train or recalibrate a model that ranks candidate song-end timestamps from local ASR and MusicDetection evidence. Keep source-specific calibration distinct from cross-video validation.

## 1. Freeze Input Contracts

Before collecting labels, freeze and record:

- Source master hash and duration.
- ASR Router Qwen3 provider and aligner revisions.
- Phrase and word timestamp schemas.
- MusicDetection model revision, 3-second window, 1-second hop, and overlap-averaging rule.
- Raw lyric interval file and its hash.
- Candidate step, search cap, feature-schema version, and code revision.

Do not combine annotations or features from runs with incompatible contracts.

## 2. Collect Accepted End Ranges

For every retained song, let the reviewer mark a continuous time range in which a cut would be acceptable. Store:

- Stable interval number and song label for review only.
- Accepted range start and end in source seconds.
- Annotation identifier, revision, creation time, and update time.
- Source and input-artifact hashes.

The annotation UI is only a label-entry tool. Its display state, waveform zoom, existing cut point, and navigation behavior must not become model features.

## 3. Generate Candidate Rows

For each song:

1. Start at the raw last-lyric timestamp.
2. Stop at `min(raw_last_lyric + 90s, next_song_start, source_duration)`.
3. Generate one candidate every 0.25 seconds.
4. Label a candidate positive when it falls inside the accepted range, otherwise negative.
5. Fail the dataset build if an accepted range contains no generated candidate.

## 4. Build the Versioned Feature Vector

The calibrated baseline contains 83 features:

- Three interval-relative values: candidate offset after the raw lyric end, song duration, and available search span.
- Music probability at offsets `-15, -10, -7, -5, -3, -2, -1, 0, +1, +2, +3, +5, +7, +10, +15` seconds.
- Mean, standard deviation, minimum, and maximum music probability before and after the candidate over 2, 3, 5, 10, and 20-second windows.
- Contiguous low-music run lengths before and after the candidate at thresholds 0.25, 0.35, 0.45, 0.55, and 0.65.
- Whether ASR overlaps the candidate, seconds since previous ASR, and seconds until next ASR.
- Talk coverage, total speech coverage, and ASR phrase count over 2, 5, 10, and 20-second windows.

Explicitly exclude:

- Interval number and song title.
- Absolute program time.
- Existing or old cut-point distance.
- Accepted-range coordinates or annotation identifiers.
- Any UI state.

## 5. Fit the Baseline Model

Use the reproducible baseline unless a recorded experiment justifies an override:

| Parameter | Value |
|---|---:|
| model | `ExtraTreesClassifier` |
| trees | 500 |
| `min_samples_leaf` | 4 |
| class weighting | balanced |
| `max_features` | none |
| random seed | 20260731 |
| parallelism | all available CPU jobs |

Fit on candidate rows, predict positive probabilities, and select the maximum-probability candidate per song. Choose the earliest timestamp on an exact tie.

## 6. Evaluate Without Overclaiming

Support two explicitly named evaluation modes:

- `source_calibration`: fit all accepted ranges from one source to reproduce that source's reviewer preference. Report hit count inside accepted ranges, margins, and misses. Never call this generalization evidence.
- `cross_video_validation`: hold out complete source videos, not random candidate rows from the same song or stream. Report per-video and aggregate hit rate, miss distance, calibration, and failure categories.

Candidate rows from one song are highly correlated. A random row-level split leaks song and neighborhood information and is not an acceptable validation design.

## 7. Save Reproducible Artifacts

Archive at least:

- Serialized model.
- Feature names and schema version.
- Candidate scores.
- Per-song selected predictions and accepted ranges.
- Feature importance.
- Training and evaluation summary.
- All source hashes, annotation revision, model parameters, code revision, and evaluation scope.

Set `generalization_claim=false` for source calibration. A perfect in-sample hit rate must still be reported as in-sample.

## 8. Production Compatibility Gate

Before production inference, require exact compatibility for:

- Feature names and order.
- ASR phrase semantics and timestamp units.
- MusicDetection probability aggregation.
- Candidate step and search-range interpretation.
- Missing-value handling and preprocessing.

If compatibility fails, do not adapt the feature vector silently. Reject the ranker and use the deterministic production fallback.
