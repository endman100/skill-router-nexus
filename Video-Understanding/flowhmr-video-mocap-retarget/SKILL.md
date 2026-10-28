---
name: flowhmr-video-mocap-retarget
description: Use when recovering physically plausible 3D human motion from a monocular video with FlowHMR (SMPL-H), or retargeting that motion onto Mixamo/VRM/PMX characters via RGB MoCap–style skeleton mapping, leg-scale root motion, and foot locking. Trigger on FlowHMR, HMR, SMPL-H, RGB MoCap, toyxyz mocap, video mocap, motion retarget, foot lock, 影片動捕, 動作重定向, 腳部鎖定. Do not use for Live2D/CMO3, pure video understanding/Q&A, or generative video models that invent motion without mesh recovery.
---

# FlowHMR video mocap and character retarget

Split the stack clearly:

- **FlowHMR** recovers global 3D human motion from a monocular video. It does **not** retarget to custom characters.
- **RGB MoCap** (or equivalent) takes FlowHMR (or similar) SMPL-H motion and retargets it to humanoid characters with optional foot locking.

## FlowHMR — what it does

HMR = Human Mesh Recovery. FlowHMR treats mocap as **video-conditioned motion generation**:

1. Pretrain a flow-matching motion model (MMDiT backbone from HY-Motion 1.0, ~0.46B).
2. Post-train with GRPO using rewards for video consistency and trackability by a physics controller (PHC+).

It aims for motions that both match the video and stay physically followable (reported high tracking success on Wild-4K vs GVHMR).

### Actual model I/O (important)

| Layer | What |
| --- | --- |
| User-facing input | Monocular **video** (internally resampled to 30 fps) |
| Model-facing inputs | Person tracks + **camera estimate** + **body features** from SAM 3D Body — **not** a finished mesh file the user supplies, and not raw pixels alone |
| Output | SMPL-H params: `poses` `(T, 52, 3)`, `trans` `(T, 3)` in `.npz`; optional `.fbx` if FBX SDK is present |

### Full local pipeline

1. **YOLOX** — detect and track people
2. **VGGT-Omega** — estimate camera (can skip / use static-camera mode for locked shots)
3. **SAM 3D Body** — extract body features (feature stage, not “bring your own 3D model”)
4. **FlowHMR** — generate SMPL-H motion
5. Optional `--postprocess` — temporal smoothing + foot–ground contact IK cleanup

Common knobs: `--seed`, `--cfg_scale` (default 1.0), `--steps` (ODE steps, default 20), `--vggt_interval` (trade VRAM), `--postprocess`. Prefer the GRPO checkpoint (`flowhmr_latest`) over base when available. Web demos often cap length (~900 frames / 30 s).

Environment notes from upstream: Python 3.10, PyTorch 2.5.x; SMPL family / VGGT-Omega / SAM 3D Body need license acceptance; GRPO training needs Isaac Gym + PHC+.

Sources:

- Repo: https://github.com/flowhmr/flowhmr
- Paper: https://arxiv.org/abs/2610.03691
- Project: https://flowhmr.github.io/

## RGB MoCap — retarget + foot lock (not FlowHMR)

Public Windows app by @toyxyz3 that wraps FlowHMR / ExMR / GVHMR and adds retarget. FlowHMR alone stays on the SMPL-H body.

### Retarget steps

1. Convert SMPL-H → 52-bone skeleton (root = Hips).
2. Auto-map ~22 body bones to Mixamo / VRM humanoid names or PMX Japanese names (no custom map in the documented app).
3. Scale root translation by **source vs target thigh+calf length ratio** (short-legged characters travel less).
4. Align legs to a shared reference pose, apply rotations; keep the target’s hierarchy and rest pose.
5. Contact correction: detect foot/hand contact spans → two-bone IK to pin feet; small horizontal root adjust; after lift-off, blend back to FK (~0.2 s). **Do not stretch bones** if the IK target is unreachable.
6. Bake (e.g. Blender) → FBX; PMX paths may export VMD for MMD.

### Practical UI / ops facts (RGB MoCap)

- Win64 + NVIDIA; models ≈ tens of GB on disk; FlowHMR is slower / hungrier than ExMR/GVHMR but often preferred for quality.
- Camera: Static Camera skips camera estimation for fixed shots.
- Motion correction: Flat Ground vs Multi Level; Lock Preset Weak / Normal / Strong; floor height & pelvis offset; timeline edit of L/R foot (and hand) lock regions.
- Caps: few characters per project (documented ≈ 8).

### Limits

- Body + fingers only; no hair / cloth / secondary physics.
- Extreme proportion gaps still need DCC cleanup.
- Contact is estimated → residual foot slide / penetration possible.
- Multi-person depth is approximate; no inter-person collision.
- Acrobat / airborne tricks: sometimes GVHMR wins; do not assume FlowHMR always wins.

Sources:

- Tool: https://github.com/toyxyz/toyxyz_RGBMocap
- Guide: https://github.com/toyxyz/toyxyz_RGBMocap/blob/main/docs/USER_GUIDE.md
- Example posts: FlowHMR Retarget Test https://x.com/toyxyz3/status/2114759528415944872 ; tool announce https://x.com/toyxyz3/status/2115030148840038608

## Decision guide

| Goal | Use |
| --- | --- |
| Video → 3D human motion (SMPL-H) | FlowHMR pipeline |
| Same motion on Mixamo / VRM / PMX anime or game character | FlowHMR (or peer) **then** RGB MoCap–style retarget |
| Arbitrary non-humanoid / custom skeleton | Out of scope without a custom bone map + DCC |
| “Any character automatically” | No — needs humanoid naming and tolerable proportions |

## Agent checklist

1. Clarify whether the user wants **recovery only** or **recovery + retarget**.
2. State that FlowHMR’s true conditioning inputs are tracks + camera + SAM 3D Body features, while the operator still starts from a video file.
3. For retarget, list target format (Mixamo FBX / VRM / PMX) and warn on proportion and physics limits.
4. Prefer citing upstream repos/paper over inventing APIs; if installing models, confirm licenses and GPU/disk needs first.
5. Keep FlowHMR vs RGB MoCap responsibilities separate in every answer.
