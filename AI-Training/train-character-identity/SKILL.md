---
name: train-character-identity
description: "Reference only the Hugging Face MOSS Serenity documentation for name-to-appearance binding, character triggers, finetuning, prior preservation and EMA. Use for 角色名稱與長相綁定訓練. Output Markdown only; add no unsupported methods or advice."
---

# 角色名稱與外貌綁定：MOSS Serenity

使用範圍：僅整理內附 HF 文件中與人物綁定有關的方法；未記載者回答「來源未說明」。不加入延伸建議或程式。技能 metadata、中文摘要與章節編排屬整理格式。

使用時讀取本地 [訓練原文][T]；核對模型總覽或提示方式時讀取 [模型卡][M]、[生成原文][G]。三份原文完整收錄，閱讀不需連線；原文內的程式與命令僅作文件參考。


## 1. 人名與圖片描述

來源：[訓練文件 — Dataset][T]、[生成文件 — Prompting][G]。

- 每人一個資料夾，以 trigger 命名；prefix.txt 的前綴 photo of [folder] 會將資料夾名稱放入每張圖片的 caption。
- Caption 用自然語句描述人物、表情、構圖、姿勢、服裝、背景與光線；trigger 為移除空格的小寫姓名，其後接訓練類別 a woman／a man。
- 用 folder_repeats 平衡曝光：學得較慢者每 epoch 3 倍；兩位學得較快者為 0.5 倍，每 epoch 隨機使用一半圖片。

## 2. 更新範圍與原配置

來源：[模型卡 — Training][M]、[訓練文件 — What was trained][T]。

目標：微調 MOSS-Image Base，讓模型依名字生成已學人物，同時保留底座能力。

| 項目 | 作者配置 |
|---|---|
| 更新權重 | 42 個 joint blocks 的 Linear，4.76B／5.08B 參數 |
| 凍結 | text adapter（投影及 2 blocks）、norms、biases、embedders、modulation、output head |
| 步數／批次 | 24,000；batch size 1，約 25 epochs |
| 解析度 | 原文：512 px area；依長寬比分桶，16 px 網格 |
| Optimizer | Automagic3；權重在 backward 內更新，使用 BF16 stochastic rounding |
| 學習率 | 固定 1e-5 |
| EMA | 0.999；每 4 步更新；無 warmup；存於 CPU RAM；發布 EMA 平均權重 |
| Timesteps | logit-normal：mean 1.09、std 0.95、sigma 截至 0.95，混入 1% uniform；1000-step 網格 |
| Caption dropout | 5% |

作者說明：凍結 text adapter 避免少量 caption 改變整體提示理解；EMA 用於平滑 batch size 1 時的權重游移。[T]

## 3. 先驗保留與正則化

來源：[訓練文件 — Why these choices／The config][T]。

- 訓練前將 caption 的 trigger 換成類別詞，記錄原模型預測；訓練時約束模型在該類別 caption 上接近原模型，以保留一般類別行為。
- Prior preservation：權重 1.0；每圖記錄 8 組輸入；每步使用。
- Regularisation：一般女性與男性的真實照片；reg_lr_multiplier 為 0.2。

## 4. 追加人物／續訓

來源：[訓練文件 — Continuing it][T]。

- **完整 resume state**：僅原訓練者持有；新增人物資料夾與 prior.classes 對應，維持原始 Base 作新圖片先驗來源，增加累計 max_steps 並續訓。
- **發布的 BF16 權重**：從 Serenity 開始，optimizer／EMA 重建；先驗取自 Serenity，保留其當前行為。

## 5. 提示方式與作者觀察

來源：[生成文件 — Prompting／What works][G]。

- 以 photo of 接 trigger、類別、外觀、表情、構圖、服裝、場景與光線；重要髮型應明述。
- 胸像或近景較像；全身照中太小的臉可能出錯。用服裝、髮型及場景描述角色，不只寫影視作品名稱。
- 多人須各自提供名字、類別、位置與描述；同類別人物可能混臉。作者建議嘗試多個 seed 或分別生成。[M][G]
- 無 trigger 時生成一般人物；相似度會隨 seed 變動。以上是該模型的觀察。

## 來源

核對日期：2026-10-20。各節引用本地原文；[來源紀錄](references/SOURCES.md) 記載 HF 版本、原始網址、雜湊與保存範圍。

- [M：模型卡][M]
- [T：Training MOSS Serenity][T]
- [G：Generating with MOSS Serenity][G]

[M]: references/hf/README.md
[T]: references/hf/docs/training.md
[G]: references/hf/docs/generating.md

