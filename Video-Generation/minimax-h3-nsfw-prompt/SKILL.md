---
name: minimax-h3-nsfw-prompt
description: "Use when running the MiniMax H3 Ref2VA pic1ref 5 s anime action-clip workflow: which graph nodes to change per case, the LoRAs in use, the prompt template, building the final prompt with build_prompt.py, and how to fill the 13 variables."
---
# MiniMax H3 Ref2VA pic1ref action-clip workflow

Produces a 2D anime action clip (default 5 s) from four references: a woman identity image, a man reference image, a first/last-frame still of the action, and an audio reference. Per action, only the still and the prompt variables change; the rest of the graph stays fixed.

This skill covers only the workflow and the prompt, not machine operation. This workflow is a single-shot 5 s variant; where general H3 prompt rules (for example `h3-prompt-writing`) conflict with it, this skill wins (for example, here `<Picture 1>` is the identity image, not a storyboard).

A Chinese version of this skill is in `SKILL_CH.md` in this folder.

## 1. Graph

Use `workflow_api_template.json` in this folder (ComfyUI API format) as is. Per case, change only these nodes:

| node | input | value |
|---|---|---|
| 35 | `image` | the action still filename (also used as first/last frame and `<Picture 3>`) |
| 25 | `value` | the final prompt from `build_prompt.py` |
| 22 | `filename_prefix` | `video/<set>/<case>` |
| 80 | `image` | woman identity image (`<Picture 1>`); change only when switching the woman character |
| 45 | `image` | man character sheet (`<Picture 2>`); change only when switching the man character |
| 26 | `audio` | voice reference (`<Audio 1>`); change only when switching the voice |

Default length is 5 s: node 1 `length` 124 at 24 fps (already set in the JSON).

LoRAs in use (already in the JSON; strength_model = strength_clip):

