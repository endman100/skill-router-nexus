---
name: evaluate-model-personality
description: "依 Artificial Analysis AA-PersonalityBench 分析與比較 LLM 模型人格、溝通風格、迎合性及套話，解讀 Elo、百分位與模型特徵，按任務偏好進行模型選型。Use for AI personality evaluation, communication style comparison, sycophancy, slop, and preference-weighted model selection."
---

# 模型人格與溝通風格評估

## 執行流程

1. 從任務與既有偏好確定重視的特徵；區分文字風格需求與任務能力需求。
2. 查閱下方官方主頁與方法頁，記錄查閱日期、完整模型版本、推理設定及比較範圍。涉及排名與數值時取得當期資料；無法讀取時明示缺口。
3. 先比較八項指數，再查看相關細項、公開回答與評審理由。結合信賴區間解讀接近的分數，區分觀察與推論。
4. 需要個人化選型時，使用 Build Your Own Personality，以 −2 至 +2 設定細項權重；負權重代表希望減少該特徵。依頁面方法合成排名，清楚列出選用特徵與權重。
5. 交付精簡比較：模型與設定、相關指標及數值單位、適用情境、限制與來源。Agent 選型另以實際語言、提示詞與工具測試任務完成率、確認次數、失敗恢復及驗證可靠性。

## 八項人格指數

| 指數 | 組成細項 |
|---|---|
| Expressiveness 表達力 | Lexically Varied、Eloquent、Literate、Natural Sounding、Metaphorical |
| Organization 組織性 | Structured、Scannable、Bottom-Line Summary、Answer First |
| Informativeness 資訊性 | Information Dense、Evidence-Based、Resource-Specific、Actionable Guidance、Pragmatic |
| Transparency 透明度 | Truthful、Admits Uncertainty、Disclaims Assumptions、Flags Nuances、Sycophantic（反向） |
| Warmth 溫暖感 | Friendly、Humorous、Sincere、Emotionally Intelligent |
| Conviction 立場鮮明度 | Direct、Confident、Opinionated、Constructive Pushback |
| Imagination 想像力 | Creative、Open-Ended |
| Slop 套話與空泛語言 | Slop；高分代表更多填充與泛泛語言 |

## 評測與分數解讀

- 以已查閱的方法為基準：30 個特徵，每項 30 題，共 900 題；全為英文，每題回答一次，單輪 user message，沒有 system prompt。完整題庫保密，主頁提供 5 題公開範例。
- 使用 LLM 評審群；每次比較交由其中一位評審，對同題兩份匿名回答判斷誰更展現指定特徵，或判定平手；隨機排列答案並平衡評審分配。
- 以 Firth-penalized Bradley–Terry 模型估計各特徵 Elo，平手各計半勝。Elo 相同代表 50/50，差 400 分代表 10:1 勝算；勝出意指特徵更突出。
- 將各細項 Elo 標準化為 z-score，必要時反向，取平均後轉為受測模型間 1–100 百分位。Transparency 反向計入 Sycophantic；原始迎合性分數仍以越高代表越迎合。
- 細項信賴區間來自 1,000 次 verdict bootstrap；指數區間以成員細項 Elo 上下界重新換算，反向項交換上下界。
- 區分百分位、Elo、單題勝率、Elo 推估的兩模型比較機率，以及相對平均值的標準差 σ。百分位不是正確率或等距能力分數，會隨受測模型集合改變。
- 將指數視為風格描述。Truthful、Evidence-Based 與 Confident 等細項仍須搭配實際事實查核；雷達圖面積不代表整體品質。
- 將低迎合性與直接性解讀為溝通傾向；自主執行能力、拒絕頻率與工具使用成效需另行驗證。

## 直接量測與探索工具

- 21 項溝通特徵：長度（字元、詞、句、段、平均句長）、結構（列表、標題、表格）、標點（破折號、縮約詞、驚嘆號、問號、括號、引號、冒號、省略號）、強調（粗體、斜體、emoji、縮寫、以問號結尾比例）。使用 900 題回答的平均值，與人格評審分數分開解讀。
- Compare Model Personalities：查看 Elo 差推估的特徵比較機率；50% 代表勢均力敵。
- Model Fingerprints：查看相對模型平均值最突出的正負 σ 特徵。
- Families & Clusters：依標準化特徵的相關性與 average-linkage 聚類；相近代表測得風格相似，不能據此推定模型血緣或訓練來源。

## 來源

- [AA-PersonalityBench 主頁](https://artificialanalysis.ai/evaluations/aa-personalitybench)
- [官方評測方法](https://artificialanalysis.ai/methodology/aa-personalitybench)

方法查閱日期：2026-10-21。將模型名次與評審配置視為動態資料，使用時查核官方頁面。
