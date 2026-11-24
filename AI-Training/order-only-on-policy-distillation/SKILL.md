---
name: order-only-on-policy-distillation
description: "在設計或評估語言模型後訓練、比較標準 on-policy distillation（OPD）與排序監督，或判斷老師的 top-K token 排序能否作為蒸餾目標時使用。涵蓋 O³PD 的損失、訓練流程、實驗結果與適用限制。"
---

# Order-Only On-Policy Distillation（O³PD）

Guangzeng Han、Yu Wu 與 Xiaolei Huang 提出 O³PD，用於將自回歸語言模型老師的逐 token 偏好移轉到學生。輸入是訓練題目、可在學生前綴上評分的凍結老師，以及可更新的學生。輸出是經蒸餾後的學生 checkpoint。 [arXiv 2611.02112v1](https://arxiv.org/abs/2611.02112v1)

## O³PD 與標準 OPD 的差異

### 標準 OPD

On-Policy Distillation 由**當前學生**對題目採樣回答，再請老師在學生實際走過的每個前綴預測下一個 token。學生用逐位置的分布匹配損失學習老師的機率。這讓訓練覆蓋學生推論時可能遇到的前綴。OPD 可採用不同的分布匹配目標，如 reverse KL。本文基線將兩方機率限制在老師的 top-8 候選上並重新正規化，最小化 Jensen–Shannon divergence（JSD），老師溫度設為 1。離線序列蒸餾則通常在固定的老師回答上做監督式微調。 [論文 §2–3](https://arxiv.org/html/2611.02112v1#S3) · [GKD](https://arxiv.org/abs/2306.13649)

### O³PD 的三個 O 與訓練流程

三個 O 分別來自 **Order**（候選 token 的次序）、**Only**（老師訊號僅含候選身分與順序）、**On**（On-Policy，前綴由當前學生生成）。PD 是 Policy Distillation。 [論文 §3](https://arxiv.org/html/2611.02112v1#S3)

1. 從題目集抽出一個 minibatch。對每題 $x$ 用當前學生 $\pi_\theta$ 採樣回答 $y^S$，形成逐位置前綴 $s_t=(x,y^S_{<t})$。
2. 凍結老師在各 $s_t$ 上評分。以老師的下一 token 機率排序，取前 $K$ 個 token，依序記為 $v_{t,1},\ldots,v_{t,K}$。傳給損失的是有序的 token ID。
3. 在同一前綴上讀取學生對這些候選的 logits $z^S_t$。按**老師排序**配對第 $i$ 名與第 $i+1$ 名，計算相鄰學生分數差 $\Delta_{t,i}=z^S_t(v_{t,i})-z^S_t(v_{t,i+1})$。
4. 對每個相鄰對最小化 Bradley–Terry logistic loss $\ell_{t,i}=-\log\sigma(\Delta_{t,i})$，其中 $\sigma$ 是 sigmoid。先對單份回答的所有位置和 $K-1$ 個相鄰對取平均，再對 minibatch 取平均。更新期間固定已採樣的回答和老師排序，梯度只用來更新學生。下一批再由更新後的學生採樣。 [公式 3–4](https://arxiv.org/html/2611.02112v1#S3.SS2) · [附錄 A.3](https://arxiv.org/html/2611.02112v1#A1.SS3)

若所有相鄰不等式成立，傳遞性便確定這 $K$ 個候選的完整順序。$K=8$ 時每個位置只需 7 組相鄰比較，而全配對排序損失用 28 組。此目標偏好較大的學生分數差，但沒有指定要擬合的分數差。論文亦測試全配對 Logistic、對排名靠前的候選加權的 Top-Weighted Logistic，以及以整份排序為目標的 ListMLE。 [論文 §3.2–3.3](https://arxiv.org/html/2611.02112v1#S3.SS2)

### 為何可能更有效

老師的機率同時反映候選偏好與信心。作者認為學生容量較小時，複製老師的信心會限制學生調整自己的分布。排序提供偏好的方向，讓學生自行決定分數差。固定前綴下，老師 logits 除以任何正溫度 $T$ 都保留 top-$K$ 身分與順序，所以 O³PD 的目標不依賴老師溫度。學生採樣設定仍會改變前綴。 [論文 §3](https://arxiv.org/html/2611.02112v1#S3)

在 8B → 1.7B 分析中，O³PD 的 JSD@Top-8 較大，多數訓練期間的 Kendall’s $\tau$ 較高，top-8 重疊率幾乎每次評估都較高，top-1 一致率相近，學生分布的熵較高。這組實驗支持排序訊號足以提升數學推理的解釋。最小的 1.7B 學生也比 OPD 更偏離初始分布。 [論文 §5](https://arxiv.org/html/2611.02112v1#S5)

| 面向 | 標準 OPD（本文基線） | O³PD |
| --- | --- | --- |
| 監督訊號 | 老師的 top-8 token 機率，學生擬合分布 | 老師的 top-8 token 身分與排序，學生學習相鄰偏好 |
| On-policy / off-policy 資料 | 固定題目集，回答前綴由當前學生採樣 | 同樣在固定題目集上採樣學生前綴，老師只評分。兩者的核心流程皆無 off-policy 回答 |
| 老師與學生 | 老師凍結並評分，學生生成回答並更新參數 | 角色相同，老師評分後只傳有序候選 |
| 計算成本 | 每批需學生 rollout 及老師評分，逐位置計算 top-8 JSD，老師溫度可另行掃描 | 同樣需 rollout 及老師評分，逐位置計算 7 組相鄰損失，可省去老師溫度搜尋。端到端時間、顯存與 FLOPs 未知／未公開（2026-11-24） |
| 結果 | 8B → 1.7B 的三項平均在第 20 步達 38.1%，之後低於原始學生的 37.7% | 同一配對在第 100 步達 40.7%。六組三項平均較 OPD 高 0.3–2.9 個百分點 |

## 論文設定與主要結果

論文用 OpenThoughts 數學推理子集做訓練，對 Qwen3 的六組配對微調學生。LoRA 為 $r=64,\alpha=128$，學習率 $5\times10^{-6}$，有效 batch size 32，訓練 100 步，訓練 seed 為 42。老師開啟 thinking，學生 rollout 關閉 thinking，長度上限 1,024 tokens。訓練使用 Transformers，評估使用 vLLM，硬體為 NVIDIA H100。 [附錄 A](https://arxiv.org/html/2611.02112v1#A1)

Avg@12 是每題採樣 12 份回答後的最終答案正確率（3 個評估 seeds，各 4 份）。下表為 HMMT25、AIME24、AIME25 的等權平均。兩法每 20 步評估一次，各回報三項平均最高的 checkpoint。 [論文 §4.1–4.2、表 3](https://arxiv.org/html/2611.02112v1#S4)

| Qwen3 老師 → 學生 | OPD | O³PD | 差值（百分點） |
| --- | ---: | ---: | ---: |
| 14B → 8B | 64.0% | 64.6% | +0.6 |
| 14B → 4B | 60.9% | 63.2% | +2.3 |
| 8B → 4B | 61.3% | 63.2% | +1.9 |
| 14B → 1.7B | 39.1% | 39.4% | +0.3 |
| 8B → 1.7B | 38.1% | 40.7% | +2.6 |
| 4B → 1.7B | 38.0% | 40.9% | +2.9 |

- 六組在 AIME25 都進步，平均增加 3.4 個百分點。4B → 1.7B 在 AIME25 增加 5.6、AIME24 增加 6.4、HMMT25 下降 3.1 個百分點。18 個配對與基準的組合中有 14 個進步。4B 老師蒸餾 1.7B 學生的平均 40.9%，超過 14B 老師用 OPD 的 39.1%。 [表 3](https://arxiv.org/html/2611.02112v1#S4.T3)
- 8B → 1.7B 的消融中，$K=4,8,16$ 的相鄰損失平均分別為 40.0%、40.7%、39.7%。固定 $K=8$ 時，三種替代排序損失也超過 OPD 的 38.1%，其中 ListMLE 為 40.6%。 [表 4](https://arxiv.org/html/2611.02112v1#S4.F4.fig1)
- OPD 用六個老師溫度做 3 步短跑。在 1.7B 及以上的學生中，單組 HMMT25 最多相差 6.4 個百分點。8B → 1.7B 在此短跑的最佳溫度為 0.25，部分其他配對則為 2。 [附錄 B](https://arxiv.org/html/2611.02112v1#A2)

## 限制與可用性

- 實證來自 Qwen3 與三項競賽數學基準。主要比較採單一訓練 seed，三個評估 seeds 反映回答採樣。排序消融與訓練曲線聚焦 8B → 1.7B，老師溫度消融只訓練 3 步。相對於完整調溫並訓練 100 步的 OPD、其他模型家族、開放式生成與安全對齊的效果，均為未知／未公開（2026-11-24）。 [論文 §4–5](https://arxiv.org/html/2611.02112v1#S4) · [倫理聲明](https://arxiv.org/html/2611.02112v1#Sx1)
- 官方專案頁、GitHub 訓練實作及 O³PD 蒸餾後權重為未知／未公開（2026-11-24）。論文提供損失、演算法、提示模板與超參數，並說明 Qwen3 基礎模型和 OpenThoughts 已公開。 [可重現性聲明](https://arxiv.org/html/2611.02112v1#Sx2) · [Hugging Face 論文頁](https://huggingface.co/papers/2611.02112)

## 工程推論與未驗證應用

- 重現時可檢查老師候選 ID 是否能對應至學生詞彙，以及前綴與預測位置是否對齊。若 tokenizer 不同，跨詞彙對齊方法及成效為未知／未公開（2026-11-24）。
- 僅傳送有序 top-$K$ ID 的介面原理上足以提供監督，前提是能為指定的學生前綴取得逐位置排序。作者在 Hugging Face 說明，當時檢查的商用 API 缺乏所需的 teacher-forcing 介面，可能要逐前綴請求。此部署方式的效能與成本為未知／未公開（2026-11-24）。 [作者討論](https://huggingface.co/papers/2611.02112)

## 相關技能

- 想從少量主題描述合成訓練課程時，參考 OPST。它在學生生成的前綴上，用帶特權資訊的 EMA 老師提供機率分布，再用 skewed JSD 蒸餾。O³PD 的實驗使用既有數學題目與獨立凍結老師，研究的是逐 token 監督的形式。 [opst-self-training](../opst-self-training/SKILL.md)
- 想比較 soft targets、溫度縮放與 MiniLLM 的 reverse KL 時，參考通用知識蒸餾。 [knowledge-distillation](../knowledge-distillation/SKILL.md)

## 來源

- Han、Wu 與 Huang 的預印本，2026-11-01。 [arXiv 摘要](https://arxiv.org/abs/2611.02112) · [HTML 全文 v1](https://arxiv.org/html/2611.02112v1) · [PDF v1](https://arxiv.org/pdf/2611.02112v1)
- 論文收錄頁與作者討論。 [Hugging Face Papers](https://huggingface.co/papers/2611.02112)
