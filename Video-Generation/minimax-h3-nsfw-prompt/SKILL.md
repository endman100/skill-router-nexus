---
name: minimax-h3-nsfw-prompt
description: "為 MiniMax H3 Ref2VA 生成與優化結構化影片 prompt。適用於動漫風格 NSFW 影片提示詞設計，包含角色參考、動作控制、音訊隔離與模組化變數。觸發關鍵字：MiniMax H3、Ref2VA、影片 prompt、角色聲音、NSFW prompt。"
type: workflow
lifecycle: active
---

# MiniMax H3 NSFW Prompt 工程

建立結構化的 MiniMax H3 Ref2VA prompt，透過模組化模板控制角色身份、姿勢、鏡頭、音訊與背景。

## 何時使用

- 要為指定角色生成不同性愛場景的影片 prompt
- 需要套用模組化模板，快速更換姿勢、鏡頭、動作
- 角色特徵與服裝已固定，只需調整場景相關變數
- 要保持角色一致性的同時產出多種性愛動作

## 核心結構

每個 prompt 必須依照以下順序：

1. `subject_definitions` — 定義角色、參考圖、音訊職責
2. `summary` — 簡短概述
3. `retention_analysis` — 鎖定要保留的元素
4. `detailed_description` — 主要控制段（姿勢、鏡頭、動作、聲音）
5. `overall_soundscape` — 聲音總結
6. `non_diegetic_music` — 通常寫 `N/A`

## 參考圖規則

| 參考 | 用途 | 權重 |
|------|------|------|
| `<Picture 1>` | 女性身份、臉、身體、服裝 | `fully_preserved` |
| `<Picture 2>` | 男性外觀（可選） | `weak_reference` |
| `<Picture 3>` | 插入細節（pussy 與 dick） | reference（固定使用 `assets/penetration-reference.png`） |
| 背景 | 純文字描述 | 不依賴參考圖 |

- 只描述想要出現的物品，不要提到不想出現的東西
- 男性若不需要出鏡臉部，設為 `weak_reference`
- `<Picture 3>` 固定使用 skill 內的 `assets/penetration-reference.png`
- 若有提供 `<Picture 1>` 或 `<Picture 2>`，必須從中確認角色特徵與服裝資訊

## 影片長度

- 預設長度為 **10 秒**
- 表情動作必須至少有 **兩種**，並在影片中輪替出現

## 性愛姿勢術語參考

| 術語 | 說明 |
|------|------|
| missionary | 傳教士體位 |
| mating press | 交配壓制 |
| doggy style | 後入 |
| cowgirl | 女上位 |
| reverse cowgirl | 反向女上位 |
| spooning | 側躺後入 |
| standing rear | 站立後入 |
| prone bone | 躺著後入 |
| standing leg-up | 站立單腿高抬 |

完整模板請參考 `template.txt`。