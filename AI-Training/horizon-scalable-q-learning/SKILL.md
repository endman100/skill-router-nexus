---
name: horizon-scalable-q-learning
description: "在設計、重現或比較長時域離線與離線轉線上強化學習時使用。涵蓋 Horizon-Scalable Q-Learning（HQL）的逐動作閘門、多步 TD 目標、Chunked-HQL、候選動作取樣與基準設定。"
---

# Horizon-Scalable Q-Learning（HQL）

Haoran Xu 等人的同名預印本（arXiv:2611.10987）提出一種 off-policy critic 訓練方法。一步時序差分（TD）在每一步做 bootstrap，長軌跡會累積殘差。固定多步 TD 減少 bootstrap 次數，卻會沿用紀錄裡的次優動作而累積偏差。HQL 依每個紀錄動作的 Q 值決定回傳範圍。論文在確定性鏈、已知終點價值及零均值、弱相關殘差的假設下推導一步 TD 的起點 RMSE 隨時域約按平方根增長。 [論文 §3–4](https://arxiv.org/html/2611.10987v1#S3)

## Critic 訓練管線

1. 從含狀態、動作、獎勵和 episode 邊界的資料集或 replay buffer，抽取連續的決策視窗。每個視窗有 $H$ 個決策，目標預算為 $B$ 時抽取 $B/H$ 個視窗。用行為克隆（BC）學習可取樣的行為策略 $\mu$。
2. 在視窗的每一位置 $i$，從 $\mu(\cdot\mid s_i)$ 抽 $N$ 個候選，以 target critic $\bar Q$ 評分。若紀錄動作的 $\bar Q(s_i,a_i)$ 大於或等於候選最高分，令 $c_i=1$，否則 $c_i=0$。閘門只用排序，無須估計動作密度。
3. 從視窗末端往回算各位置的 TD 目標。$\bar V^\pi$ 是 target critic 對目標策略的 bootstrap 價值，末端的跨步修正項歸零。閘門關閉的位置切斷向前一位置傳遞的修正，切點之後仍有自己的訓練目標。

   $$Y_t = r_t+\gamma\bar V^\pi(s_{t+1})+\gamma c_{t+1}\bigl(Y_{t+1}-\bar Q(s_{t+1},a_{t+1})\bigr).$$

4. 對視窗內每個有效的狀態–動作對回歸其停止梯度的 $Y_t$。遮罩排除超出 episode 邊界的位置並阻止修正跨越邊界。比較基線時，對齊每次更新的 critic 目標數，另外記錄讀取的 transitions 與採樣設定。 [論文 §4.1、§4.3、附錄 A.5](https://arxiv.org/html/2611.10987v1#S4)

論文在表格型設定下以逐決策重要性採樣推導固定點條件，再用行為策略的指數傾斜與由樣本估計的正規化常數，導出反溫度趨近無限時的硬閘門。實作只要求策略能產生候選，因此適用於 flow 或 diffusion sampler。 [論文 §4.2](https://arxiv.org/html/2611.10987v1#S4.SS2)

## 動作選擇與 Chunked-HQL

- 基本架構由 BC flow sampler、critic ensemble 與其 target network 組成。官方 best-of-N 實作以目前的 critic 選取候選，bootstrap 再以 target critic 評估所選動作。閘門寬度 $N$ 可與執行和 bootstrap 的候選數分開。HQL 也可保留原閘門並替換策略擷取方式，論文實測 QAM 與 VGF。 [論文 §5.4](https://arxiv.org/html/2611.10987v1#S5.SS4) · [官方實作](https://github.com/ryanxhr/hql/blob/main/hql/agents/hql.py)
- Chunked-HQL 把 $L$ 個原始動作當成一次決策。critic 對整個 chunk 評分，使用 chunk 內折扣獎勵和與 $\gamma^L$，視窗涵蓋 $L H$ 個環境步並產生 $H$ 個目標。執行時依序送出該 chunk 的動作。當 $H=1$ 時，Chunked-HQL 退化為 Q-chunking。 [論文 §4.3](https://arxiv.org/html/2611.10987v1#S4.SS3)

## 基準與重現設定

| 基準 | 訓練與評估設定 | 論文結果 |
| --- | --- | --- |
| Combination lock | 確定性鏈長 512–4,096 步，含重置動作的視窗比例約 0–75%，用解析的真實 Q 衡量誤差 | 一步 TD 的 RMSE 隨鏈長上升，64 步 TD 在受污染資料上明顯退化，HQL 在各鏈長維持較低 RMSE |
| OGBench | 六組狀態觀測設定，每組五個任務、五個 seeds，episode 上限 500–4,000 步。1M 離線更新加 1M 線上步。HQL 用 32 個 16 步視窗，每次更新 512 個目標，閘門、執行與 bootstrap 都用 best-of-4 | 平均最終成功率 74%，最佳 TD 基線（8 步 TD）49%。表 1 的離線 → 線上平均為 HQL 40% → 74%、Chunked-HQL 41% → 81%、LQL 34% → 62%、QC 21% → 45% |
| OCBench | 八個 50 Hz 模擬操作任務，episode 上限 1,000–5,000 步，單一 seed。1M 離線更新加 1.5M 線上步，1024 個目標／更新。Chunked-HQL 用 $L=25$、$H=8$，閘門 $N=2$，執行與 bootstrap 用 best-of-16 | 平均最終成功率 82%，100 步 TD 為 53%，200 步 TD 為 46% |

- OGBench 使用 4 層、寬 512 的網路、兩個取均值的 critic、10 步 flow sampler、Adam（學習率 $3\times10^{-4}$），$\gamma=0.99$，兩個 giant maze 用 0.995。OCBench 用 8 層、寬 2048 的 residual MLP、HL-Gauss critic，$\gamma=0.9999$。 [論文附錄 A.4–A.6](https://arxiv.org/html/2611.10987v1#A1.SS4)
- OGBench 的 trace 記錄中，77% 只走一步、17% 走兩步、6% 走三步以上，最長六步。消融在固定 512 個目標時比較 $H=8,16,32$，表現相近。另一組消融用 1024 個目標，並同步變動閘門與動作選擇的候選數。$N=4,8,16$ 的平均成功率依序為 59.6%、52.1%、46.1%。 [論文 §5.3、§5.5](https://arxiv.org/html/2611.10987v1#S5) · [附錄 A.8](https://arxiv.org/html/2611.10987v1#A1.SS8)

## 限制與可用性

- 論文指出閘門依賴 critic 自己的排序。Chunked-HQL 的 chunk 內為開迴路，chunk 越長，候選動作向量維度越高。OCBench 的單一 seed 無法衡量種子間變異。實機、分層子目標與 diffusion 策略的 HQL 基準成效為未知／未公開（2026-11-26）。 [論文 §4.3、圖 5、§6](https://arxiv.org/html/2611.10987v1#S6)
- **工程推論，論文未驗證**。移植到新資料時，可同步追蹤開閘率、實際 trace 長度及 rollout 的 Monte Carlo 價值誤差，並以目標預算相同的一步 TD 和無閘門視窗 TD 對照，評估延伸回傳與使用閘門的效果。官方實作提供這些診斷。 [GitHub README](https://github.com/ryanxhr/hql#quick-start)
- 官方 GitHub 公開 JAX 訓練、評估與重現腳本，程式碼採 MIT，arXiv 預印本採 CC BY 4.0。HQL 專用公開權重、Hugging Face 模型卡與獨立資料集為未知／未公開（2026-11-26）。 [程式碼授權](https://github.com/ryanxhr/hql/blob/main/LICENSE) · [論文授權](https://arxiv.org/abs/2611.10987) · [Hugging Face Papers](https://huggingface.co/papers/2611.10987)
- OGBench 與 OCBench 都有上游公開基準資料。官方 HQL 實作用各基準的套件下載資料，OCBench 資料由基準作者託管於 Hugging Face，其資料卡的資料授權標示為未知／未公開（2026-11-26）。 [OGBench](https://github.com/seohongpark/ogbench) · [OCBench 資料卡](https://huggingface.co/datasets/seohongpark/ocbench)

## 來源

- [HQL 專案頁](https://ryanxhr.github.io/hql/) · [作者提供的 PDF](https://ryanxhr.github.io/hql/paper.pdf)
- [arXiv 摘要](https://arxiv.org/abs/2611.10987) · [HTML 全文 v1](https://arxiv.org/html/2611.10987v1)
- [官方 GitHub 與重現設定](https://github.com/ryanxhr/hql) · [Hugging Face 論文頁](https://huggingface.co/papers/2611.10987)
