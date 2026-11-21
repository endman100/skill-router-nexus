---
name: opst-self-training
description: "On-Policy Self-Training (OPST) 無外部標註與人工題庫的 LLM 後訓練與自我蒸餾方法（arXiv:2610.32770）。在評估或設計無標註資料的模型自我改進（Data-Free Self-Improvement）、比較 OPST 與 SFT／GRPO／OPSD，或判斷某方案是否需要模型權重更新與逐 token 分布監督（而非單純提示詞與記憶）時使用。"
---

# On-Policy Self-Training: Data-Free Self-Improvement in Large Language Models (OPST)

本條目整理論文 **《On-Policy Self-Training: Data-Free Self-Improvement in Large Language Models》**（arXiv:2610.32770，Leon Sick et al., 2026）的核心方法、實驗結論與限制。本檔為外部論文研究之可重用方法包裝，完整數學推導與提示詞模板請查閱原始論文與作者網站。

## 適用情境與基本前提

- **適用情境**：在缺乏人工標註解答（ground-truth answers）與人工策展題庫（human-curated problem sets）時，僅以高階主題描述（coarse topic descriptors）引導大型語言模型或多模態模型進行後訓練（post-training）以放大模型既有潛在能力。
- **必要技術前提**：
  1. **必須具備模型權重更新能力**：OPST 是參數級的後訓練方法，需要更新學生模型參數 $\theta$ 並維護指數移動平均（EMA）老師模型參數 $\phi$。
  2. **必須能取得完整 next-token 機率分布（logits）**：訓練時需在學生自生成的軌跡上，逐 token 計算學生與老師分布之間的歪斜 Jensen-Shannon 散度（skewed JSD）。
- **重要區別（單純提示詞／記憶 $\neq$ OPST）**：若系統僅透過提示詞工程（prompting）、上下文反思或外部記憶庫（memory）讀寫來調整輸出，而**沒有更新模型權重**且**無法存取逐 token 分布進行蒸餾**，則不屬於 OPST。

## 核心方法流程

1. **主題驅動生成課程與特權資訊（Topic-Seeded Curriculum Generation）**：
   - 僅給定粗粒度主題描述 $\tau \in \mathcal{T}$（例如 `"Abstract Algebra"` 或 `"Commonsense Causal Reasoning"`），不提供任何人工題目或參考答案。
   - 由生成器 $\pi_{\text{gen}}$（初始凍結模型 $\pi_{\theta_0}$ 或 EMA 老師 $\pi_{\phi}$）合成問題 $x$ 以及特權資訊（privileged information）$z = (r, a)$，其中 $r$ 為推理過程（rationale），$a$ 為候選答案（candidate answer）。
