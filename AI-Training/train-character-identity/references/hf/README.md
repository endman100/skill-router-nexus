---
license: apache-2.0
base_model: OpenMOSS-Team/MOSS-Image-Base
base_model_relation: finetune
pipeline_tag: text-to-image
tags:
  - moss-image
  - text-to-image
  - comfyui
  - full-finetune
  - people
---

# MOSS Serenity

**MOSS Serenity** is a full finetune of [MOSS-Image Base](https://huggingface.co/OpenMOSS-Team/MOSS-Image-Base)
that teaches the model a set of people by name, while keeping what the base model already knows.
It was trained for 24,000 steps on a single RTX 5090 with [maltrainer](https://github.com/malcolmamal/maltrainer).

It is a drop-in replacement for MOSS-Image Base: the same architecture, text encoder
(Qwen3.5-9B) and VAE (FLUX.2), so any MOSS-Image workflow in ComfyUI runs it unchanged.

<table>
  <tr>
    <td><img src="samples/scenes-50steps/keanureeves_john_wick_50steps_00001_.png" alt="keanureeves"></td>
    <td><img src="samples/scenes-50steps/gilliananderson_x_files_50steps_00001_.png" alt="gilliananderson"></td>
  </tr>
  <tr>
    <td><img src="samples/scenes-50steps/anyataylorjoy_queens_gambit_50steps_00001_.png" alt="anyataylorjoy"></td>
    <td><img src="samples/scenes-50steps/jasonmomoa_aquaman_50steps_00001_.png" alt="jasonmomoa"></td>
  </tr>
  <tr>
    <td><img src="samples/scenes-50steps/jennaortega_wednesday_50steps_00001_.png" alt="jennaortega"></td>
    <td><img src="samples/scenes-50steps/nathanfillion_firefly_50steps_00001_.png" alt="nathanfillion"></td>
  </tr>
  <tr>
    <td><img src="samples/no-people/alpine_sunrise_50steps_00001_.png" alt="alpine valley"></td>
    <td><img src="samples/no-people/rural_town_50steps_00001_.png" alt="rural village"></td>
  </tr>
</table>

More in [`samples/`](samples): [`portraits`](samples/portraits) (8-step street portraits),
[`scenes`](samples/scenes) (8-step film scenes), [`scenes-50steps`](samples/scenes-50steps) (Full HD, 50 steps),
[`pairs`](samples/pairs) (two people), [`trios`](samples/trios) (three people) and [`no-people`](samples/no-people).

## Files

| File | What |
|---|---|
| [`serenity_base_v1_24000_bf16.safetensors`](serenity_base_v1_24000_bf16.safetensors) | the finetuned DiT, bf16, ComfyUI single file (10.2 GB): the EMA average of the weights at step 24,000 |
| [`serenity_base_v1_24000_int8_convrot.safetensors`](serenity_base_v1_24000_int8_convrot.safetensors) | the same model in ComfyUI's INT8 ConvRot format (5.4 GB): half the size and faster, within ~1% of the bf16 weights |
| [`lora-extract/serenity_v1_lora_r64.safetensors`](lora-extract) | the finetune as a LoRA for MOSS-Image Base, rank 64 (0.3 GB) |
| [`lora-extract/serenity_v1_lora_r128.safetensors`](lora-extract) | rank 128 (0.6 GB) |
| [`lora-extract/serenity_v1_lora_r256.safetensors`](lora-extract) | rank 256 (1.2 GB) |
| [`workflow/base-turbo-no-lora.json`](workflow) | ComfyUI workflow: 8 steps with the DMD turbo LoRA |
| [`workflow/base-no-turbo-no-lora.json`](workflow) | ComfyUI workflow: 50 steps, no turbo |
| [`workflow/base-turbo-lora.json`](workflow) | ComfyUI workflow: turbo, plus a person LoRA of your own in the Power Lora Loader |
| [`workflow/lora-extract-turbo-lora.json`](workflow) | ComfyUI workflow: the original MOSS-Image Base + `serenity_v1_lora_r256` + turbo, 12 steps |
| [`docs/generating.md`](docs/generating.md) | generating with the model: setup, settings, prompting |
| [`docs/training.md`](docs/training.md) | how it was trained, and how to train or continue it |

The text encoder and VAE are MOSS-Image's own: Qwen3.5-9B (`qwen3.5_9b_int8_convrot.safetensors`,
or [`qwen3.5_9b_bf16.safetensors`](https://huggingface.co/Comfy-Org/Qwen3.5/blob/main/text_encoders/qwen3.5_9b_bf16.safetensors))
in `models/text_encoders`, and the FLUX.2 VAE (`flux2_vae.safetensors`) in `models/vae`.

## Quick start (ComfyUI)

1. Put `serenity_base_v1_24000_bf16.safetensors` (or the smaller `serenity_base_v1_24000_int8_convrot.safetensors`)
   in `ComfyUI/models/diffusion_models/`.
2. Drag one of the [workflows](workflow) into ComfyUI and pick the model in **Load Diffusion Model**.
3. Prompt `photo of <trigger>, a woman, ...` (see [Prompting](#prompting)).

| | Turbo (fast) | Full (best detail) |
|---|---|---|
| Extra LoRA | lodestones' [`MOSS-Image-Base-8-steps-dmd`](https://huggingface.co/lodestones/MOSS-Image-Base-8-steps-dmd) at 1.0 | none |
| Steps | 8 | 50 (20 is close for landscapes) |
| CFG | 4.0 | 4.0 |
| Sampler / scheduler | euler / simple | euler / simple |
| SkipLayerGuidanceDiTSimple | layer 22, start 0, end 0.5 | layer 22, start 0, end 0.5 |
| Negative | `bad ugly blurry` | `bad ugly blurry` |
| Size used for the samples | 1584 × 1776 | 1920 × 1088 |
| Time on an RTX 5090 | ~16 s | ~62 s at 1920 × 1088 (~25 s at 20 steps) |

Shift needs no node: ComfyUI runs MOSS-Image at shift 5. Full details in
[docs/generating.md](docs/generating.md).

**bf16 or INT8 ConvRot?** Same model, same workflows: pick the file in **Load Diffusion Model**. The
INT8 file stores each block's big Linears as int8 in a Hadamard-rotated basis with one scale per
row (ComfyUI's INT8 ConvRot, as in Comfy-Org's `moss_image_*_int8_convrot` releases), so it is half
the size and runs on comfy-kitchen's int8 kernels. Its weights are within 0.9% of the bf16 ones
(mean relative error per Linear), and on the same seed it renders a near-identical image: the turbo
workflow took 8.7 s including loading, against ~16 s for bf16, on an RTX 5090. Keep the bf16 file
for finetuning, merging and LoRA extraction.

## Prompting

The model learned each person from captions of one shape, so prompts work best in that shape:

```
photo of <trigger>, a <woman|man>, <one sentence: look, framing, clothing, setting, light>
```

```
photo of gilliananderson, a woman with shoulder-length straight auburn red hair, a serious focused
expression, medium close-up from the chest up, holding a small flashlight raised beside her face,
wearing a dark charcoal 1990s pantsuit jacket over a white blouse, standing in a dark abandoned
warehouse corridor at night, cold blue moonlight, 1990s film grain, cinematic film still
```

- **Keep faces large.** Chest-up and closer gives the best likeness; full-body shots with a small
  face can come out wrong.
- **Describe the look, not the title.** The model knows the people, not their films: "a long brown
  leather duster coat in the cargo bay of a worn frontier spaceship" works, a film title does not.
- **Two people: a man and a woman work well; two of the same gender are hit-or-miss.** See
  [Two people in one shot](#two-people-in-one-shot) and [Three people](#three-people-in-one-shot).
- Without a trigger, `photo of a woman, ...` gives an ordinary person, as in the base model.

## Characters

Each trained person is prompted with a **trigger**: their name in lower case, without spaces, put
first after `photo of`, then the class word they were trained with:

```
photo of keanureeves, a man, ...
```

The samples below were made with the workflows in [`workflow/`](workflow): **(50)** marks the full
model at 50 steps and 1920 × 1088; the rest are the 8-step turbo workflow at 1584 × 1776.

| Trigger | Class | Who | Samples |
|---|---|---|---|
| `alisonbrie` | woman | Alison Brie | [street portrait](samples/portraits/alisonbrie_b_00001_.png), [Community](samples/scenes/alisonbrie_community_00001_.png), [GLOW](samples/scenes/alisonbrie_glow_00001_.png), [GLOW (50)](samples/scenes-50steps/alisonbrie_glow_50steps_00001_.png) |
| `amberrayne` | woman | Amber Rayne | [film noir street (50)](samples/scenes-50steps/amberrayne_noir_street_50steps_00001_.png) |
| `anyachalotra` | woman | Anya Chalotra | [street portrait](samples/portraits/anyachalotra_b_00001_.png), [The Witcher (50)](samples/scenes-50steps/anyachalotra_witcher_50steps_00001_.png) |
| `anyataylorjoy` | woman | Anya Taylor-Joy | [street portrait](samples/portraits/anyataylorjoy_b_00001_.png), [The Queen's Gambit](samples/scenes/anyataylorjoy_queens_gambit_00001_.png), [The Queen's Gambit (50)](samples/scenes-50steps/anyataylorjoy_queens_gambit_50steps_00001_.png) |
| `asmongold` | man | Asmongold, streamer | [streaming (50)](samples/scenes-50steps/asmongold_stream_gaming_50steps_00001_.png), [stream reaction](samples/scenes/asmongold_stream_reacting_00001_.png) |
| `aubreyplaza` | woman | Aubrey Plaza | [street portrait](samples/portraits/aubreyplaza_b_00001_.png), [The White Lotus](samples/scenes/aubreyplaza_white_lotus_00001_.png), [The White Lotus (50)](samples/scenes-50steps/aubreyplaza_white_lotus_50steps_00001_.png) |
| `bradpitt` | man | Brad Pitt | [street portrait](samples/portraits/bradpitt_b_00001_.png), [Troy (50)](samples/scenes-50steps/bradpitt_troy_50steps_00001_.png) |
| `emmawatson` | woman | Emma Watson | [Beauty and the Beast ballroom](samples/scenes/emmawatson_beauty_beast_00001_.png), [Hogwarts library (50)](samples/scenes-50steps/emmawatson_hogwarts_50steps_00001_.png) |
| `feliciaday` | woman | Felicia Day | [street portrait](samples/portraits/feliciaday_b_00001_.png), [The Guild](samples/scenes/feliciaday_the_guild_00001_.png), [The Guild (50)](samples/scenes-50steps/feliciaday_the_guild_50steps_00001_.png) |
| `gilliananderson` | woman | Gillian Anderson | [street portrait](samples/portraits/gilliananderson_b_00001_.png), [The X-Files (50)](samples/scenes-50steps/gilliananderson_x_files_50steps_00001_.png) |
| `helenmirren` | woman | Helen Mirren | [street portrait](samples/portraits/helenmirren_b_00001_.png), [RED](samples/scenes/helenmirren_red_00001_.png), [RED (50)](samples/scenes-50steps/helenmirren_red_50steps_00001_.png) |
| `jasonmomoa` | man | Jason Momoa | [Aquaman](samples/scenes/jasonmomoa_aquaman_00001_.png), [Aquaman (50)](samples/scenes-50steps/jasonmomoa_aquaman_50steps_00001_.png), [street portrait](samples/portraits/jasonmomoa_b_00001_.png) |
| `jennaortega` | woman | Jenna Ortega | [Wednesday (50)](samples/scenes-50steps/jennaortega_wednesday_50steps_00001_.png) |
| `jenniferlawrence` | woman | Jennifer Lawrence | [The Hunger Games](samples/scenes/jenniferlawrence_hunger_games_00001_.png), [The Hunger Games (50)](samples/scenes-50steps/jenniferlawrence_hunger_games_50steps_00001_.png), [Silver Linings Playbook](samples/scenes/jenniferlawrence_silver_linings_00001_.png) |
| `keanureeves` | man | Keanu Reeves | [street portrait](samples/portraits/keanureeves_b_00001_.png), [John Wick (50)](samples/scenes-50steps/keanureeves_john_wick_50steps_00001_.png) |
| `klaudiajachira` | woman | Klaudia Jachira, speaker | [parliament speech (50)](samples/scenes-50steps/klaudiajachira_parliament_50steps_00001_.png) |
| `mileycyrus` | woman | Miley Cyrus | [Flowers video](samples/scenes/mileycyrus_flowers_00001_.png), [Hannah Montana (50)](samples/scenes-50steps/mileycyrus_hannah_montana_50steps_00001_.png) |
| `morenabaccarin` | woman | Morena Baccarin | [Deadpool](samples/scenes/morenabaccarin_deadpool_00001_.png), [Firefly](samples/scenes/morenabaccarin_firefly_00001_.png), [Firefly (50)](samples/scenes-50steps/morenabaccarin_firefly_50steps_00001_.png) |
| `nathanfillion` | man | Nathan Fillion | [street portrait](samples/portraits/nathanfillion_b_00001_.png), [Castle](samples/scenes/nathanfillion_castle_00001_.png), [Firefly (50)](samples/scenes-50steps/nathanfillion_firefly_50steps_00001_.png) |
| `oliviawilde` | woman | Olivia Wilde | [street portrait](samples/portraits/oliviawilde_b_00001_.png), [House](samples/scenes/oliviawilde_house_00001_.png), [Tron (50)](samples/scenes-50steps/oliviawilde_tron_50steps_00001_.png) |
| `rihanna` | woman | Rihanna | [Ocean's 8 (50)](samples/scenes-50steps/rihanna_oceans_8_50steps_00001_.png) |
| `sadiesink` | woman | Sadie Sink | [street portrait](samples/portraits/sadiesink_b_00001_.png), [Stranger Things](samples/scenes/sadiesink_stranger_things_00001_.png), [Stranger Things (50)](samples/scenes-50steps/sadiesink_stranger_things_50steps_00001_.png) |
| `samuelljackson` | man | Samuel L. Jackson | [street portrait](samples/portraits/samuelljackson_b_00001_.png), [Nick Fury](samples/scenes/samuelljackson_nick_fury_00001_.png), [Pulp Fiction (50)](samples/scenes-50steps/samuelljackson_pulp_fiction_50steps_00001_.png) |
| `sashagrey` | woman | Sasha Grey | [street portrait](samples/portraits/sashagrey_b_00001_.png), [The Girlfriend Experience](samples/scenes/sashagrey_girlfriend_experience_00001_.png), [The Girlfriend Experience (50)](samples/scenes-50steps/sashagrey_girlfriend_experience_50steps_00001_.png) |
| `scarlettjohansson` | woman | Scarlett Johansson | [street portrait](samples/portraits/scarlettjohansson_b_00001_.png), [Black Widow](samples/scenes/scarlettjohansson_black_widow_00001_.png), [Black Widow (50)](samples/scenes-50steps/scarlettjohansson_black_widow_50steps_00001_.png) |
| `sweetanita` | woman | Sweet Anita, streamer | [streaming (50)](samples/scenes-50steps/sweetanita_stream_gaming_50steps_00001_.png) |
| `taylorswift` | woman | Taylor Swift | [street portrait](samples/portraits/taylorswift_b_00001_.png), [Eras Tour close-up 1 (50)](samples/scenes-50steps/taylorswift_eras_closeup_a_50steps_00001_.png), [Eras Tour close-up 2 (50)](samples/scenes-50steps/taylorswift_eras_closeup_b_50steps_00001_.png), [Eras Tour close-up 3 (50)](samples/scenes-50steps/taylorswift_eras_closeup_c_50steps_00001_.png), [Eras Tour stage (50)](samples/scenes-50steps/taylorswift_eras_tour_50steps_00001_.png) |
| `zendaya` | woman | Zendaya | [street portrait](samples/portraits/zendaya_b_00001_.png), [Dune (50)](samples/scenes-50steps/zendaya_dune_50steps_00001_.png) |

Scenes without people, at 50 steps: [alpine valley](samples/no-people/alpine_sunrise_50steps_00001_.png), [macro dragonfly](samples/no-people/macro_dragonfly_50steps_00001_.png), [Tokyo alley](samples/no-people/rainy_neon_alley_50steps_00001_.png), [rural village](samples/no-people/rural_town_50steps_00001_.png), [vintage cars](samples/no-people/vintage_cars_50steps_00001_.png).

### Two people in one shot

The training data had no group shots, yet two triggers in one prompt work well **for a man and a
woman**: each keeps their own face. Name both with their class word, put them on a side, and
describe each separately:

```
photo of nathanfillion, a man, and morenabaccarin, a woman, two people in the cockpit of a worn
frontier spaceship: on the left nathanfillion, a man with short dark hair and a wry smile, wearing a
brown leather duster coat over a red shirt; on the right morenabaccarin, a woman with long dark hair
pinned up in curls, wearing a flowing silk robe in deep jewel tones, ...
```

Samples (50 steps): [Firefly](samples/pairs/pair_firefly_nathan_morena_1_50steps_00001_.png), [helicarrier](samples/pairs/pair_helicarrier_samuel_scarlett_1_50steps_00001_.png), [Dune](samples/pairs/pair_dune_jason_zendaya_1_50steps_00001_.png), [ship's bow 1](samples/pairs/pair_ship_bow_keanu_jennifer_1_50steps_00001_.png), [ship's bow 2](samples/pairs/pair_ship_bow_keanu_jennifer_2_50steps_00001_.png), [diner](samples/pairs/pair_diner_samuel_rihanna_1_50steps_00001_.png).

**Two people of the same gender are hit-or-miss.** Some work: the
[stadium duet](samples/pairs/pair_duet_taylor_miley_1_50steps_00001_.png) and the
[palace audience](samples/pairs/pair_palace_helen_gillian_1_50steps_00001_.png) keep two distinct women.
Others don't: in [this library scene](samples/pairs/pair_library_emma_jenna_1_50steps_00001_.png) the
second woman has the right braids, collar and dress, yet a face pulled toward the first, and two men
[on a beach](samples/pairs/pair_surf_brad_keanu_1_50steps_00001_.png) do the same (the second loses most
of his likeness). Both triggers
share a class word (`a woman` or `a man`), which is likely where they meet. Costumes and hair always stay apart;
the faces are what can drift. Try several seeds, or render each person separately.

### Three people in one shot

The same rule holds with three: **faces stay distinct across class words, and drift within one.**

- **[One woman, two men](samples/trios/trio_matrix_keanu_olivia_samuel_1_50steps_00001_.png)** (a rainy
  city alley): all three keep their own faces.
- **[One man, two women](samples/trios/trio_firefly_nathan_morena_felicia_2_50steps_00001_.png)** (a
  spaceship cargo bay): the man is solid; the two women keep their costumes and hair, but their faces
  move partly toward each other.
- **[Three women](samples/trios/trio_hogwarts_emma_jenna_sadie_1_50steps_00001_.png)** (a castle dining
  hall): braids, red hair and house ties are all right, yet all three faces converge on the strongest
  identity of the three.

So for groups, mix genders where you can, and render same-gender groups with several seeds, or
person by person.

The film scenes describe each role's look (costume, hair, setting) rather than naming the film,
which the model does not know: see [docs/generating.md](docs/generating.md#prompting).

## The LoRAs

The [`lora-extract`](lora-extract) files hold the finetune as a LoRA for **MOSS-Image Base**: the
SVD of each layer's change, so they load on the base model and stack with other LoRAs. Use them
when you'd rather keep one base model and switch LoRAs. The workflow
[`lora-extract-turbo-lora.json`](workflow) is that setup: `moss_image_base_bf16` → `serenity_v1_lora_r256`
(1.0) → the DMD turbo LoRA → 12 steps, CFG 4, euler / simple.

They keep only part of each layer's change (by size, r64 drops 96%, r128 93%, r256 87%): at batch
size 1 much of a full finetune's change is step-to-step noise that no low rank captures. That noise
may not matter for likeness, but compare a LoRA with the full model on the same seed before
relying on it. The full model keeps everything.

## Training

Full finetune of MOSS-Image Base with [maltrainer](https://github.com/malcolmamal/maltrainer),
summarised here and in full in [docs/training.md](docs/training.md):

| | |
|---|---|
| Trained | the Linear weights of the 42 joint blocks (4.76B of 5.08B parameters); the text adapter, norms and embedders frozen |
| Steps | 24,000 at batch size 1 (~25 epochs), 512 px aspect buckets |
| Optimizer | Automagic3, fused into backward, rate pinned at 1e-5 |
| EMA | 0.999 (updated every 4 steps, no warmup); the released weights are the average |
| Prior preservation | weight 1.0: each trigger is also trained against the original model's output for its class word, so "a woman" / "a man" stay as they were |
| Regularisation | real photos of women and men at 0.2× the step |
| Timesteps | MOSS-Image's own final-pretraining distribution (logit-normal, mean 1.09, std 0.95, cutoff 0.95, 1% uniform) |
| Hardware | one RTX 5090 (32 GB): ~1.3 s/step, 24.9 GB peak |

## Responsible use

This model can produce the likeness of real people. Do not use it to deceive, to impersonate, to
harass, or to make sexual or demeaning images of anyone. Label generated images as generated.

## License

Apache 2.0, as MOSS-Image. The DMD turbo LoRA used in the turbo workflows is lodestones'
([lodestones/MOSS-Image-Base-8-steps-dmd](https://huggingface.co/lodestones/MOSS-Image-Base-8-steps-dmd)) and is not part of
this repository.
