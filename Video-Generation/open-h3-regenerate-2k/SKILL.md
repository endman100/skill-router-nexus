---
name: open-h3-regenerate-2k
description: >-
  Use when upscaling or regenerating a MiniMax H3 (or other low-res) draft video
  to 2K with NVIDIA Open-H3-Regenerate-2K in ComfyUI. Marks Draft-Video → 2K as
  the preferred reasonable upscale path; default Sigmas to 2 steps to reduce
  face/identity drift. Trigger on Open-H3, Open-H3-Regenerate-2K, H3 2K
  upscale/regenerate, ComfyUI OpenH3Regen*, face drifting after 2K refine.
---

# Open-H3 Regenerate 2K（合理放大）

**判定：這是目前合理的 H3／草稿片放大方法**——用 NVIDIA 開源 [Open-H3-Regenerate-2K](https://nvlabs.github.io/Sana/Open-H3-Regenerate-2K/)（套件 `ComfyUI-Open-H3-Regenerate`）把低解析草稿**原生 regenerate 到 2K**，不是一般 pixel upscaler。內容、構圖、運鏡跟草稿；細節在 refine 重畫。

## 預設硬規則：Sigmas = **2 steps**（防臉跑掉）

| 設定 | 用途 |
| --- | --- |
| **`steps` 2**（預設） | σ `0.7 → 0.494 → 0`。較貼臉／身份；約快 30%。**本 skill 預設。** |
| `steps` 3（release） | σ `0.909 → 0.857 → 0.667 → 0`。官方表，細節更兇，**臉容易漂**——勿當預設。 |
| `start_sigma` 0.8（可選） | 啟用 shift-6 從 0.8 起；更貼草稿（官方 4K ladder）。仍漂再試 0.7。 |

節點：`Open-H3 Regenerate · Sigmas`。介面沒有獨立 shift 旋鈕；shift 寫死 6.0，由 `start_sigma>0` 啟用。

## Prompt

必須是 **MiniMax H3 格式**：

```
integrated_multimodal_description:
[Shot N] ...

overall_soundscape:
...

non_diegetic_music:
...
```

可用圖內 *Video to H3 Prompt (inference server)*（OpenAI 相容視覺 LLM），或把已知 H3 prompt 貼進 `manual_prompt`／`CLIPTextEncode`。**禁止只用一般散文描述當 refine prompt。**

## 執行步驟

1. 載入 workflow：`references/open-h3-regenerate-2k-draft-video.json`（Draft Video 圖；已接 **2-step** Sigmas）。
2. *Draft video* 換成要放大的 mp4（24 fps 佳）。
3. 確認 Sigmas 為 **2 steps**、`start_sigma` 0（或依需求 0.8）。
4. 填 H3 格式 prompt → Queue。
5. 成品：`output/video/open_h3_regen_2k_*.mp4`。若 decode 掛了，refined latent 已在 `output/open_h3_latents/`，改跑套件內 **Decode Saved Latent** 圖即可。

## 其他建議設定

- Prepare Draft：`768p`（H3 草稿）／`576p`（他模）；`max_frames` 121≈5 s。
- Latent Upscale：`2k (2560×1440)`；sampler **euler**；CFG 1；Open-H3 LoRA + Sharp curves；LBH 3D upscaler。
- VRAM：~32GB 卡 refine 常貼天花板；fast VAE 不夠時會 fallback 一般 H3 VAE（NestedTensor 需只解 video）。

## Needs

- `ComfyUI-Open-H3-Regenerate`
- `Comfyui_Minimax_h3_latent_Upscaler`（LBH 3D）
- FL2VA + `H3/Open-H3-Regenerate-2K/` LoRA／curve branches、H3 video/audio VAE、Qwen3-VL encoder

## 與兄弟 skill

| 需求 | Skill |
| --- | --- |
| **草稿 → 2K 合理放大（本配方）** | **this** |
| 手寫／改寫 H3 六段／Ref2VA prompt | `h3-prompt-writing` / `minimax-h3-prompt-rewriter-ref2va` |
| 固定 pic1ref 動作片圖 | `minimax-h3-nsfw-prompt` |
| 一般 Comfy workflow 建修 | `comfyui-workflow-skill` |