2. **雙軸品質過濾（Pseudo-Verification & Consensus Gate）**：
   - **偽驗證（Pseudo-Verification，確保題目定義良好與答案一致性）**：
     - **新上下文重解**：要求生成器在不看特權資訊 $z$ 的全新上下文（fresh context）與低溫設定下獨立重解問題 $x$，答案須與候選答案一致（$\hat{a}(x) = a$），將「出題意圖」與「解題」分離。
     - **改寫重解**：要求生成器在保留語義下改寫問題為 $x'$，並於相同條件下重解，答案仍須一致（$\hat{a}(x') = a$），以剔除依賴特定措辭或具歧義的題目。
     - 保留條件：$v(x,z) = \mathbb{I}[\hat{a}(x)=a] \cdot \mathbb{I}[\hat{a}(x')=a] = 1$。
   - **共識閘門（Consensus Gate，確保題目對當前學生具資訊量）**：
     - 由當前學生模型 $\pi_{\theta}$ 對通過偽驗證的問題 $x$ 採樣 $G$ 條 on-policy 軌跡 $\{y_g\}_{g=1}^G$ 並抽取答案 $\{\hat{a}_g\}_{g=1}^G$。
     - 若學生所有採樣皆已穩定答對候選答案（$c(x,z) = \frac{1}{G}\sum_{g=1}^G \mathbb{I}[\hat{a}_g = a] = 1$），代表題目對學生過於簡單、老師能提供的額外訊號極少，直接剔除。留下的題目因此位於學生的能力邊界（capability frontier），且隨學生進步自動提升課程難度。
3. **基於自生成特權資訊的 On-Policy 自我蒸餾（On-Policy Self-Distillation）**：
   - **不對稱條件化（Asymmetric Conditioning）**：學生與老師共享同一模型架構，但**學生只看問題 $x$** 並自行生成 on-policy 軌跡 $y \sim \pi_{\theta}(\cdot \mid x)$；**老師額外看特權資訊 $z=(r,a)$**，在學生訪問的每個前綴狀態 $y_{<t}$ 提供逐 token 的下一詞預測分布 $q_t = \pi_{\phi}(\cdot \mid x, z, y_{<t})$ 作為密集監督（梯度不流經老師）。
   - **歪斜 Jensen-Shannon 散度（Skewed JSD，$\alpha = 0.8$）**：定義混合分布 $\bar{q}_{i,t} = (1-\alpha)q_{i,t} + \alpha p_{i,t}$，設定 $\alpha = 0.8$（偏向 mode-seeking 的反向 KL 區間）。相較於無界的 KL 散度，Skewed JSD 受二元熵 $H(\alpha)$ 上界約束，可防止合成提示中的局部雜訊或極端低機率 token 主導梯度更新。
   - **EMA 老師穩定更新與最終評估**：老師初始化自學生（$\phi_0 = \theta_0$），每步梯度更新後以指數移動平均 $\phi_k = (1-\beta)\phi_{k-1} + \beta\theta_k$ 更新（論文消融最佳值為 $\beta = 0.05$）。EMA 能平滑合成資料帶來的批次雜訊、避免自我強化漂移；且因 EMA 老師表現穩定優於學生（MMLU 高出 1.8 個百分點），**最終部署與評估的對象皆為 EMA 老師模型 $\pi_{\phi}$**。
4. **多輪迭代與跨輪去重（Iterative Self-Training）**：
   - 將「生成 $\to$ 驗證過濾 $\to$ 蒸餾訓練」重複執行 $N$ 輪，學生與 EMA 老師權重跨輪繼承。
   - 每一輪由演進後的老師重新生成新題目，並**去重（移除與先前輪次重複的題目）**，使老師在出題品質、驗證可靠度與逐 token 監督品質上與學生共同演進。

## 與直接 SFT 及 GRPO 的核心差異

在相同的自生成資料 $(x, z)$ 上，三種訓練範式的本質差異在於**如何對待自生成的候選答案與推理**：

| 方法 | 監督訊號密度 | 自生成答案 $z=(r,a)$ 的角色 | 在純合成資料下的行為與缺陷／優勢 |
| :--- | :--- | :--- | :--- |
| **直接 SFT** | 密集（Dense） | **作為直接優化目標（Target）照抄** | 僅在離線生成的 $z$ 軌跡上強制模仿每個 token（teacher-forcing），產生曝光偏差（exposure bias），且將合成推理中的遺漏或錯誤答案一併當成標準答案照抄（當錯誤答案比例達 75% 時，Gemma 4 E2B MMLU 掉至基線以下 `-4.4` 分）。 |
| **GRPO (RL)** | 稀疏（Sparse） | **按候選答案一致性給純量獎勵（Reward）** | 雖在學生 on-policy 軌跡上訓練，但將題目生成時產生的豐富推理與答案資訊壓縮為單一純量獎勵，丟失步驟級監督訊號，提升幅度有限。 |
| **OPST** | 密集（Dense） | **作為老師的背景上下文（Context）** | 學生走自己的 on-policy 軌跡，老師將 $z$ 視為提示上下文並結合自身參數知識給出逐 token 分布：能自動補全 $r$ 省略的推理步驟、不強迫模仿 $z$ 的表面措辭，且先驗知識能抑制錯誤 $z$ 的影響（即使移除過濾並混入 75% 錯誤候選答案，仍高於基線 `+3.3` 分）。 |

## 實驗結果重點（需區分是否開啟 Thinking）

評估結果需嚴格區分「無思考（w/o Thinking）」與「開啟思考（w/ Thinking）」模式，避免混淆基線與增幅：

- **Gemma 4 E2B（MMLU 基準）**：
  - **無思考（w/o Thinking）**：Base `37.5` $\to$ OPST `47.7`（**+10.2** 分）；同資料下 SFT 為 `38.3`（+0.8）、GRPO 為 `37.3`（-0.2）。
  - **開啟思考（w/ Thinking）**：Base `69.9` $\to$ OPST `71.1`（**+1.2** 分）；因思考模式下基線已高，MMLU 剩餘空間較小，但 GPQA（`27.8` $\to$ `34.3`，+6.5）與 GSM8K（`72.7` $\to$ `80.9`，+8.2）仍有顯著提升。
- **Gemma 4 E4B（開啟思考 w/ Thinking）**：
  - **GSM8K**：Base `84.4` $\to$ OPST `93.0`（**+8.6** 分；同資料 SFT 為 `87.1`、GRPO 為 `83.2`）。
  - **MMLU**：Base `76.0` $\to$ OPST `80.1`（+4.1 分）；**GPQA**：Base `43.9` $\to$ OPST `48.0`（+4.1 分）。
- **跨模型族泛化（Qwen3-4B-Base，未經指令微調之預訓練基座）**：
  - 四項基準平均由 `66.7` $\to$ `72.7`（+6.0 分），其中 GSM8K `+13.3`、GPQA `+5.1`、MMLU `+3.1`、HellaSwag `+2.5`。
- **多模態延伸（Visual OPST）**：
  - 在 OpenImages 未標註圖片上，以模型自生成的詳細場景描述（scene caption）與物件邊界框空間關係（spatial relations）作為特權資訊，並要求候選答案在色彩抖動、縮放與隨機裁切（不含水平翻轉）的擴增視圖間保持一致。Gemma 4 E2B 在 VQAv2 提升 `+6.9` 分，POPE 召回率提升 `+4.5` 分（E4B 提升 `+6.2` 分）。

## 論文限制與工程推論邊界

### 1. 論文已確認之限制（Verified Limitations）
- **一致性不等於正確性（Consistency $\neq$ Correctness）**：偽驗證（新上下文重解與改寫重解）本質上衡量的是模型的「自我一致性」而非客觀正確性；若模型對某類問題抱持穩定一致的錯誤認知，該錯誤仍會通過過濾進入訓練。
- **只能放大既有知識（Amplifies Existing Knowledge Only）**：OPST 依賴模型自身的參數知識生成題目與特權監督，無法憑空灌輸模型預訓練中完全不存在的新事實或外部知識。
- **小模型實驗證據**：論文實驗僅在小型模型（Gemma 4 E2B、Gemma 4 E4B 與 Qwen3-4B-Base）上驗證，尚未在更大規模模型上實證。
- **非無限進化（飽和與退化現象）**：多輪自訓練並非輪數越多越好。在 Gemma 4 E2B MMLU（無思考）消融實驗中（Table 6c），第 0 輪為 `37.5`、第 3 輪為 `43.1`、**第 7 輪達到峰值 `47.7`**，但繼續訓練至 **第 12 輪與第 20 輪時回落並維持在 `46.2`**，顯示合成誤差累積與收益飽和。
- **視覺版仍需未標註圖片**：文字版 OPST 僅需主題名稱即可零資料啟動，但 Visual OPST 仍必須提供真實的未標註圖片集合（unlabeled images）作為輸入。
- **混合領域之局部退化**：多領域混合訓練雖能維持大多數領域外（OOD）表現，但在三領域混合實驗中 MATH-500 出現 `-4.9` 分的退化。
- **官方程式碼狀態**：作者專案網站目前標示 **`Code (Coming Soon)`**，尚無官方公開程式碼倉庫。

### 2. 實務 Agent 系統之延伸建議（工程推論，非論文已證實結果）
> **⚠️ 注意：以下內容屬於將 OPST 概念借鏡至實務 Agent 系統的工程推論（Engineering Inference），並非原論文已實證之結果。**
- 原論文在 Limitations 中僅將「工具或檢索接地驗證（tool- or retrieval-grounded verification）」列為未來方向。
- 在實務程式碼或任務型 Agent 場景中，若借鏡 OPST 的題目合成與篩選機制，**建議將純內部一致性的「偽驗證」替換或結合外部測試／執行結果驗證**（例如：實際執行單元測試、編譯器檢查、沙盒執行回饋或確定性驗證器），以避免模型將「前後一致的幻覺」當成特權資訊進行自我強化。此結合外部執行驗證的做法屬於工程推論與實務延伸，非論文實驗已證實之結論。

## 來源與參考連結

- **Hugging Face Paper 頁面**：https://huggingface.co/papers/2610.32770
- **arXiv 論文摘要**：https://arxiv.org/abs/2610.32770
- **arXiv HTML 全文**：https://arxiv.org/html/2610.32770v1
- **arXiv PDF 全文**：https://arxiv.org/pdf/2610.32770
- **作者專案網站（Code Coming Soon）**：https://leonsick.github.io/opst/
