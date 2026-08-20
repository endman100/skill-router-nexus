# Boundary Methodology

## Start Selection

The first lyric timestamp is evidence about the allowable range, not the cut itself. The start cut must satisfy all hard constraints:

1. It is earlier than the first lyric.
2. It is earlier than the start of the continuous music run associated with that lyric.
3. If an ASR cluster sits immediately before the music onset, move the anchor to the start of that cluster so the full non-lyric phrase remains inside the clip.
4. Find the end of the previous ASR cluster and search only the ASR-free gap before the anchor, capped at 5 seconds.
5. Do not place the cut inside an ASR phrase after applying 0.3 seconds of padding.

Use 0.4-second smoothed RMS only for local micro-placement after the semantic and detector constraints. Find local minima at or below the search window's 35th percentile and choose the qualifying trough nearest the anchor. If none exists, use the window minimum. RMS must not create song intervals or determine end boundaries.

## End Selection

The end boundary is harder because music tails, applause, talk-over-music, and detector persistence can look similar. Use a prebuilt candidate ranker only when its model metadata confirms compatibility with the current ASR, MusicDetection aggregation, feature schema, and boundary parameters and explicitly records independent generalization evidence. An in-sample fit is not production-compatible.

For compatible ranker inference:

1. Generate candidates every 0.25 seconds from the raw last lyric.
2. Stop at the earliest of 90 seconds after the last lyric, the next song start, or source duration.
3. Compute the exact versioned local ASR and MusicDetection feature vector expected by the model.
4. Select the highest positive score and the earliest candidate on an exact tie.
5. Record the model identifier, schema version, selected score, and inference range.

Do not use song identity, interval number, absolute program time, old cut distance, or any accepted annotation range at inference time.

If no compatible ranker exists, search at most 30 seconds after the last lyric for a stable non-music run of at least 2 seconds while avoiding ASR occupancy. Keep 0.3 seconds of ASR padding and at least 0.6 seconds of token-safe gap. Mark the result as deterministic fallback.

Ranker fitting, annotation collection, feature construction, and evaluation live only in [end-boundary-ranker-training.md](end-boundary-ranker-training.md).

## Confidence

Keep these confidence concepts separate:

- `technical verification`: FFprobe confirms media streams and duration.
- `detector confidence`: MusicDetection probability or low-music stability.
- `ranker score`: model probability for a candidate under the calibrated feature distribution.
- `semantic confidence`: Codex confidence that phrases belong to a title.
- `manual acceptance`: user-reviewed boundary range.

Never present one as another. A high ranker score does not prove a clip includes the full song, and a technically verified MP4 says nothing about semantic cut quality.