| LoRA | source | weight |
|---|---|---|
| `minimax_h3_PDMD_DMAD_4step_r256_add_fro1_turbo_lora.safetensors` | [Civitai](https://civitai.com/models/2929860?modelVersionId=3385247) | 1.0 |
| `2dan1m_fl2va_768-000000.safetensors` | [Civitai](https://civitai.com/models/2860624?modelVersionId=3259966) | 0.6 |
| `gzani/Motion_Repair_V2.safetensors` | [Civitai](https://civitai.com/models/2890788/bunny-general-motion-continuity-repair) | 0.5 |
| `gzani/Minimax_H3_Unlocked_V2.1.safetensors` | [Civitai](https://civitai.red/models/2925727) | 0.8 |

## 2. Prompt template

Six fixed segments, English body; Chinese only inside `<d>...</d>`. The template is also saved as `template.txt` in this folder. The final prompt must be composed with `build_prompt.py`: put the 13 variables in a JSON file and run `python3 build_prompt.py vars.json -o prompt.txt`, then paste the result into node 25. Never fill the template by hand.

```text
subject_definitions:
<Subject 1> is the adult woman as she appears in <Picture 1>: {{female_appearance}}. {{female_outfit_exposure}}.
<Subject 2> is the adult man as he appears in <Picture 2>. {{male_outfit_exposure}}.
<Subject 3> is {{background}}.
<Picture 1> is the source for the woman's identity, face, hair, body, and outfit.
<Picture 2> is a weak reference for the man's general appearance only. Do not emphasize his face or upper body.
<Picture 3> is the third reference image: the opening frame, exact first and last frame, for composition, poses, framing, and camera angle.
<Audio 1> is the voice-timbre reference only for <Subject 1>. Use the breathy vocal quality and speaking style. Do not copy any unrelated words or dialogue from it.
summary:
[reference generation + first-frame lock + audio reference] 2d anime style, dynv2, continuation with bright lighting, high saturation, and vivid colors. {{background}}. She is {{pose_description}} {{character_position}} with {{female_expression}}. {{camera_angle}}. {{motion_description}}. {{camera_movement}}. Soft high-pitched breathy moans with onomatopoeia matching <Audio 1> timbre.
retention_analysis:
<Subject 1> (appears throughout [Shot 1]): fully_preserved - exact face, hair, body, and exposure from <Picture 1>.
<Subject 2> (appears throughout [Shot 1]): weak_reference.
<Subject 3> (appears throughout [Shot 1]): fully_preserved - {{background}}.
<Picture 1> (identity): fully_preserved.
<Picture 2> (identity): weak_reference - general appearance only, do not focus on face.
<Picture 3> (opening frame): fully_preserved.
<Audio 1>: reference - breathy vocal quality and speaking style only.
detailed_description:
[Shot 1] 2d anime style, dynv2, bright lighting, high saturation, vivid and colorful. {{background}}. {{camera_angle}} of the woman {{pose_description}} {{character_position}}. {{female_outfit_exposure}}. {{female_expression}}. {{motion_description}}. {{female_body_reaction}}. Continuous {{motion_type}}. {{camera_movement}}. It opens and ends on <Picture 3>. She produces soft high-pitched breathy moans mixed with onomatopoeia matching <Audio 1> timbre. She says: <d>[Chinese] {{dialogue}}</d>
overall_soundscape:
Quiet room tone, clear wet thrusting, skin slapping, and impact sounds synced to the fast motion. Soft high-pitched breathy moans, onomatopoeia, and short spoken lines using <Audio 1> timbre.
non_diegetic_music:
N/A
```

Template history: the original version had a penetration-detail reference as `<Picture 3>` and the still as `<Picture 4>`. After the penetration reference was removed, only minimal edits were made: the two Picture 3 penetration lines and the "The penetration matches the appearance in <Picture 3>..." sentence in detailed_description were deleted, `<Picture 4>` became `<Picture 3>`, and `fourth reference image` became `third reference image`.

## 3. How to fill the 13 variables

| variable | rule | example |
|---|---|---|
| `female_appearance` | Face, hair color, hairstyle, eyes, skin tone, body type, breast size only; no clothing. Take it from `<Picture 1>` and keep it identical across actions | same face, long pink-to-orange hair with bangs, green eyes, fair skin, curvy body with large breasts |
| `female_outfit_exposure` | Garment type + color + which parts are exposed; covered parts still need garment and color. Take it from `<Picture 1>` | She wears a blue top with pink ribbon, blue skirt, black thigh-high socks, and red shoes, with breasts fully exposed and pussy exposed |
| `male_outfit_exposure` | Take clothing from `<Picture 2>` (never default to naked) and say what is pulled down or exposed | He wears a blue t-shirt and dark pants pulled down, with his cock fully exposed and already inside her |
| `background` | Plain text; name only the scene elements you want, never what you don't want | a simple room with white walls and light wooden floor |
| `pose_description` | Static description: body placement, hands, gaze, whether and where the genitals are inserted, which parts are visible, whether the man is partly visible. Use proper position terms (missionary, standing missionary, cowgirl position, reverse cowgirl position, doggy style, mating press, prone bone, spooning, standing carry, full nelson, piledriver, amazon position, upright straddle, etc.; other acts: fingering, handjob, footjob, grinding, just the tip, ejaculation, orgasm). Always state whether the man's face shows (male face out of frame / visible / partially visible). Be explicit about hands: palms on the wall, backs of hands on the wall, or fingers gripping an object | standing in a standing leg-up position, back pressed against the wall, one leg raised high, hands raised near shoulders with back of hands pressed against the wall, male face out of frame |
| `character_position` | Spatial relation to surrounding objects; say explicitly whether the body touches the floor or an object (lying on / sitting on / pressed against) so nobody floats | pressed against the white wall, body in contact with the wall |
| `camera_angle` | Never empty; viewing angle only, no movement; must name a focus (focused on ...); must be physically plausible for the body position | Side view, focused on her pussy and the penetration |
| `camera_movement` | Default to slight rotation and drift; describe sway, pan, rotation, etc. | Camera side view with slight handheld movement |
| `motion_type` | Short label for the action, using proper position terms | fast standing leg-up |
| `motion_description` | Dynamic description: how they move, thrust style, how the bodies sway with it, whether penetration stays connected throughout | He holds her raised leg with one hand, thrusting hard and fast from the front. Penetration stays connected throughout |
| `female_expression` | Pick one main expression (happy, scared, sad, angry, horrified, ahegao, exciting, estrus, naughty, moaning), then add at least two alternating dynamic ones (pout, raised eyebrow, nose blush, blush, half-closed eyes, biting lip, eyes briefly rolling up). Never only a static expression | ahegao with half-closed eyes and blush |
| `female_body_reaction` | Default breast bounce and ass bounce; add pussy opening and closing when visible | breasts bouncing, ass bouncing, pussy opening and closing with each thrust |
| `dialogue` | Mixed Chinese, Japanese and English; mostly onomatopoeia unless specific lines are given | 嗯……ah……嗯啊……んっ……ah…… |

### General writing rules
- Describe only what should appear; never write "don't show X".
- When the man's face isn't needed, keep him weak_reference and write male face out of frame.
- Keep the full prompt at 1000 English words or fewer.
