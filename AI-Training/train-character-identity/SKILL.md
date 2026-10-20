---
name: train-character-identity
description: "Reference the name-to-appearance training method documented in the Hugging Face malcolmrey/moss-serenity repository. Use for 人名與長相綁定、角色名稱觸發詞、MOSS Serenity 訓練、prior preservation、EMA. Summarize only that repository's documented methods in Markdown; do not add training advice, code, or unsupported adaptations."
---

# 角色名稱與外貌綁定：MOSS Serenity 原文件整理

本 skill 僅以文末三份 HF 文件為方法來源。以下為中文摘要，並非逐字翻譯；技能名稱、觸發說明及章節編排屬整理格式。

## 使用範圍

- 依本文件回覆原專案的資料標註、微調、先驗保留與續訓方法。
- 技術內容限於來源已記載的事項；未記載者註明「來源未說明」。
- 不自行補入動漫遷移、資料切分、replay、評估矩陣、其他論文或新的訓練建議。
- 只輸出 Markdown 說明，不產生程式或設定檔。

## 1. 原專案目標與更新範圍

依 [模型卡的 Training 章節][M]：

- 以 MOSS-Image Base 微調，使模型透過名字生成已訓練的人物，同時保留底座原有能力。
- 更新 42 個 joint blocks 的 Linear 權重，約為主幹 5.08B 參數中的 4.76B。
- 凍結 text adapter、norms、embedders。

## 2. 將人物名字放入照片描述

依 [訓練文件的 Dataset 章節][T]：

- 每位人物一個資料夾，以該人物的 trigger 命名。
- 透過 prefix.txt，將資料夾名稱加入每張圖片的 caption 前方。
- Caption 使用自然語句描述人物、表情、構圖、姿勢、服裝、背景與光線。
- 以 folder_repeats 平衡人物曝光；作者對學得較慢的人物使用每 epoch 3 倍，對兩位學得較快的人物使用 0.5 倍。

依 [生成文件的 Prompting 章節][G]，trigger 使用小寫、移除姓名空格；其後接訓練時使用的類別詞 a woman 或 a man。

## 3. 以原模型預測保留一般類別行為

依 [訓練文件的 What was trained／Why these choices 章節][T]：

- 訓練前，將 caption 內的人物 trigger 換成類別詞，記錄原模型的預測。
- 每次訓練同時要求模型在這些類別 caption 上接近原模型預測，使一般類別詞維持底座行為。
- Prior preservation 權重為 1.0，每張圖片記錄 8 組輸入，每步使用。
- 額外使用一般女性與男性的真實照片作 regularisation，原配置的 reg_lr_multiplier 為 0.2。

## 4. 原專案訓練配置

依 [模型卡的 Training 章節][M]：

| 項目 | 作者記載 |
|---|---|
| 訓練步數 | 24,000 |
| Batch size | 1，約 25 epochs |
| 解析度 | 原文記為 512 px aspect buckets |
| Optimizer | Automagic3，fused into backward |
| 學習率 | 固定 1e-5 |
| EMA | 0.999，每 4 步更新，不設 warmup |
| 發布權重 | EMA 平均後的權重 |
| Timesteps | logit-normal，mean 1.09、std 0.95、cutoff 0.95，混入 1% uniform |

依 [訓練文件的 Why these choices 章節][T]，作者保持 text adapter 凍結，以免少量 caption 改變整體提示理解；使用 EMA 平滑 batch size 1 時的權重游移。

## 5. 追加人物與繼續訓練

依 [訓練文件的 Continuing it 章節][T]：

| 起點 | 作者記載的方法 |
|---|---|
| 完整 resume state | 加入新人物資料夾與 prior.classes 對應；維持原始 Base 作新圖片先驗來源，增加 max_steps 並續訓。該狀態僅原訓練者持有。 |
| 發布的 BF16 權重 | 從 Serenity 權重開始；optimizer 與 EMA 重新建立，先驗取自 Serenity，因此保留的是 Serenity 當前行為。 |

## 6. 作者記載的提示方式與限制

依 [生成文件的 Prompting／What works 章節][G]：

- 提示以 photo of 開頭，接人物 trigger、類別詞及外觀、表情、構圖、服裝、場景、光線。
- 胸像或更近的臉部效果較好；全身照中太小的臉可能失去相似度。
- 以服裝、髮型及場景描述角色外觀，不只提供影視作品名稱。
- 多人同框時，各自提供名字、類別詞、位置及描述；同類別人物可能混合臉部特徵。
- 相似度會隨 seed 變動，作者建議嘗試多個 seed。

以上為作者對該模型的觀察。

## 來源

核對日期：2026-10-20。各節均標示來源文件與對應章節；方法內容限於這三份文件。

[M]: https://huggingface.co/malcolmrey/moss-serenity
[T]: https://huggingface.co/malcolmrey/moss-serenity/blob/main/docs/training.md
[G]: https://huggingface.co/malcolmrey/moss-serenity/blob/main/docs/generating.md

- [模型卡][M]
- [Training MOSS Serenity][T]
- [Generating with MOSS Serenity][G]
