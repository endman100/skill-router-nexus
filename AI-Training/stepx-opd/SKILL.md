---
name: stepx-opd
description: "在評估或設計文生圖 diffusion／flow-matching 模型的少步採樣蒸餾、多教師能力整合，或比較聯合訓練與先做 on-policy distillation（OPD）再壓縮採樣步數時使用。涵蓋 StepX-OPD 的教師路由、軌跡分布匹配、低噪聲速度回歸、實驗與公開實作。"
---

# StepX-OPD 多教師在策略蒸餾

StepX-OPD（專案頁網址為 Step-OPD）是 Wang 等人提出的文生圖後訓練方法。輸入是按能力分組的訓練提示詞、對應的凍結專家與可訓練的學生。學生沿自己當前的少步去噪軌跡產生狀態，在同一次訓練中整合專家的能力並學會少步採樣。論文主實驗輸出四步學生。 [專案頁](https://winterccc.github.io/Step-OPD/) · [論文 v2 §1、§4](https://arxiv.org/html/2611.04386v2#S4)

## 相對標準 OPD 的改變

在文生圖基線中，標準 OPD 在學生造訪的連續去噪狀態上匹配老師的條件轉移。對共享協方差的高斯轉移，逐步 reverse KL 可寫成帶權重的速度平方差。論文比較的 Flow-OPD 與 DiffusionOPD 先整合出一個 40 步模型。串接方案再以這個整合模型為凍結教師，用軌跡分布匹配（Trajectory Distribution Matching，TDM）把採樣壓到 4 步。 [論文 v2 §2–3](https://arxiv.org/html/2611.04386v2#S3) · [表 1](https://arxiv.org/html/2611.04386v2#S4.T1)

StepX-OPD 讓同一位來源對應的專家直接監督少步學生。TDM 匹配學生軌跡經加噪後的中間邊際分布，低噪聲批次另由同一位老師提供直接速度回歸目標。這個訓練流程省去產生中間的 40 步整合模型，仍以已訓練的凍結專家為輸入。 [論文 v2 §4](https://arxiv.org/html/2611.04386v2#S4)

## 訓練流程

1. **初始化與教師路由**。SD3.5-Medium 主實驗在底模加上三個專家增量的平均與全權重 SFT 增量。每批只取一個提示詞來源。前 200 個訓練步用凍結的初始學生自蒸餾，之後以固定對照將 GenEval、OCR、PickScore 批次分別交給 GenEval、OCR、美學專家。主實驗的來源抽樣比例為 1:1:1。 [論文 v2 §5.1](https://arxiv.org/html/2611.04386v2#S5.SS1) · [附錄 C](https://arxiv.org/html/2611.04386v2#A3) · [表 14](https://arxiv.org/html/2611.04386v2#A6.T14)
2. **以學生軌跡建立監督點**。每個訓練步重抽去噪網格的內部節點，端點固定為純噪聲 $t=1$ 與乾淨端 $t=0$。當前學生從高斯噪聲做 Euler rollout。均勻選一段並在段內抽基準時間，線性插值兩端狀態，其中低噪聲端在插值時停止梯度。再從基準時間到該段高噪聲端之間抽監督時間 $\tau$，用精確前向 SDE 轉移加高斯噪聲得到 $z_\tau$。插值的精確性適用於 Euler 軌跡。 [論文 v2 §4.2](https://arxiv.org/html/2611.04386v2#S4.SS2) · [附錄 A.2](https://arxiv.org/html/2611.04386v2#A1.SS2)
3. **匹配邊際分布**。在 $z_\tau$ 訓練輔助的 fake-score 模型（critic）估計學生分布的 score。TDM 以其估計與當批老師提供的目標之差建立學生更新，附錄 B 用速度表示兩者並以 pseudo-Huber 實作學生損失。 [論文 v2 §3](https://arxiv.org/html/2611.04386v2#S3) · [演算法 1](https://arxiv.org/html/2611.04386v2#algorithm1)
4. **回歸低噪聲速度**。SD3.5-Medium 主實驗從訓練第 500 步起，在批次平均 $\bar\tau\leq0.5$ 時加做一次學生前向，用逐元素 MSE 擬合同一凍結老師在同一狀態和時間的引導速度。總損失加上係數 0.5 的這一項。論文主設定對 MSE 採逐元素平均。理論分解中，$w_b(t)=(t_i-t)(1-t)/t$ 在區段內偏重低噪聲時間，其中 $t_i$ 是區段的高噪聲端。分解用的是分布誘導的速度場，換成網路速度須考慮老師一致性與學生自一致性。 [論文 v2 §4.3](https://arxiv.org/html/2611.04386v2#S4.SS3) · [附錄 A.5](https://arxiv.org/html/2611.04386v2#A1.SS5)

SD3.5-Medium 主實驗以 rank-32 LoRA 訓練學生與 critic，學習率分別為 $2\times10^{-6}$ 與 $10^{-5}$。論文使用 4 個 FSDP process、每個 64 筆，全域 batch 256。GitHub 發布的是 SD3.5-Medium 的 $w_b$ 變體，在速度回歸加入受邊際 KL 分解啟發的樣本權重，其公開配置採 8 個 GPU 各 32 筆，同為全域 batch 256。 [論文 v2 §5.1](https://arxiv.org/html/2611.04386v2#S5.SS1) · [官方 GitHub](https://github.com/WinterCCC/StepX-OPD) · [公開設定](https://github.com/WinterCCC/StepX-OPD/blob/main/configs/sd35m_wb.yaml)

## 與相關方法的對照

| 方法 | 學生生成的狀態與訓練資料 | 教師訊號與用途 |
| --- | --- | --- |
| StepX-OPD | 每批取自單一能力的提示詞來源，狀態由當前文生圖學生的少步去噪軌跡構造 | 暖身後由該來源的凍結專家供應 TDM 邊際分布匹配及低噪聲速度回歸目標，同時整合能力與壓縮步數 |
| 標準 OPD | 文生圖基線使用學生的去噪狀態，O³PD 的語言模型基線在固定題集上由學生生成回答前綴 | 文生圖基線匹配條件去噪轉移，表 1 的整合模型採樣 40 步。語言模型基線在學生前綴擬合老師的下一 token 機率 |
| [O³PD](../order-only-on-policy-distillation/SKILL.md) | 從既有數學題目採樣，當前語言模型學生生成回答前綴 | 凍結老師只提供有序 top-$K$ token ID，用相鄰候選的 Bradley–Terry 損失學排序 |
| [OPST](../opst-self-training/SKILL.md) | 由粗粒度主題生成並篩選問題與特權資訊，當前語言模型學生只看問題並採樣回答 | 以學生的 EMA 老師讀取推理與候選答案，在學生前綴給下一 token 分布，以 skewed JSD 自蒸餾 |

StepX-OPD 的實驗與 O³PD、OPST 的結果分屬文生圖與語言模型後訓練，來源未比較。標準 OPD 的兩種設定分別依 StepX-OPD 論文與 O³PD skill。 [論文 v2 §3](https://arxiv.org/html/2611.04386v2#S3) · [O³PD 的 OPD 基線](../order-only-on-policy-distillation/SKILL.md#標準-opd)

## 主要結果

論文 v2 表 1 在 512×512 評估。Average 是 GenEval、OCR、DeQA 除以 5、PickScore 除以 26 四項的等權平均。下表皆為論文 v2 的 Average，括號內為採樣步數。 [表 1](https://arxiv.org/html/2611.04386v2#S4.T1) · [評估設定](https://arxiv.org/html/2611.04386v2#A3)

| 底模 | StepX-OPD（4） | Flow-OPD + TDM（4） | DiffusionOPD + TDM（4） | Flow-OPD（40） | DiffusionOPD（40） |
| --- | ---: | ---: | ---: | ---: | ---: |
| SD3.5-Medium | **0.8901** | 0.8345 | 0.8403 | 0.8788 | 0.9022 |
| FLUX.1-dev | **0.8902** | 0.8695 | 0.8761 | 0.8864 | 0.8943 |

- 兩個底模的 StepX-OPD 都在四步比較中取得最高 Average、GenEval 與 OCR。SD3.5-Medium 的 GenEval／OCR 為 0.944／0.899，FLUX.1-dev 為 0.890／0.929。兩個底模的四步 DeQA 與 PickScore 最高分均由其他方法取得。四步模型各用 4 次網路評估（NFE），兩個底模的 40 步比較分別用 80 與 40 NFE。 [表 1](https://arxiv.org/html/2611.04386v2#S4.T1) · [附錄 C](https://arxiv.org/html/2611.04386v2#A3)
- SD3.5-Medium 的論文表 22 回報所比較的訓練階段耗時 72.7 GPU 小時，串接的 DiffusionOPD + TDM 為 115.7 GPU 小時，約少 37%。 [表 22](https://arxiv.org/html/2611.04386v2#A6.T22)
- SD3.5-Medium 消融中，依來源路由、隨機指定老師、平均老師速度的 Average 依序為 0.8901、0.8410、0.8230。另一組控制實驗停用速度回歸、第 0 步啟用、第 500 步啟用的 Average 為 0.8722、0.8895、0.8901。 [表 3](https://arxiv.org/html/2611.04386v2#S5.T3) · [表 6](https://arxiv.org/html/2611.04386v2#S5.T7.fig1)
- 專案頁另列 SD3.5-Medium 的 $w_b$ 加權變體，四步 Average 為 0.8906，GenEval／OCR 為 0.946／0.897。論文 v2 表 1 的 0.8901 對應其未做樣本權重的主設定。 [專案頁結果與回歸消融](https://winterccc.github.io/Step-OPD/) · [論文 v2 附錄 A.5](https://arxiv.org/html/2611.04386v2#A1.SS5)

## 限制與公開資源

- **非預期文字**。在不預期有文字的 4,899 張圖／模型的評估中，SD3.5-Medium 底模有 21 張圖重現提示詞文字，DiffusionOPD 有 218 張，四步 StepX-OPD 有 94 張。可選的 precise teacher 將老師短程去噪中的引導速度取平均，將 94 降至 84，啟用的 500 步期間每個訓練步多 4.33 秒。 [附錄 C](https://arxiv.org/html/2611.04386v2#A3) · [附錄 E](https://arxiv.org/html/2611.04386v2#A5)
- **資料與實證範圍**。表 1 的串接基線以 JourneyDB 做 TDM，StepX-OPD 使用帶來源的 Flow-OPD 提示詞。表 21 額外控制資料來源，StepX-OPD 用這兩套資料的 Average 分別為 0.8300 與 0.8901。JourneyDB 缺少對應的來源標籤，該組實驗任意指定老師。其他模型家族、解析度及文生圖以外任務的效果為未知／未公開（2026-11-24）。 [表 21](https://arxiv.org/html/2611.04386v2#A6.T21) · [實驗設定](https://arxiv.org/html/2611.04386v2#S5.SS1)
- **公開範圍**。官方 GitHub 提供 $w_b$ 變體的 SD3.5-Medium 訓練與推論程式，設定檔需要填入三組本地提示詞檔與權重路徑。Hugging Face 提供四步推論 LoRA 與訓練初始化 adapter。FLUX.1-dev 的官方訓練實作與蒸餾權重為未知／未公開（2026-11-24）。 [官方 GitHub](https://github.com/WinterCCC/StepX-OPD) · [公開設定](https://github.com/WinterCCC/StepX-OPD/blob/main/configs/sd35m_wb.yaml) · [模型卡](https://huggingface.co/ShimaRinC/StepX-OPD-SD3.5)

## 工程推論與未驗證應用

- 若要移植到新的文生圖提示詞分組，可固定資料與評估後，先以來源路由對照隨機派發，再檢查各能力分數與非預期文字。新分組的效益及缺少來源標籤時其他路由策略的效果為未知／未公開（2026-11-24）。

## 來源

- [專案頁](https://winterccc.github.io/Step-OPD/) · [質化比較](https://winterccc.github.io/Step-OPD/comparisons.html) · [非預期文字範例](https://winterccc.github.io/Step-OPD/spillover.html)
- [arXiv 摘要](https://arxiv.org/abs/2611.04386) · [HTML 全文 v2](https://arxiv.org/html/2611.04386v2) · [PDF v2](https://arxiv.org/pdf/2611.04386v2)
- [官方 GitHub](https://github.com/WinterCCC/StepX-OPD) · [Hugging Face 模型卡](https://huggingface.co/ShimaRinC/StepX-OPD-SD3.5) · [互動示範](https://huggingface.co/spaces/hugging-apps/stepx-opd)
