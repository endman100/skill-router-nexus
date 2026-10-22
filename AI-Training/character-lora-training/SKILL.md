---
name: character-lora-training
description: >-
  從作品名與角色名開始，收集、清理並生成角色圖片資料集，使用 Codex 逐張打標，再訓練 Anima 角色 LoRA。
  適用於為動畫角色從零建立 LoRA 訓練資料集、打標（caption）或訓練角色 LoRA 時。
---

# 角色 LoRA 訓練

## 輸入

作品名、角色名、trigger（小寫底線，例 `takane_yasuko`，亦為 LoRA 檔名）。選填：參考圖、生成張數 N（預設 30）。

## 必守規則

- Codex 不得接收任何 NSFW 圖片或文字；NSFW 僅由 Grok 處理（分流於步驟 2 與 5）。

## 流程

複製此清單並逐步勾選。每一步驟先閱讀對應的 md 檔案，並依照其中的指令執行。

```
- [ ] 0. 建立 workspace
- [ ] 1. 資料收集
- [ ] 2. 清理
- [ ] 3. 三視圖
- [ ] 4. 資料集生成
- [ ] 5. 整理訓練集與打標
- [ ] 6. LoRA 訓練
- [ ] 7. LoRA 驗證
```

0. **建立 workspace**：閱讀 [00_workspace.md](00_workspace.md)，先建立全新案例目錄；後續 `<WS>` 均指此目錄。
1. **資料收集**：閱讀 [01_data_collection.md](01_data_collection.md)。
2. **清理**：閱讀 [02_cleaning.md](02_cleaning.md)。
3. **三視圖**：閱讀 [03_character_sheet.md](03_character_sheet.md)。
4. **資料集生成**：閱讀 [04_dataset_generation.md](04_dataset_generation.md)。
5. **整理訓練集與打標**：閱讀 [05_captioning.md](05_captioning.md)。
6. **LoRA 訓練**：閱讀 [06_lora_training.md](06_lora_training.md)。
7. **LoRA 驗證**：閱讀 [07_lora_validation.md](07_lora_validation.md)。

`scripts/` 內的程式直接執行，不需要讀取內容；指令與參數寫在各步驟的 md 檔案中。`templates/` 則是打標用的 prompt 模板、欄位設定與 schema。
