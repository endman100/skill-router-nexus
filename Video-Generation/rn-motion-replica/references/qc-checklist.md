# Reference Replica QC Checklist

## Reference evidence

- Confirm the selected start and end time.
- Verify duration, dimensions, fps, and codecs with `ffprobe`.
- Inspect the overview contact sheet.
- Inspect dense samples around entrances and transitions.
- Keep reference screenshots and source metadata private.

## Composition check

- Build the fully visible layout before animation.
- Confirm every card fits inside the canvas.
- Confirm connector paths sit behind cards.
- Confirm every connector and junction is hidden at time zero.
- Confirm the first subject is readable within the opening beat.
- Confirm later elements do not appear before their cue.
- Confirm no render-time clocks, unseeded randomness, or infinite repeats.

## Snapshot check

Capture explicit frames at the opening, state swaps, and transitions. For a transition at `T`, inspect at least `T - 0.1`, `T + duration / 2`, and `T + duration + 0.1`.

Reject:

- black or empty handoffs
- floating connectors or junctions
- clipped or missing text
- cards crossing the frame edge unintentionally
- unreadable low-contrast metadata
- two independent elements revealing at the same time without a reason

## Final-MP4 check

Run a media probe:

```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate,duration,nb_frames \
  -show_entries format=duration,size,bit_rate \
  -of default=noprint_wrappers=1 \
  <final.mp4>
```

Run a black-frame scan:

```bash
ffmpeg -hide_banner -loglevel info -i <final.mp4> \
  -vf "blackdetect=d=0.1:pix_th=0.02:pic_th=0.98" \
  -an -f null -
```

Generate a contact sheet from the final MP4. Inspect it separately from preview snapshots.

Require:

- requested resolution and fps
- duration within one frame of the intended timeline
- non-zero file size and playable video stream
- no unintended black interval
- readable opening, midpoint, transition, and final frame
- source-identifying content absent from the deliverable

The MP4 is the deliverable. Probe JSON and contact sheets are supporting QC evidence.
