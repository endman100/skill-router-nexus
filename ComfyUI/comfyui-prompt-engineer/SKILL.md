---
name: comfyui-prompt-engineer
description: Interview for creative intent and craft prompts for the exact image, video, audio, or multimodal model used in a ComfyUI workflow. Use when creating, refining, or debugging model-specific prompts and generation settings.
---

# Prompt engineering for ComfyUI

Prompt for the exact model and conditioning path. Do not apply one model family's syntax to another.

## Brief interview

Ask only for missing decisions that materially affect the result:

1. subject and action
2. composition, camera and duration
3. style, mood, lighting and color
4. identity/reference constraints
5. required text, dialogue or audio
6. target model/workflow and output dimensions
7. unacceptable elements

Stop asking once the workflow can be specified. Then return the prompt, any supported negative conditioning, recommended workflow controls, and the assumptions made.

## Model-aware rules

Read the current publisher or ComfyUI tutorial for the selected model.

- Natural-language image models: use clear scene prose, spatial relationships, lighting and camera intent.
- Tag-oriented checkpoints: use the vocabulary and weighting syntax documented for that checkpoint.
- Text-rendering models: quote exact required text and describe placement, typography and hierarchy.
- Video models: describe subject motion, camera motion, temporal progression and what must remain stable.
- Audio or speech models: separate spoken content from delivery, speaker traits, pacing and production notes when the model supports those fields.

Do not add a generic negative prompt automatically. Some architectures ignore negative conditioning or respond poorly to long negative lists. Use negative conditioning only when the actual workflow and model support it.

## Prompt debugging

1. Verify the intended model, encoders, VAE and conditioning nodes.
2. Reproduce with a fixed seed and minimal graph.
3. Remove conflicting style and composition clauses.
4. Move critical constraints earlier and make spatial relationships explicit.
5. Test one change at a time.
6. Use workflow controls such as masks, reference images or ControlNet when language alone cannot enforce geometry.

## Output format

Return:

- model/workflow assumption
- positive prompt or model-specific fields
- negative conditioning only if supported
- relevant generation controls
- unresolved risks
- one compact alternate prompt when useful

Do not promise exact identity, typography or motion from prompt wording alone.
