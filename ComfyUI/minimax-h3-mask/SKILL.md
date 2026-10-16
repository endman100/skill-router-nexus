---
name: minimax-h3-mask
description: 記錄 ComfyUI MiniMax H3 灰階 mask 部分重繪的必要節點接線；用於 SetLatentNoiseMask、影片與音訊 mask 合併，以及 mask 強度控制。
---

# MiniMax H3 mask 接法

## 影片 mask

| 來源輸出 | 目標輸入 |
|---|---|
| 來源影片的 `GetImageSize.width` | `SolidMask.width` |
| 來源影片的 `GetImageSize.height` | `SolidMask.height` |
| `SolidMask.MASK`（例如 `value=0.6`） | `VHS_DuplicateMasks.mask` |
| 來源影片的 `GetImageSize.batch_size` | `VHS_DuplicateMasks.multiply_by` |
| 來源影片的 `VAEEncode.LATENT` | 影片 `SetLatentNoiseMask.samples` |
| `VHS_DuplicateMasks.MASK` | 影片 `SetLatentNoiseMask.mask` |
| 影片 `SetLatentNoiseMask.LATENT` | `LTXVConcatAVLatent.video_latent` |

## 音訊 mask 與合併

| 來源輸出 | 目標輸入 |
|---|---|
| 來源音訊的 `VAEEncodeAudio.LATENT` | 音訊 `SetLatentNoiseMask.samples` |
| 另一個 `SolidMask.MASK`（`value=1`、尺寸 `1×1`） | 音訊 `SetLatentNoiseMask.mask` |
| 音訊 `SetLatentNoiseMask.LATENT` | `LTXVConcatAVLatent.audio_latent` |
| `LTXVConcatAVLatent.latent` | `SamplerCustomAdvanced.latent_image` |

讓已附加 mask 的來源 latent 沿此路徑進入採樣器。

## mask 意義與實測條件

- `0`：保留來源 latent；`1`：允許完全重繪；中間值（如 `0.6`）：灰階強度的部分重繪。
- 全畫面 `0.6` 表示全畫面使用該強度，不是選取 60% 面積，也不等於 `denoise=0.6`。
- 音訊 mask 為 `1` 表示允許重繪音訊。
- 使用者實測：此方法需停用 Turbo，並使用足夠的採樣步數；步數過少會讓部分重繪效果不如預期，不能因此判定灰階 mask 無效。
