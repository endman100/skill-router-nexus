---
name: minimax-h3-image-pose-transfer-lora
description: 用於以 MiniMax-H3-Image 和 Pose Transfer v2 LoRA，將第一張圖的姿勢套用到第二張圖的人物或角色，並要求保留第二張圖的背景。涵蓋 ComfyUI 雙圖接線、提示詞、取樣設定與權重查核。
---

# MiniMax-H3-Image Pose Transfer LoRA

## 方法

- 用兩張圖片做指令式編輯。Picture 1 提供姿勢，Picture 2 提供要改姿勢的人物或角色及要保留的背景。作者工作流直接使用兩張影像，無骨架偵測、ControlNet 或遮罩接線。
- 依 MiniMax 官方模型卡，MiniMax-H3-Image 使用 H3 的 Qwen3-VL 編碼提示詞與參考影像，並以影像 VAE 編碼參考影像。33.1B、50 層的單流 DiT 以這些條件預測輸出 latent，再由 VAE 解碼。
- `LoraLoaderModelOnly` 以 `strength_model=1.0` 將 v2 LoRA 套到影像 DiT。權重標頭顯示 50 個 block 各有 attention 的 QKV／輸出投影和 MLP 的 `fc1`／`fc2` 更新，共 200 組低秩矩陣。

## 在 ComfyUI 使用

1. 匯入作者 JSON。工作流格式 `0.4`，記錄的 frontend 為 `1.58.5`，節點來自 `comfy-core` `0.45.0`／`0.45.2`。這些是匯出時的版本資料。節點缺失時依 ComfyUI 官方教學更新。
2. 按下表重選模型。`UNETLoader` 的 dtype 用 `default`，`CLIPLoader` 的 type 用 `minimax`、device 用 `default`。作者存檔中的子路徑與檔名依本機安裝而異。
3. 在 `Pose Reference - Picture 1` 與 `Target - Picture 2` 換成自己的圖。兩路各經 `ImageScaleToTotalPixels`，用 `lanczos` 和 32 px 尺寸步進。共用的 `Internal Megapixel Amount=4` 覆蓋兩個縮放節點內存的 `16`。
4. 兩路依序接到 `MiniMaxH3ImageConditioning` 的 `images.image_1`（姿勢）和 `images.image_2`（目標）。接上 CLIP、VAE 與 `PrimitiveStringMultiline`。`Reference or Target Output Dimensions` 經 `GetImageSize` 提供輸出寬高。JSON 的 `false` 取縮放後的姿勢圖，切到 `true` 取縮放後的目標圖。
5. `KSampler` 取套用 LoRA 的 model、conditioning 的 positive 和 latent，negative 接 `ConditioningZeroOut`。作者設定為 `lcm`、`simple`、6 steps、CFG `1.0`、denoise `1.0`。JSON 記錄 seed `115787125466567`，每次生成後隨機化。最後經 `VAEDecode` 和 `SaveImage` 儲存。

作者的英文提示詞如下。模型卡的 `instance_prompt` 是 `n/a`，工作流只送出這段指令。

> Put the person/character from Picture 2 into the reference pose shown in Picture 1. Preserve the background from Picture 2.

作者的 `pose-transfer_workflow.png` 內含 `prompt` 與 `workflow` metadata。內嵌範例用另一組輸入圖、seed `1054467597647090` 和 `switch=true`，取樣參數與 JSON 一致。

## 模型與檔案

| 元件 | 工作流選項和公開檔案 |
| --- | --- |
| DiT | `minimax_h3_image_pruned_int8_convrot.safetensors`，約 21.0 GB，放在 `models/diffusion_models/`。 |
| 文字編碼器 | 工作流選 `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`（約 15.7 GB），節點下載 metadata 指向 `qwen3vl_32b_minimax_h3_int8_convrot.safetensors`（約 27.1 GB）。兩個版本都能在 Comfy-Org 的檔案清單找到，放在 `models/text_encoders/`。 |
| VAE | 工作流選 `p-h3-image_vae_int8_convrot.safetensors`，該檔來源與大小未知／未公開（2026-11-27）。節點 metadata 與 ComfyUI 官方教學均指向公開的 `minimax_h3_image_vae_fp16.safetensors`（約 1.17 GB），放在 `models/vae/` 並在載入器重選。 |
| LoRA | 公開下載檔 `minimax-h3-image_pose-transfer_v2.safetensors` 約 298 MB（298,292,984 bytes，Xet），矩陣 BF16、alpha 純量 FP32，放在 `models/loras/`。將作者本機的 `h3image/pose_transfer_v2.safetensors` 重選為公開下載檔。 |

