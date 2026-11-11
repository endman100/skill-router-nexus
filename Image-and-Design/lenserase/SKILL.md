---
name: lenserase
description: "LensErase（LensFamily/LensErase）的 mask-based Erase Anything 圖片移除與修補方法。用於查詢、評估或追蹤 LensErase 的 object removal、inpainting、物件消除、文字／浮水印移除、多目標及陰影反射消除，以及官方程式與權重發布狀態。"
---

# LensErase

## 摘要與適用情境

[LensErase: A Foundation Model for Erase Anything](https://arxiv.org/abs/2610.18072) 是以原圖與選取遮罩為條件的通用消除模型，不需要文字提示。適合照片物件、視覺文字、浮水印、半透明內容及多層海報的局部移除，也涵蓋多目標與伴隨陰影、反射的消除。

以預訓練 Lens 生成模型為基礎，透過 Mask-Aware RoPE 將遮罩資訊注入來源影像 tokens，經 SFT 與 contract-guided、region-aware RL 改善消除品質；推論時以 TraceFusion 估計實際編輯區域並保留其餘內容。

串流影片的遮罩式物件消除可參考 [StreamErase](../../Video-Editing/streamerase/SKILL.md)；兩者用途相近，未查得模型衍生關係。

## 發布狀態與執行方式

查核日期：2026-11-11；[官方 repo](https://github.com/LensFamily/LensErase) `main` 查核版本：`0db2cb984517f8dcdc14c55199400a526e7a9201`。

官方 README 與專案頁仍標示 **Code coming soon**。目前只有 README、LICENSE、展示網頁及素材；沒有模型執行腳本、依賴清單、推論／訓練設定或官方安裝指令。官方文件未連結 LensErase checkpoint 或 Hugging Face 模型卡；查核時 HF 模型搜尋亦無結果。

需要實際執行時，先重查官方 README 與完整檔案清單。以下只是取得官方資料與檢查檔案的 Git 操作，**不是官方推論指令**：

```bash
git clone https://github.com/LensFamily/LensErase.git
cd LensErase
cat README.md
git ls-files
```

- 安裝、權重下載、Python API、推論 CLI：尚未公布；依未來官方發布補齊，勿猜測套件、模型 ID 或 `inference.py` 參數。
- 硬體：最低 GPU／VRAM、CUDA／PyTorch 版本、CPU 支援與推論速度未提供，不能承諾本機可跑。
- 論文附錄 E.4 的實驗設定：20-step Euler sampler，輸入尺寸 padding 至 16 的倍數，輸出裁回原尺寸。這些是方法參數，尚無對應可執行設定檔。
- 如上游仍未發布，交付方法說明、發布狀態及缺少的執行條件；如另用替代工具，明確標示其名稱。

## 輸入與輸出

| 項目 | 規格 |
|---|---|
| 輸入影像 | 含待移除內容的來源影像；檔案格式與解析度上限待官方程式確認 |
| 選取遮罩 | 與影像對齊的二元 mask；論文以 1 表示選取區域；可選取多個目標，無須文字 prompt |
| 輸出 | 移除目標並生成合理補全的影像；論文評測輸出恢復為原圖尺寸 |
| 編輯邊界 | 相關陰影／反射可能延伸至選取 mask 外；TraceFusion 依實際變化區域融合，不能保證 mask 外逐像素不變 |

## 已報告成果與限制

- LensErase-100M 含 101.07M 組 source–mask–target 訓練樣本；LensErase-Bench 含 500 案例，涵蓋一般物件、海報、浮水印與視覺文字。
- [論文附錄 F.4、Table 16](https://arxiv.org/html/2610.18072v1#A6.SS4) 報告 LensErase-Bench Overall **95.22/100**、HiFi Removal **82.80%**；後者要求原始 0–4 分量表的 Removal = 4，且 Inpainting、Preservation、Cleanliness 均 ≥ 3。這是作者的 VLM 評測，非本 skill 實測或品質保證。
- 論文附錄 H 指出 4K 等超高解析度的可靠訓練資料建構仍有困難；勿推定任意 4K 輸入都能可靠處理。
- 人工檢查殘留目標、陰影／反射、補全合理性、附近文字／物件與融合邊界。補全是生成結果，不代表還原被遮擋區域的真實內容。

## 授權

- GitHub repo 的 [LICENSE](https://github.com/LensFamily/LensErase/blob/main/LICENSE) 為 **MIT**（Copyright 2026 LensFamily）；使用或散布其內容時保留授權與著作權聲明。
- 論文頁標示 **CC BY-NC-SA 4.0**。模型權重與資料集的發布條款尚未確認，不能由 repo 的 MIT 推定。

## 官方來源與後續查核

- [GitHub／README](https://github.com/LensFamily/LensErase)：發布狀態及未來執行步驟。
- [論文](https://arxiv.org/abs/2610.18072)／[全文](https://arxiv.org/html/2610.18072v1)：方法、實驗設定、結果與限制。
- [專案頁](https://lensfamily.github.io/LensErase/)：原圖、mask、輸出範例與評測說明。
- [Hugging Face 模型搜尋 API](https://huggingface.co/api/models?search=LensErase)：查核時為空；這是搜尋端點，非模型卡或權重下載連結。
- [Lens 基礎模型](https://github.com/LensFamily/Lens)：相關研究；其權重與用法不能替代 LensErase 的正式發布。

分類決策：`KEEP_FLAT`；主要用途為既有圖片的移除與修補，置於 `Image-and-Design`。現有 Gemini 特定浮水印工具與 fal.ai 編輯 skill 未涵蓋此模型，不重複收錄其內容。
