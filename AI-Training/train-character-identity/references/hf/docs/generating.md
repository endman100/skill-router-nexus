# Generating with MOSS Serenity

Everything needed to run the model in ComfyUI, the settings the samples were made with, and how to
prompt it. Back to the [model card](../README.md).

## Files

| ComfyUI folder | File |
|---|---|
| `models/diffusion_models` | `serenity_base_v1_24000_bf16.safetensors` or `serenity_base_v1_24000_int8_convrot.safetensors` (this repository; the INT8 one is half the size and faster) |
| `models/text_encoders` | `qwen3.5_9b_int8_convrot.safetensors` (what the model trained with), or [`qwen3.5_9b_bf16.safetensors`](https://huggingface.co/Comfy-Org/Qwen3.5/blob/main/text_encoders/qwen3.5_9b_bf16.safetensors) |
| `models/vae` | `flux2_vae.safetensors` (the FLUX.2 VAE) |
| `models/loras` | optional: lodestones' [`MOSS-Image-Base-8-steps-dmd`](https://huggingface.co/lodestones/MOSS-Image-Base-8-steps-dmd) for the turbo workflows; the [extracted LoRAs](../lora-extract) |

Use the **Base** DMD LoRA, not the SFT one: Serenity was finetuned from MOSS-Image Base.

## The workflows

All four are in [`workflow/`](../workflow); drag one into ComfyUI and pick your own paths in the
loaders (the model and LoRA paths are the author's folders).

### Turbo: `base-turbo-no-lora.json`

Load Diffusion Model → Power Lora Loader (empty, for your own LoRAs) → Load LoRA (DMD, 1.0) →
SkipLayerGuidanceDiTSimple → KSampler.

| Node | Setting |
|---|---|
| Load CLIP | `qwen3.5_9b_int8_convrot`, type `moss_image` |
| Load LoRA (model only) | `MOSS-Image-Base-8-steps-dmd`, strength 1.00 |
| SkipLayerGuidanceDiTSimple | `single_layers` 22, `double_layers` empty, start 0.0, end 0.5 |
| Negative | `bad ugly blurry` |
| EmptyFlux2LatentImage | 1584 × 1776 |
| KSampler | 8 steps, CFG 4.0, euler, simple, denoise 1.00 |

About 16 s per image on an RTX 5090. This is the setup the portrait samples were made with: not
necessarily the best possible, but very good, and fast.

### Full: `base-no-turbo-no-lora.json`

The same without the DMD LoRA, at 50 steps:

| Node | Setting |
|---|---|
| SkipLayerGuidanceDiTSimple | layer 22, start 0.0, end 0.5 |
| Negative | `bad ugly blurry` |
| EmptyFlux2LatentImage | 1920 × 1088 (Full HD, on the 16 px latent grid) |
| KSampler | 50 steps, CFG 4.0, euler, simple |

On an RTX 5090 at 1920 × 1088: ~62 s at 50 steps, ~25 s at 20 (1.24 s per step either way).
Same seeds at 20 and 50 steps give the same composition; 50 adds fine structure (an insect's head,
lettering on signs, small figures). For landscapes 20 is close.

### Turbo with a person LoRA: `base-turbo-lora.json`

The turbo workflow with a separate person LoRA switched on in the **Power Lora Loader** (strength
1.0), for people Serenity was not trained on. MOSS-Image person LoRAs trained on Base load on top
of Serenity. Prompt them the way they were trained: this example's LoRA uses the class word as its
keyword, so the prompt starts `photo of a woman, ...` with no name trigger.

### Base + the extracted LoRA: `lora-extract-turbo-lora.json`

The original **MOSS-Image Base** (`moss_image_base_bf16.safetensors`) instead of Serenity, with
Serenity added back as a LoRA: Load Diffusion Model → Power Lora Loader (`serenity_v1_lora_r256`,
strength 1.0) → Load LoRA (DMD, 1.0) → SkipLayerGuidanceDiTSimple → KSampler at **12 steps**, CFG
4.0, euler / simple, 1584 × 1776, negative `bad ugly blurry`. For when you keep the base model
around and switch LoRAs. The LoRA keeps only part of the finetune (see
[The extracted LoRAs](#the-extracted-loras)); the full model is the reference.

### Notes

- **Shift:** ComfyUI already runs MOSS-Image at shift 5. To change it, add **ModelSamplingAuraFlow**
  before the KSampler. Not ModelSamplingSD3: its timestep scale is 1000× off for MOSS-Image.
- **Size:** keep both sides multiples of 16. Portrait (1584 × 1776) suits people; 1920 × 1088 suits
  scenes.
- **"widescreen" / "anamorphic" in a prompt** bake black letterbox bars into the image. Leave the
  words out if you don't want bars.

## The extracted LoRAs

To keep one base model and switch LoRAs (the
[`lora-extract-turbo-lora.json`](../workflow/lora-extract-turbo-lora.json) workflow does this at 12 steps): Load Diffusion Model `moss_image_base_bf16` → Power Lora Loader or Load LoRA
(`serenity_v1_lora_r256`, strength 1.0) → (DMD LoRA for turbo) → SkipLayerGuidanceDiTSimple →
KSampler, with the settings above. Higher ranks keep more of the finetune; compare with the full
model on the same seed.

## Prompting

### The shape

The captions were `photo of <trigger>, <one sentence>`, so prompts work best the same way:

```
photo of <trigger>, a <woman|man>, <look>, <expression>, <framing>, <clothing>, <setting>, <light>
```

The trigger is one lower-case word, the person's name without spaces (the list is in the
[model card](../README.md#characters)). The class word after it (`a woman`, `a man`) matches how
the model was trained.

### Examples

```
photo of jenniferlawrence, a woman with long dark brown hair in a single side braid, a determined
serious expression, looking slightly off-camera to her left, medium close-up from the chest up,
holding a wooden recurve bow with an arrow drawn, a quiver strapped over her shoulder, wearing a dark
green hooded hunting jacket over a gray shirt, standing in a dense misty pine forest, dappled
morning sunlight through the trees, cool green and amber tones, cinematic film still, shallow depth
of field
```

```
photo of nathanfillion, a man with short dark hair, a wry lopsided smile, standing in the cargo bay
of a worn frontier spaceship, wearing a long brown leather duster coat over suspenders and a red
shirt, a holstered pistol at his hip, warm amber light, medium shot, TV series still
```

```
photo of taylorswift, a woman with long blonde hair and bangs, bold red lipstick, a soft joyful
expression with her eyes looking toward the crowd, close-up of her face and shoulders, holding a
microphone near her chin, wearing a glittering silver sequined outfit, bokeh of thousands of
colorful wristband lights behind her, warm golden spotlight
```

### What works

- **Large faces.** Chest-up or closer. In a full-body stadium shot the face was a few dozen pixels
  and came out wrong; the same scene as a close-up was clean.
- **Describe the role, not the title.** The model knows the person, not the film. Costume, hair and
  setting make the scene: the side braid, bow and pine forest above read as a well-known role
  without naming it.
- **Name the hair when it matters.** A prompt that does not mention someone's signature hair can
  lose it (red hair especially).
- **Two people: a man and a woman work; two of the same gender are hit-or-miss.** Name both with their
  class word, place them (`on the left ...; on the right ...`) and describe each separately. A
  man and a woman keep their own faces; two women (or two men) always keep their costumes, but in some
  seeds their faces drift toward each other. Three people follow the same rule: one woman with two
  men holds, three women converge on one face. See [Two people in one shot](../README.md#two-people-in-one-shot)
  and [Three people in one shot](../README.md#three-people-in-one-shot).
- **No trigger, no person:** `photo of a woman, ...` gives an ordinary person; prior preservation
  kept the class words close to the base model.
- **Seeds:** likeness varies a little by seed; try a few.
