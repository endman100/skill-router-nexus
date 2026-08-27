---
name: long-video-understand
description: Analyze local video files with the pinned VideoChat3-4B model using memory-bounded temporal chunking, resumable checkpoints, timestamped segment descriptions, and hierarchical summaries. Use when Codex must understand, summarize, inspect, or answer questions about short or long MP4/MKV/MOV/WebM videos, especially when a full video cannot fit GPU memory at once.
---

# Long Video Understanding

Run the bundled wrapper to analyze real video frames with VideoChat3. Keep model weights and Hugging Face remote code in the shared cache; never copy the upstream repository or weights into this skill.

## Workflow

1. Resolve the local video path and the user's question or desired summary.
2. Run `python scripts/doctor.py`. Read `references/runtime.md` only if a dependency, CUDA, memory, or download check fails.
3. Run one model process at a time. Do not parallelize segments because every process loads the model again.
4. Analyze with:

   ```powershell
   python scripts/longvideo_understand.py "C:\path\video.mp4" --prompt "Create a timestamped summary and identify important events." --output "C:\path\analysis.json"
   ```

5. Inspect the JSON `final_answer`, `segments`, timing, model revision, and peak GPU memory. Report that the result describes sampled visual frames, not the audio track.
6. Re-run the same command to resume an interrupted job from completed segments. Use `--no-resume` only when intentionally replacing that checkpoint.

## Sampling choices

- Keep the defaults (`--chunk-seconds 120 --nframes 8 --max-pixels 100352`) for Windows SDPA and general long videos.
- Use `--chunk-seconds 30` to `60` for dense action or brief events.
- Use `--chunk-seconds 180` to `300` for lectures, meetings, or mostly static scenes.
- Increase `--nframes` before increasing `--max-pixels` when temporal coverage matters. Keep frame counts even.
- Use `--attention-backend auto`; it selects FlashAttention 2 only when installed, otherwise the tested PyTorch SDPA fallback.
- Reduce `--nframes` to `4` after CUDA out-of-memory errors. Never work around memory pressure by starting concurrent model processes.

## Guardrails

- Require a CUDA-capable NVIDIA GPU for practical inference.
- Keep `--model-revision` pinned unless the user explicitly requests testing a newer upstream revision.
- Treat `trust_remote_code=True` as a security boundary; the pinned code is downloaded from the model repository on first use.
- Preserve the JSON checkpoint because it makes long runs resumable and exposes what each time range contributed.
- State that VideoChat3-4B does not transcribe or reason over audio. Combine a separate ASR transcript only when the user requests audio-aware analysis.
