---
name: filmops-first-video-analysis
description: Route film-oriented video analysis through selected FilmOps operators before downstream interpretation or reference-video auto-prompting when camera language must be preserved. Use for shot scale, composition, camera angle, color and tone, character layout, camera movement, cinematic matching, 景別、構圖、運鏡、鏡位、人物站位、分鏡拆解、參考片轉提示詞. Do not use for transcript-only, subtitle-only, download-only, cutting, transcoding, content-only prompt extraction, or generic summaries without cinematographic requirements.
---

# FilmOps-first video analysis

Use FilmOps as a structured cinematic-evidence layer, not as a universal video analyzer or a complete FilmBench scorer. Its six operators cover shot scale, composition, camera angle, color and tone, character layout, and camera movement. Add other tools for dialogue, story, identity, action, audio, technical quality, safety, or editing rhythm.

## Apply the FilmOps gate

Run FilmOps before downstream analysis when at least one condition holds:

- The user explicitly asks for cinematographic attributes covered by FilmOps.
- A reference video must be converted into a shot list, style specification, storyboard, or generation prompt that should preserve camera language.
- The task compares a generated video with a prompt, storyboard, reference, or another video on cinematic execution.
- The task needs repeatable, structured, per-shot labels rather than only a qualitative summary.

Skip FilmOps when the task is limited to transcription, subtitles, downloading, trimming, transcoding, thumbnails, content-only summarization, object detection, or another dimension outside its taxonomy. For an ambiguous one-off request, explain the value and cost of FilmOps briefly, then choose the lightest method that can answer accurately.

Treat FilmOps as a preferred prerequisite, not an unconditional dependency. If its environment or fine-tuned checkpoints are unavailable, disclose that before analysis and use an explicit fallback such as shot extraction plus a capable Video-MLLM. Never imply that FilmOps ran when it did not.

## Prepare the footage

1. Obtain a local video path when the input is remote. Do not download or install large models without authorization.
2. Inspect duration, frame rate, resolution, codec, and audio presence.
3. Detect shot boundaries before cinematic analysis. FilmOps camera movement expects a shot-like clip; it does not perform shot detection.
4. Extract representative frames with timestamps from each shot. Use enough frames to detect changes without treating adjacent duplicates as independent evidence.

When FilmOps is configured:

1. Resolve and record the FilmOps repository or installed-package root; do not assume the current directory.
2. Confirm that the active Python environment can import `filmops`.
3. Use the repository's verification script as a checkpoint inventory only. File existence does not prove that a model can load or infer.
4. Load and run a smoke inference for every operator selected for this task before starting a long analysis.

From a verified FilmOps repository root, the inventory command is:

```bash
python <FILMOPS_ROOT>/scripts/verify_install.py --ckpt-dir <checkpoint-dir>
```

Do not assume the bundled downloader supplies all fine-tuned weights. If import, load, or smoke inference fails, record the failed operator and checkpoint, then continue only with an explicitly named fallback.

## Run per-shot analysis

Select only the operators needed by the request:

| Requested evidence | Operator |
| --- | --- |
| 景別 / shot size | `shot_scale` |
| 構圖 / framing | `composition` |
| 鏡位、俯仰、荷蘭角 | `camera_angle` |
| 色調、色溫、飽和度 | `color_tone` |
| 人物站位、朝向、前後景 | `character_layout` |
| 運鏡 / camera motion | `camera_movement` |

Run all six only for a full cinematic-language breakdown or when every dimension is genuinely needed downstream. For each detected shot:

1. Run selected frame-level operators on representative frames.
2. Run `camera_movement`, when selected, on the isolated shot clip rather than indiscriminately on a multi-shot sequence.
3. Preserve raw per-frame results and timestamps before deriving a shot summary.
4. Mark a label as stable only when it is supported across representative frames or by a clearly identified keyframe. Preserve conflicts and uncertainty instead of forcing consensus.

Use additional analyzers only for missing dimensions. Examples include ASR for dialogue, shot detection for segmentation, tracking or embeddings for cross-shot identity, Video-MLLMs for narrative and action, and technical metrics for flicker, compression, or temporal quality.

## Produce a structured handoff

Return a machine-readable evidence object before writing prose or prompts. Adapt fields to the task, but preserve provenance and observed-versus-inferred status.

```json
{
  "source": {"path": "...", "duration_s": 0, "fps": 0},
  "analysis_backend": {
    "filmops_status": "used|partial|unavailable|not_needed",
    "filmops_revision": "...",
    "operators": [
      {"name": "shot_scale", "checkpoint_revision": "...", "smoke_test": "passed"}
    ],
    "fallbacks": [],
    "errors": []
  },
  "shots": [
    {
      "shot_id": 1,
      "start_s": 0.0,
      "end_s": 0.0,
      "frames": [
        {
          "timestamp_s": 0.0,
          "operator_results": {"shot_scale": {"labels": [], "raw": {}}}
        }
      ],
      "observed": {
        "shot_scale": [],
        "composition": [],
        "camera_angle": [],
        "color_tone": [],
        "character_layout": [],
        "camera_movement": []
      },
      "confidence_notes": [],
      "inferred": {}
    }
  ]
}
```

Do not present an overall FilmBench score unless a separate, verified scoring pipeline actually produced it. FilmOps labels alone are not a FilmBench score.

## Generate an auto-prompt

Generate a prompt only when the user requests one or when it is an explicit downstream step.

1. Build the prompt shot by shot from the structured evidence.
2. Use stable FilmOps observations as camera-language constraints: duration, shot scale, angle, composition, camera movement, color and tone, and character blocking.
3. Add subject, action, environment, dialogue, audio, lighting, editing, and narrative intent from other verified analyzers or user input.
4. Keep observed facts separate from creative additions. Label additions as inferred or proposed.
5. Do not turn low-confidence or conflicting labels into hard prompt requirements.
6. Preserve the target generator's required syntax only after the evidence layer is complete; then hand off to the appropriate model-specific prompt skill.

Preferred shot-prompt order:

```text
[time range] + subject/action + shot scale + camera angle + composition
+ camera movement + character blocking + color/lighting/style + dialogue/audio
```

## Report limitations

Always state:

- Which FilmOps operators actually ran.
- Which dimensions came from fallback models or inference.
- Any missing checkpoints, failed operators, uncertain shot boundaries, or conflicting labels.
- That FilmOps specializes in cinematic language and does not replace complete semantic, narrative, audio, continuity, or technical-quality analysis.
