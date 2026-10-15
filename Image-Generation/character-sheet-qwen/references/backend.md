# Backend provenance and operation

Derived from the user's `image_qwen_image_2_1_image_edit (3).json`, inspected 2026-10-15 on ComfyUI 0.37.0/frontend 1.53.6, Python 3.12.8, PyTorch 2.14.0+cu130, RTX 5090 32 GB. Recheck live capabilities before use.

The supplied workflow initially used the derivative `redqw21UNLOCKEDV2TI2I_redqw21UNLOCKEDV2_fp8.safetensors`. The default now uses the installed base `qwen_image_2.1_int8_convrot.safetensors`, matching the real character case tested below. Retain the supplied Qwen3-VL encoder, matching VAE, DEIS/Beta, 25 steps, CFG 3, denoise 1. The supplied LoRA was bypassed; this graph contains no LoRA. Set cache device to auto instead of forcing gpu. Replace resolution selector/switch with direct EmptyLatentImage dimensions, matching the supplied graph's selected branch. Replace advanced save/audio notifications with core SaveImage. All nodes belong to the target ComfyUI core.

TextEncodeQwenImage21 returns a 64-channel latent matching its first reference; the supplied workflow selects a separate EmptyLatentImage instead, allowing arbitrary framing. The installed model's empty-latent processing supplies the appropriate channels. Large aspect-ratio changes can shift edit alignment; inspect results and match reference aspect ratio for targeted repair. Width/height must be multiples of 32. Default square outputs match the supplied configured size; body candidates may use 768×1344 after composition review.

Reference inputs use flat API keys `images.image_1` through `images.image_16`, not a nested dictionary or image batch. Each slot takes only the first batch image. Check actual names/capacity in object_info every run.

Override settings in a case-specific backend.json. The supplied derivative remains an explicitly selectable alternative, not an automatic fallback. A model/encoder change requires new inference validation. No hosted generation fallback or model download is implicit.

The client queues at the tail and never interrupts, clears, cancels, unloads, or restarts. Polling timeout preserves the prompt ID; resume monitoring with `--resume` and the same output. After an uncertain POST outcome, inspect queue/history before resubmission. Do not replay automatically.

The attached file's scene prompts and image filenames are reference material for a different task. They are not carried into this distributable skill. All new prompts concern isolated sheet assets.

## Inference evidence, 2026-10-15

Three local inference calls completed with successful ComfyUI history and downloaded PNGs: one original-reference front with the supplied derivative model, a two-image targeted repair (original plus rejected target), and an original-reference front using the alternative base Qwen 2.1 weights. All used 25 steps, CFG 3, DEIS/Beta, 1024×1024 outputs. No API fallback was used.

The test reference was a synthetic flat geometric robot. All three candidates failed strict design preservation: the first added human features/clothing, its repair retained those errors, and the base-model candidate retained some flat geometry but added hair/shoes and changed proportions. Preserve these as rejected candidates, not accepted sheet assets. Both checkpoint and instruction changed in the base comparison, so it does not isolate checkpoint effects. These runs establish transport/inference operation, not character likeness, expression accuracy, complete-sheet quality or repeated-run stability.

## Real character case, 2026-10-15

The user supplied one anime angel illustration. Fifteen Qwen 2.1 base-model calls produced a complete nine-asset 2875×1876 sheet after review: neutral anchor, front/profile/back, hands/shoes/outfit details, and happy/angry portraits. NORMAL is a byte-identical anchor copy. Five generated asset categories passed first review; four required repair or candidate selection. The case is one accepted design adaptation, not a repeatability benchmark.

Use 768×1344 for body views and 1024×1024 for portraits/details as a starting point. Short explicit Chinese transformation instructions with `<image1>`/`<image2>` roles accompanied the tested English templates. Every generation included the original reference. For stubborn detail framing, an additional inspected crop helped one shoe attempt; a subsequent sharpening attempt regressed and was rejected. Extra reference slots do not guarantee adherence.

The accepted final back used a case-specific Euler/simple, 40 steps, CFG 2.5 configuration after DEIS/Beta repairs retained front belt details and accumulated texture. It corrected the rear belt/collar; some cloth texture variation remained. Changing sampler, steps, CFG and instruction together does not isolate a causal improvement or justify changing all defaults.

Local compositing retained clean unaffected pixels when successful garment/cuff corrections degraded other regions. Inspected source crops removed broad near-white margins that confused automatic foreground detection. Original outputs, failed attempts, input logs, masks, crop boxes and hashes were retained. Back construction, upright unseen proportions and complete footwear were disclosed design inference; shoe lines remained softer than other details. Do not present inferred design as reference evidence.
