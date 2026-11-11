---
name: speculative-forcing
description: "記錄與評估 Speculative Forcing（arXiv:2610.22347）：以 token-wise early commitment、training-free 或 learned verifier 加速 few-step autoregressive video diffusion、LongLive 串流影片生成與 Lingbot-World 2.0 世界生成。適用於減少去噪計算、理解 KV cache 保留機制、比較速度與品質，以及查核官方程式碼和權重釋出狀態。"
---

# Speculative Forcing

## 方法與適用時機

論文 **Speculative Forcing for Efficient Autoregressive Video Generation**（KAIST AI / NAVER AI Lab，2026）提出少步數自回歸影片擴散模型的推論加速框架。每步 clean latent estimate 作為 draft；verifier 判斷個別 token 是否已足夠接近完整步數輸出，接受後固定輸出並跳過後續去噪，保留其逐層 keys / values 供尚未完成的 tokens 使用。每個 chunk 完成後仍須以 assembled clean output 執行 clean forward，更新後續 chunk 的 KV cache。

用於研究或評估串流影片、長影片及相機控制世界模型的速度／品質取捨。論文測試 LongLive 1.3B 與 Lingbot-World 2.0 Causal-Fast 1.3B，皆為四步去噪；生成器權重保持凍結。

兩種 verifier：

- **Training-free**：第一步比較 draft 與 clean history／reference tokens 的相似度；之後比較相鄰步 draft 的穩定度。兩個閾值須以 held-out data 校準。
- **Learned head**：以生成器最後一個 transformer block 的特徵預測距完整步數輸出的 normalized gap；僅訓練 LayerNorm + 三層 3D convolution head（4.11M 參數），使用 full-step rollout 標籤與 Huber loss。兩者皆先平滑時空分數再接受 token。

相關：[speculative-decoding](../speculative-decoding/SKILL.md) 處理 LLM draft／verify 加速；此方法借用該概念，但不採用其 exact acceptance rule，也未宣稱輸出分布完全等價。

## 如何執行與釋出狀態

**查核日期：2026-11-11。** [官方 GitHub README](https://github.com/naver-ai/speculative-forcing) 表示程式碼仍在內部審查、將於之後釋出；目前 repo 僅有 README。

- **安裝與推論命令**：官方尚未提供，無可核實的可執行 quick start；不要把基底模型命令當成已整合此方法的實作。
- **權重／模型卡**：官方來源未提供 verifier checkpoint、下載命令或此方法的 HF model card；HF paper API 的 linked models 為空。
- **硬體**：論文在單張 NVIDIA H100 測量吞吐；最低 VRAM、消費級 GPU 相容性、套件版本與 CUDA 環境尚未公布。

實際執行前先重查官方 repo 的安裝文件、對應基底模型與 verifier 權重、推論入口及授權；依正式釋出的原始命令操作。目前可依 [論文 §3、附錄 A](https://arxiv.org/html/2610.22347v1) 理解實作，但不能宣稱已可直接執行或已重現。

論文參考設定：保留原四步 schedule `[1000.0, 937.5, 833.3, 625.0]`；learned verifier 的 ε 為短片 `0.28`、長片與世界生成 `0.24`。這些是實驗設定，尚無官方 CLI flags。實作時須保留 accepted-token KV、只對 active tokens 繼續 forward，並在 chunk 結束刷新 clean KV。

## 輸入與輸出

- **LongLive**：文字提示、噪聲及先前生成的 latent chunks → 串流影片；論文評估 5 秒與 30 秒影片。
- **Lingbot-World 2.0**：初始影像、文字提示、逐幀相機軌跡及生成歷史 → 相機控制的世界影片；評估每段 253 frames，沿用基底模型的相機條件路徑。
- **Verifier**：中間 clean estimates／歷史，或生成器 hidden features → 每個 token 的接受決策；最終 chunk 混合不同步數已接受的 clean estimates。公開檔案格式與 CLI I/O schema 未知。

## 論文結果與限制

以下為 learned verifier 相對四步基線的作者報告，非本地重現（[官方專案頁](https://speculative-forcing.github.io/)）：

| 場景 | 平均去噪步數／token | 基線 → 本方法 FPS | 品質分數：基線 → 本方法 |
| --- | --- | --- | --- |
| LongLive 5 秒 | 1.68 | 26.40 → 41.74（約 1.58×） | VBench total：83.08 → 83.21 |
| LongLive 30 秒 | 1.72 | 24.5 → 37.8（約 1.54×） | VBench-Long total：82.69 → 82.81 |
| Lingbot-World 2.0 | 2.55 | 18.1 → 24.5（約 1.35×） | 六維 VBench quality：82.62 → 82.65 |

吞吐以單張 H100 的 **DiT forward time** 計算，排除 VAE encoding／decoding；平均去噪步數排除 clean KV refresh pass，不能直接視為端到端 FPS 或 `4 / mean_steps` 加速。上述品質分數使用不同評估協定，不宜跨列直接比較。

加速幅度依生成器與場景而變；大幅相機運動、剛顯露的內容通常需要更多步。放寬接受閾值可能過早固定未完成內容並降低品質；仍須驗證一致性、Drift 與相機軌跡誤差。尚未證明可直接泛化至任意影片模型。

## 授權與來源

- 論文：arXiv 標示 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。
- 程式碼／verifier 權重授權：目前官方 repo 無 LICENSE、無權重授權資訊，**未知**；論文授權不代表程式碼或基底模型授權。
- [Hugging Face paper：2610.22347](https://huggingface.co/papers/2610.22347)
- [arXiv 摘要](https://arxiv.org/abs/2610.22347) · [完整論文與附錄](https://arxiv.org/html/2610.22347v1) · [PDF](https://arxiv.org/pdf/2610.22347)
- [官方專案與示例](https://speculative-forcing.github.io/) · [官方 GitHub／釋出狀態](https://github.com/naver-ai/speculative-forcing)
