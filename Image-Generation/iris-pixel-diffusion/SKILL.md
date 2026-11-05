---
name: iris-pixel-diffusion
description: 使用 Iris-3B（arXiv 2610.09450）的 pixel-space diffusion／無 VAE 文字轉圖片、單目深度估計與 4× 圖像修復超解析；包含官方權重下載、本機推論及 Iris-3B Turbo 四步生成。適用於部署 Iris-3B 或比較像素空間 generative prior 的下游效果。
---

# Iris-3B 像素空間生成

論文：[Iris-3B: Going Beyond the Latent with Pixel-Space Diffusion Training, Conversion and Fine-Tuning](https://arxiv.org/abs/2610.09450)。Iris-3B 是直接輸出 RGB 像素的 3B diffusion transformer，省去 VAE；文字編碼器另用凍結的 Qwen3-VL-4B-Instruct。採 16×16 patches、8 個 dual-stream + 16 個 single-stream blocks、4 個 PiT pixel-head blocks，以 rectified flow／v-prediction 經 256 → 512 → 1024 訓練，再做 SFT。深度與修復各有獨立微調權重。

## 何時使用

- 要以官方開放權重在本機執行無 VAE 的 text-to-image，或試用四步 Iris-3B Turbo。
- 要從照片估計相對深度，或做單步 4× 修復／放大。
- 要研究 pixel-space prior 的優缺點；不要把「省去 VAE」解讀成已證明下游品質更好。

## 安裝與文字轉圖片

依[官方 model card](https://huggingface.co/speridlabs/iris-3b#get-started)與 [README](https://github.com/speridlabs/iris-3b#inference)操作；需 Python ≥3.11、PyTorch ≥2.7.1、NVIDIA CUDA GPU。先在工作目錄執行：

```bash
git clone https://github.com/speridlabs/iris-3b.git
cd iris-3b
pip install -e .
hf download speridlabs/iris-3b --local-dir iris-3b --exclude "depth/*" "upscaler/*" "turbo/*"
python scripts/sample.py --checkpoint iris-3b --prompt "a red fox"
```

此處內層 `iris-3b/` 是權重目錄，包含 `model.safetensors` 與 `config.yaml`（約 12 GB）；首次推論另自動下載文字編碼器。官方程式載入 FP32 權重，以 BF16 autocast 推論。預設為 1024×1024、100 步 DPM-Solver++（order 2）、CFG 3；可用 `--seed`、`--steps`、`--cfg-scale`、`--negative-prompt`、`--height`、`--width` 調整，或 `--txt-file prompts.txt` 每行一個 prompt。建議用描述性的英文句子。

### 深度與修復

在同一原始碼目錄執行；首次使用會自動下載 HF repo 的 `depth/` 或 `upscaler/`（各約 12 GB），兩者使用空 prompt 的單次 forward pass，不載入文字編碼器：

```bash
python scripts/depth.py photo.jpg --out depth_out
python scripts/upscale.py photo.jpg --out upscaled
```

`--weights` 可指定本機權重目錄。深度預設將模型輸入長邊限制為 1024，`--max-side 0` 保留原解析度。修復預設先將輸入限制在短邊 512／長邊 1024，較大輸出用重疊 1024×1024 tiles；`--no-budget` 保留輸入大小，運算量隨輸出面積增加。

### 可選：Iris-3B Turbo

官方後續發布的全參數四步蒸餾權重，位於相同 HF repo 的 `turbo/`（約 6 GB）：

```bash
hf download speridlabs/iris-3b --include "turbo/*" --local-dir iris-3b
python scripts/sample.py --checkpoint iris-3b/turbo --prompt "a red fox"
```

程式讀取 `distill.yaml` 的固定四步 schedule，無 CFG；`--steps`、`--order`、`--shift`、`--cfg-scale`、`--negative-prompt` 不適用。仍可調 prompt、解析度與 seed。官方報告 H100、batch 4 下每張 1024×1024 約 0.7 秒；這不是其他硬體的速度保證。

## 輸入與輸出

| 任務 | 輸入 | 輸出 |
|---|---|---|
| 文字生成（含 Turbo） | 文字 prompt、可選 seed／尺寸 | 預設 `output/samples/` 的 JPG 與 `grid.png`；可用 `--outdir` 改路徑 |
| 深度 | RGB 照片 | 原圖解析度的 `<name>.npy` 相對 log depth（−1 近、+1 遠）與彩色 `<name>.png` |
| 修復／放大 | 低品質照片 | `<name>_x4.png`；4× 是相對於尺寸限制後的輸入，預設最大 2048×4096（可轉置） |

## 結果與限制

- [論文 Table 2](https://arxiv.org/html/2610.09450v1#S3.T2)：1024²、CFG 3、100 步、無 prompt rewriting，GenEval **0.798**、DPG **86.52**、LongText **0.857**、OneIG-EN **0.540**；OneIG 接近 Qwen-Image 的 0.539，不能推論所有任務都追平。
- 論文也用 gain-matched ridge 初始化與較低 trunk learning rate，將 FLUX.2 Klein base 4B 轉成 pixel-space model；這是另一組實驗，並非上面的 Iris 權重。深度與 4× DIV2K 修復比較均未顯示 pixel-space prior 有顯著優勢；Iris 沒有匹配的 latent twin，短預算、單次訓練及不同前訓練條件限制了結論。
- 深度是 affine-invariant 相對值，不能直接當公尺；評測需在 log space 對齊 scale／shift。原始深度可能出現 16×16 patch-grid 痕跡。
- 文字繪製、物件數量與位置可能不準確；Turbo 的長文字與跨 seed 多樣性較弱，平坦背景可能帶細粒噪點。
- 官方 demo 同駐三模型約需 45 GB VRAM，`IRIS_OFFLOAD=1` 約 20 GB 峰值；這是 demo 設定，**單獨 CLI 的最低 VRAM 未公布**。本 skill 僅核對官方文件與程式，未在本機下載權重或實跑 GPU 推論。

## 授權與來源

官方程式與 Iris 權重為 **Apache-2.0**，遵守 repo 的 `LICENSE` 與 `NOTICE`。另行下載的 Qwen3-VL 文字編碼器與訓練用 DINOv2 為 Apache-2.0，Dion optimizer 為 MIT，依各自授權使用。

- [Hugging Face 論文頁](https://huggingface.co/papers/2610.09450)
- [arXiv 摘要](https://arxiv.org/abs/2610.09450)／[全文](https://arxiv.org/html/2610.09450v1)
- [官方 HF model card 與權重](https://huggingface.co/speridlabs/iris-3b)
- [官方 GitHub](https://github.com/speridlabs/iris-3b)／[LICENSE](https://github.com/speridlabs/iris-3b/blob/main/LICENSE)／[NOTICE](https://github.com/speridlabs/iris-3b/blob/main/NOTICE)
- [文字生成 CLI](https://github.com/speridlabs/iris-3b/blob/main/scripts/sample.py)／[深度 CLI](https://github.com/speridlabs/iris-3b/blob/main/scripts/depth.py)／[修復 CLI](https://github.com/speridlabs/iris-3b/blob/main/scripts/upscale.py)
- [官方 demo](https://huggingface.co/spaces/speridlabs/iris-3b)／[Turbo demo](https://huggingface.co/spaces/speridlabs/iris-3b-turbo)
