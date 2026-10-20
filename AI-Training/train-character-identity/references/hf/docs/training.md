# Training MOSS Serenity

How the model was trained, how to reproduce it, and how to continue it with more people. Back to
the [model card](../README.md).

Trainer: [maltrainer](https://github.com/malcolmamal/maltrainer), `train_moss_image_finetune.py`.
Its own guides go deeper: `docs/finetune-tutorial.md` (a walkthrough from install to the finished
model) and `docs/moss-image-finetuning.md` (every setting).

## What was trained

| | |
|---|---|
| Base | MOSS-Image Base, bf16 (`moss_image_base_bf16.safetensors`) |
| Trained | the Linear weights of the 42 joint blocks: 4.76B of 5.08B parameters |
| Frozen | the text adapter (its projection and 2 blocks), norms, biases, embedders, modulation, output head |
| Steps | 24,000 at batch size 1, about 25 epochs |
| Resolution | 512 px area, aspect buckets on a 16 px grid |
| Optimizer | Automagic3, fused (each weight steps inside backward, so no full gradient set is held), stochastic rounding into bf16 |
| Learning rate | 1e-5, pinned (`learning_rate` = `automagic_min_lr` = `automagic_max_lr`) |
| EMA | 0.999, updated every 4 steps, no warmup, in CPU RAM; the released file is the average |
| Timesteps | MOSS-Image's final-pretraining distribution: logit-normal, mean 1.09, std 0.95, truncated at sigma 0.95, 1% uniform, on the 1000-step grid |
| Caption dropout | 5% |
| Prior preservation | weight 1.0, 8 recorded inputs per image, every step |
| Regularisation | real photos of women and men, 0.2× the step |
| Hardware | one RTX 5090 (32 GB): ~1.3 s/step with prior and EMA, 24.9 GB peak VRAM |

**Why these choices:**

- **The text adapter stays frozen** (OpenMOSS's advice, and Fizgig's): it reads every prompt, so
  training it on a few hundred captions would change how all prompts are read.
- **A pinned 1e-5:** left to adapt, Automagic3's rate fell to ~2.5e-7 on MOSS-Image's flat loss,
  where a step moves a bf16 weight by a fraction of one rounding step and the change came out as
  noise. 1e-5 is Fizgig's finetune rate.
- **EMA 0.999:** at batch size 1 each step's direction comes from one image at one noise level, so
  the raw weights wander (the run's drift grew like a random walk). The long average keeps the
  learning and cancels the wandering. Previews of the raw weights changed look every few hundred
  steps; the EMA row changed slowly and steadily.
- **Prior preservation:** before step 1 the trainer records the original model's predictions for
  each image with its trigger replaced by the class word ("photo of feliciaday, a woman ..." →
  "photo of woman, a woman ..."). Each step then holds the model to them on that caption, so
  "a woman" without a trigger stays the base model's. Over the run the prior term drifted *down*
  (0.015 → 0.011): the people did not leak into the class words.

## Dataset

One folder per person, named after their trigger, with a `prefix.txt` that puts the trigger in
front of every caption:

```
datasets/finetunes/moss/        <- dataset.path
  people/
    prefix.txt                 "photo of [folder]"
    feliciaday/
      001.jpg
      001.txt                  "a woman with reddish-brown wavy hair smiling slightly, ..."
    keanureeves/
      ...
datasets/reg/                  <- dataset.reg_path
  women/  men/                 real photos of the class, captioned
```

- **Captions** are one natural sentence: who, expression, framing, pose, clothing, background,
  light. `[folder]` in `prefix.txt` becomes the folder name, so the caption trains as
  `photo of feliciaday, a woman with ...`.
- **Balancing** with `dataset.folder_repeats`: people who learned slowly ran at 3× per epoch, two
  who learned quickly at 0.5× (a random half of their images each epoch).
- **Encodings are cached** next to the images (`.maltrainer_cache/`), so restarts and resumes only
  encode what is new.

## The config

The relevant parts (paths shortened; the full template is maltrainer's
`templates/moss_image_finetune_template.yaml`):

```yaml
model:
  transformer_path: ".../diffusion_models/moss_image_base_bf16.safetensors"
  vae_path: ".../vae/flux2_vae.safetensors"
  text_encoder_path: ".../text_encoders/qwen3.5_9b_int8_convrot.safetensors"

dataset:
  path: datasets/finetunes/moss
  resolution: 512
  aspect_mode: bucket
  trigger: ''                # every image has a caption; a missing one trains on nothing
  default_caption: ''
  folder_repeats: {feliciaday: 3, keanureeves: 0.5}   # per person, as needed
  cache: true
  reg_path: datasets/reg
  reg_default_caption: a photo of a woman

finetune:
  trainable_prefixes: [layers.]
  linears_only: true

prior:
  weight: 1.0
  classes: {feliciaday: woman, keanureeves: man}      # every trigger: its class word
  samples_per_image: 8
  every: 1

train:
  batch_size: 1
  max_steps: 24000
  save_every: 0              # save on the s / q keys and at the end
  save_state: true
  timestep_distribution: logit_normal
  timestep_logit_mean: 1.09
  timestep_logit_std: 0.95
  timestep_cutoff: 0.95
  timestep_uniform_mix: 0.01
  optimizer: automagic3
  learning_rate: 1.0e-05
  automagic_min_lr: 1.0e-05
  automagic_max_lr: 1.0e-05
  automagic_fused: true
  ema_decay: 0.999
  ema_every: 4
  ema_warmup: false
  caption_dropout: 0.05
  reg_lr_multiplier: 0.2

sample:
  every: 500
  rows: [ema]
  prompts:
    - "photo of feliciaday, a woman smiling slightly, close-up with face visible, soft light from the front"
  steps: 30
  cfg: 3.0
  width: 1024
  height: 1024
```

## Running it

```bash
python train_moss_image_finetune.py --config my_run.yaml --suggest-steps     # max_steps for 22 epochs per person
python train_moss_image_finetune.py --config my_run.yaml --dry-run           # check the schedule
python train_moss_image_finetune.py --config my_run.yaml                     # train
python train_moss_image_finetune.py --config my_run.yaml --resume-from output/.../<name>_state
```

Keys while training: `s` save and continue, `q` save and stop, `p` pause, `e` preview menu, `h`
help.

### How this run went

- **Two stages.** The first 8,505 steps trained a smaller set: 482 samples per epoch, 136
  regularisation photos, prior recorded for 270 images. The dataset then grew to 2,465 samples per
  epoch, with more people and 432 regularisation photos, and the run resumed from its state:
  weights, optimizer, EMA and step count carried on, with a fresh epoch. The prior for the 444 new
  images was recorded from the original base model first (~5 minutes), for 714 in total.
- **Likeness** kept improving to the end: people present from the start were recognisable by step
  3,000-6,000 and refined after; people added at step 8,505 improved clearly between 12,000 and 24,000.
- **Health:** no NaN or inf gradients in 24,000 steps; loss flat by noise band, as expected for
  flow matching; prior term slowly falling.
- **Cost:** ~1.3 s/step at 512 px with prior preservation every step and EMA. Each save is a 10 GB
  model plus a ~35 GB resume state (raw weights, EMA, optimizer).

## Continuing it

To add people, photos or regularisation images to Serenity, there are two ways:

- **From the resume state** (exact): only the person who trained it has it. Add the new folders and
  their `prior.classes` entries, keep `model.transformer_path` on the original MOSS-Image Base (the
  prior for new images is recorded from it), raise `max_steps` (it counts from the start of the
  run), and resume.
- **From the released weights** (anyone): point `model.transformer_path` at
  `serenity_base_v1_24000_bf16.safetensors` and train as above. The optimizer and EMA start fresh,
  and prior preservation then records from Serenity itself, so it protects what Serenity does now
  rather than what the base model did.

## Converting to INT8 ConvRot

The INT8 file was made from the bf16 one with maltrainer's `scripts/convert_int8_convrot.py`, run
with ComfyUI's Python because it calls comfy-kitchen's own `quantize_int8_convrot_weight`:

```bash
<ComfyUI>/venv/Scripts/python.exe scripts/convert_int8_convrot.py serenity_base_v1_24000_bf16.safetensors serenity_base_v1_24000_int8_convrot.safetensors --reference moss_image_sft_int8_convrot.safetensors
```

The reference is any INT8 ConvRot file of the same architecture (here Comfy-Org's MOSS-Image SFT
release): it decides which Linears are quantized (each block's `qkv`, `o`, `ffn_up_gate`,
`ffn_down`: 168 in all) and supplies the blobs an INT8 release carries (each block's
`comfy_attention.config`). Everything else is copied from the bf16 file unchanged. The result has
the reference's exact layout (757 tensors), and the quantized Linears are within 0.88% of the bf16
weights on average (0.98% at most). The conversion takes seconds on a GPU.

Finetune, continue and extract LoRAs from the bf16 file; the INT8 one is for generating.

## Extracting the LoRAs

The [`lora-extract`](../lora-extract) files came from the difference between Serenity and its base:

```bash
python scripts/extract_lora.py moss_image_base_bf16.safetensors serenity_base_v1_24000_bf16.safetensors --rank 64 128 256
```

One SVD pass writes all three ranks (~4 minutes on the RTX 5090). By size, they drop 96% (r64),
93% (r128) and 87% (r256) of each layer's change, mostly the batch-1 noise described above.
