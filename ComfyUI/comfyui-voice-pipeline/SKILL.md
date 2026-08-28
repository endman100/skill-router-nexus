---
name: comfyui-voice-pipeline
description: Design and validate speech, voice-cloning, audio-conditioning, and lip-sync stages used with ComfyUI while checking current node support, licenses, consent, and output compatibility.
---

# Build a voice stage for ComfyUI

Separate three concerns:

- speech generation or voice cloning
- audio cleanup and timing
- video conditioning or lip-sync

A tool that performs one stage is not automatically suitable for the others.

## Verify current support

1. Check the current ComfyUI release and audio tutorials.
2. Inspect /object_info for installed audio and video-conditioning nodes.
3. Verify the model or custom-node repository is maintained and supports the target ComfyUI/Python/PyTorch versions.
4. Verify model files, sample rate, channel layout, language support and license.
5. Run the tool's minimal official example before integrating it.

Do not assume Chatterbox, F5-TTS, RVC, Wav2Lip, ElevenLabs or another named tool is installed, maintained, commercially licensed or compatible. Do not recommend Wav2Lip for commercial work without resolving its licensing restrictions.

Current core or official-template support can change; discover it rather than maintaining a fixed preferred-tool ranking.

## Consent and safety

Obtain permission for voice cloning and preserve records of source and consent. Do not create deceptive impersonation. Disclose synthetic speech where required. Keep credentials outside workflow JSON.

## Audio contract

Record:

- spoken text and language
- reference-audio provenance
- target voice traits and delivery
- sample rate, channels, bit depth and loudness target
- duration and timing constraints
- output path and license

Normalize or resample once at a controlled boundary. Avoid repeated lossy encoding.

## Lip-sync integration

Confirm whether the target node accepts waveform, file path, audio object or features. Match its expected frame rate and sample rate. Test a short sentence with visible phoneme variation before a full render.

Keep the original video and audio. Treat lip-sync as a derived artifact and verify face identity, mouth artifacts, frame count, duration and audio/video drift.

## Completion check

Confirm consent, license, installed nodes, model hashes, successful minimal generation, audio metadata, workflow execution and synchronization on the final encoded output.
