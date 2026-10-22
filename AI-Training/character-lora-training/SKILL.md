---
name: character-lora-training
description: >-
  從作品名與角色名開始，收集、清理、生成角色圖片資料集，用 Codex 逐張打標，再訓練 Anima 角色 LoRA。
  用於要為一個動畫角色從零做 LoRA 訓練資料集、打標（caption）或訓練角色 LoRA 時。
---

# 角色 LoRA 訓練

## 輸入

作品名、角色名、trigger（小寫底線，例 `takane_yasuko`，也是 LoRA 檔名）。可選：參考圖、生成張數 N（預設 30）。

## 必守規則

- Codex 不能拿到任何 NSFW 圖片或文字；NSFW 只由 Grok 處理（分流在步驟 2 與 5）。

## 流程

複製這份清單，逐步打勾。每一步先讀對應的 md，照裡面的指令執行。

```
- [ ] 1. 資料收集
- [ ] 2. 清理
- [ ] 3. 三視圖
- [ ] 4. 資料集生成
- [ ] 5. 整理訓練集與打標
- [ ] 6. LoRA 訓練
```

1. **資料收集**：讀 [01_data_collection.md](01_data_collection.md)。
2. **清理**：讀 [02_cleaning.md](02_cleaning.md)。
3. **三視圖**：讀 [03_character_sheet.md](03_character_sheet.md)。
4. **資料集生成**：讀 [04_dataset_generation.md](04_dataset_generation.md)。
5. **整理訓練集與打標**：讀 [05_captioning.md](05_captioning.md)。
6. **LoRA 訓練**：讀 [06_lora_training.md](06_lora_training.md)。

`scripts/` 裡的程式直接執行，不需要讀內容；指令與參數寫在各步驟的 md。`templates/` 是打標用的 prompt 模板、欄位設定與 schema。
