---
name: infovis
description: 使用 InfoVis（arXiv 2610.16784）9B 模型執行投影片圖片生成與編輯：text-to-slide、template-conditioned generation、multi-image grounded generation、instruction-based slide editing。適用於本機部署簡報影像模型、依範本設計投影片、整合多圖素材、修改既有投影片，以及理解 VisSlideBench 評測與文件轉簡報流程。
---

# InfoVis：統一投影片圖片生成與編輯

論文 **InfoVis: Unified Slide Image Generation and Editing** 將四種投影片任務整合至同一個 9B 模型。以 FLUX.2-klein-base-9B 為基底，先做文字生成投影片 continual pretraining，再做四任務混合訓練，最後從共享 checkpoint 分別 SFT 並線性融合。資料引擎建立逾 13M 筆 CPT 與 1.9M 筆 SFT records；僅訓練 diffusion transformer，凍結 Qwen3 文字編碼器與 VAE。來源：[論文 §3、§5](https://arxiv.org/html/2610.16784v1)、[訓練說明](https://github.com/VectorSpaceLab/InfoVis/blob/main/docs/training.md)。

## 何時使用與輸入輸出

需要開放權重的投影片影像生成、風格參考或自然語言修改時使用；先確定目標是單頁圖片，或另外串接整份簡報流程。

| 任務 | 輸入 | 輸出 |
|---|---|---|
| Text-to-slide | 短需求、詳細描述或 `style_json` 設計指令 | 一張投影片圖片 |
| Template-conditioned | 新內容指令 + 一張參考投影片 | 沿用參考風格的新投影片圖片 |
| Multi-image grounded | 指令 + 1–4 張圖表、圖片等素材 | 整合素材的投影片圖片 |
| Instruction-based editing | 修改指令 + 原始投影片圖片 | 修改後的投影片圖片 |

CLI 以 `--out` 指定輸出檔案，下列範例輸出 PNG。圖片輸入共用 `--images`，角色由指令與任務決定。模型本身不直接輸出可編輯 PPTX。

## 安裝、權重與推論

**查核日期：2026-11-11。** 依[官方 README](https://github.com/VectorSpaceLab/InfoVis#-quick-start)及 [model card](https://huggingface.co/InfoVis/InfoVis)執行；Python 3.12、PyTorch 2.7.1、支援 BF16 的 NVIDIA CUDA GPU，`diffusers>=0.37.0`。下例為官方 CUDA 12.6 安裝方式，其他版本依實際環境選擇。

```bash
conda create -n infovis python=3.12
conda activate infovis
pip install torch==2.7.1 torchvision --extra-index-url https://download.pytorch.org/whl/cu126
git clone https://github.com/VectorSpaceLab/InfoVis.git
cd InfoVis
pip install -r requirements.txt
hf download InfoVis/InfoVis --local-dir checkpoints/InfoVis

python inference.py --transformer checkpoints/InfoVis \
  --prompt "A clean title slide for a talk on renewable energy, with a wind turbine illustration." \
  --out slide.png

python inference.py --transformer checkpoints/InfoVis \
  --prompt "Change the title color to red." \
  --images source.png --width 1280 --height 720 --out edited.png
```

- `--transformer InfoVis/InfoVis` 可直接從 HF 載入。權重庫僅提供 transformer；首次執行另載入基底的文字編碼器與 VAE。基底 `black-forest-labs/FLUX.2-klein-base-9B` 為 gated repo，先完成 HF 存取條件並讓本機具備下載權限。
- 使用官方 `inference.py` 重現設定：50 Euler steps、CFG 4.0、空 negative prompt、BF16、4,096-token context，並遮蔽 prompt padding。原生 `Flux2KleinPipeline` 預設不具備相同 context 與 masking 行為。
- 單次 CLI 預設 **1376×768**；基準文字生成為 1280×720，範本／多圖為 1376×768，編輯依原圖尺寸。CLI 編輯時明確指定寬高。輸入圖片先限制至 1024×1024 的像素面積，再中心裁切為 32 的倍數；過長 prompt 會截斷。
- 官方程式預設將整個 pipeline 放到 CUDA；**單卡最低 VRAM、各 GPU 推論延遲與 CPU offload 指令未公布**。訓練共使用 48–96 張 H100 80GB，不能當作推論最低需求。無合適 GPU 時可試[官方 Space](https://huggingface.co/spaces/sabulin/InfoVis)，其預設 30 steps，與論文 50 steps 不同。

### 可選：VisSlideBench

以下為官方 README 的 **8 GPU** 四軌推論命令，在同一原始碼目錄執行：

```bash
hf download InfoVis/VisSlideBench --repo-type dataset --local-dir VisSlideBench
bash scripts/infer_visslidebench.sh checkpoints/InfoVis VisSlideBench outputs/infovis
```

評分依下載資料的 `eval/README.md`；文字忠實度使用 OCR，其餘多項判斷使用 GPT-4.1，單純生成圖片不等於完成評測。

### 文件轉整份簡報

[論文附錄 D](https://arxiv.org/html/2610.16784v1)描述：解析文字與素材 → GPT-4.1 規劃內容及 `style_json` → InfoVis 產生候選 → Qwen3.5-27B verifier 選圖，首張選定圖片作為後續頁的風格參考。可選 PPTX 匯出透過 OCR、文字移除／修補與文字框重建；圖表及表格仍是圖片。**目前公開 repo 未提供完整流程／PPTX 匯出的執行入口與命令**，單頁 CLI 不能直接完成文件轉簡報。

## 結果與限制

- [論文 Table 1](https://arxiv.org/html/2610.16784v1)：VisSlideBench 共 1,527 個人工篩選案例、四任務十一項指標；InfoVis overall **7.94**，基底 **6.30**、Nano-Banana-2 **7.99**、GPT-Image-2 **8.36**。InfoVis 在該比較的十一項指標均領先受測開放模型。
- Table 3 的完整文件流程在 SlidesGen-Bench **Aesthetics 27.09**，十個系統中第二；使用額外 planner、verifier 與每頁兩個候選，**未執行 content／editability 評測**，不能視為單模型可編輯性成績。
- 資料與基準僅涵蓋英文投影片；繁體中文與其他語言品質未知。美感仍是與專有模型差距最大的面向，知識／推理密集的投影片也有明顯落差。
- 輸入圖表可能被重繪，導致座標、圖例或資料結構失真；局部編輯可能連帶刪改無關區域。交付前逐一核對文字、數值、圖表及未指定修改的區域。
- 編輯基準來自與訓練相同的建構流程，主要衡量分布內能力；生成 SFT 目標及部分基準由專有模型合成，有其風格偏向。本記錄核對官方文件與程式，未下載權重或實跑 GPU 推論。

## 授權與來源

- 程式碼：[Apache-2.0](https://github.com/VectorSpaceLab/InfoVis/blob/main/LICENSE)。
- 權重：[FLUX Non-Commercial License v2.1](https://huggingface.co/InfoVis/InfoVis/blob/main/LICENSE.md)，model card 限非商業使用，並要求遵守 [NOTICE](https://huggingface.co/InfoVis/InfoVis/blob/main/NOTICE) 的 attribution；程式授權不等於權重可商用。
- VisSlideBench 為 CC BY-NC 4.0；訓練資料 annotations／metadata 為 CC BY-NC 4.0，原圖片版權仍屬原作者，資料卡限非商業學術研究。論文本身為 CC BY 4.0，與權重及資料授權分開。
- [HF 論文頁](https://huggingface.co/papers/2610.16784)／[arXiv 摘要](https://arxiv.org/abs/2610.16784)／[全文](https://arxiv.org/html/2610.16784v1)
- [專案頁](https://vectorspacelab.github.io/InfoVis/)／[GitHub](https://github.com/VectorSpaceLab/InfoVis)／[推論原始碼](https://github.com/VectorSpaceLab/InfoVis/blob/main/inference.py)
- [HF model card 與權重](https://huggingface.co/InfoVis/InfoVis)／[基底模型](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)／[Demo](https://huggingface.co/spaces/sabulin/InfoVis)
- [VisSlideBench 與評分程式](https://huggingface.co/datasets/InfoVis/VisSlideBench)／[訓練資料](https://huggingface.co/datasets/InfoVis/Data)／[訓練說明](https://github.com/VectorSpaceLab/InfoVis/blob/main/docs/training.md)