- 作者 repo 另有 `minimax-image_pose-transfer_workflow.json`（22.6 kB）、`pose-transfer_workflow.png`（4.53 MB）、`README.md`（1.47 kB）、`.gitattributes`（2.31 kB）與 `images/example01.jpg` 至 `example05.jpg` 五張示例。JSON 預選的 `pose029.jpg`、`pose007.png` 未隨 repo 提供，匯入後請換成自己的兩張圖。
- MiniMax 官方 BF16 影像發布包約 68.65 GB。官方模型卡另列 H3 text encoder 約 66.7 GB。上表為 Comfy-Org 的 ComfyUI 重封裝與作者工作流配置。

## 訓練、限制與授權

- 作者說明使用 Fizgig。v2 標頭記錄 rank `32`、alpha `32`、epoch `40`、`automagic4`、學習率欄位 `0.00025`、`modelspec.resolution=1024x1024`，以及訓練 adapter `fizgig_minimax_h3_image_training_adapter.safetensors`。Fizgig 的 adapter 用於訓練，作者推論圖只載入 Pose Transfer v2。
- 這項 LoRA 已公開權重與工作流。訓練資料來源、數量與配對方式、batch size、總步數、完整訓練設定與程式，以及專屬論文均未知／未公開（2026-11-27）。
- 作者回報偶有失敗，並觀察到 LoRA 有助於保留原角色的相似度。姿勢精度、人物與背景保留程度、多人物適用性、最低硬體需求及替換 VAE 的效果差異未知／未公開（2026-11-27）。
- **工程推論，論文／官方未驗證**。因工作流會經 DiT 生成整張圖，應以輸出檢查姿勢、人物和背景是否符合要求，尤其是需要背景逐像素一致時。
- HF 自動產生的 Diffusers 片段只傳文字。官方 Diffusers 影像編輯介面需傳實際參考圖，此 v2 權重的 Diffusers 載入相容性未知／未公開（2026-11-27）。
- LoRA 模型卡標示 `Apache-2.0`。MiniMax-H3-Image 與 Comfy-Org 重封裝權重適用 MiniMax-H3-Image Community License Agreement，包含地域、用途與再散布條件。依第 IV 節，年化營收超過 100 萬美元或向第三方提供託管服務須事先取得書面授權。該 LoRA 是否另獲 MiniMax 授權，及工作流與示例的單獨授權，未知／未公開（2026-11-27）。

## 來源

- [作者模型頁](https://huggingface.co/supermansundies/Minimax-H3-Image-Pose-Transfer-Lora) · [檔案列表](https://huggingface.co/supermansundies/Minimax-H3-Image-Pose-Transfer-Lora/tree/main) · [v2 權重](https://huggingface.co/supermansundies/Minimax-H3-Image-Pose-Transfer-Lora/blob/main/minimax-h3-image_pose-transfer_v2.safetensors)
- [作者 workflow JSON](https://huggingface.co/supermansundies/Minimax-H3-Image-Pose-Transfer-Lora/blob/main/minimax-image_pose-transfer_workflow.json) · [內嵌工作流的 PNG](https://huggingface.co/supermansundies/Minimax-H3-Image-Pose-Transfer-Lora/blob/main/pose-transfer_workflow.png) · [作者發布與回覆](https://www.reddit.com/r/StableDiffusion/comments/1y50mmr/minimax_h3_image_pose_transfer_lora/)
- [MiniMax 官方模型卡](https://huggingface.co/MiniMaxAI/MiniMax-H3-Image) · [官方授權](https://huggingface.co/MiniMaxAI/MiniMax-H3-Image/blob/main/LICENSE) · [Comfy-Org 權重](https://huggingface.co/Comfy-Org/MiniMax-H3-Image)
- [ComfyUI 官方教學](https://docs.comfy.org/tutorials/image/minimax/minimax-h3-image) · [ComfyUI conditioning 原始碼](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_minimax_h3.py) · [Diffusers 文件](https://huggingface.co/docs/diffusers/main/en/api/pipelines/minimax_h3_image)
- [Fizgig 訓練文件](https://github.com/shootthesound/Fizgig/blob/master/docs/MINIMAX_IMAGE.md) · [Fizgig 訓練 adapter](https://huggingface.co/ShootTheSound/Fizgig-MiniMax-H3-Image-Training-Adapter)
