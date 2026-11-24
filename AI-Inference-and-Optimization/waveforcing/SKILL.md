---
name: waveforcing
description: >-
  說明與評估 Wave Forcing（WaveForcing）多步自回歸影片擴散與 WaveRT。
  使用者要比較串流影片生成方法、理解因果去噪與多 GPU 排程，或查核吞吐量、長片品質及官方釋出時使用。
---

# Wave Forcing

上海交通大學 DENG Lab 提出的文字轉影片方法，以 Wan2.1-T2V-1.3B 為基底，讓不同影片片段在不同噪聲階段同時去噪。Wave Forcing（WF）定義模型看得到哪些上下文以及如何訓練，Wave Runtime（WaveRT）以 Wave Parallelism（WP）執行多 GPU 管線。

## 為什麼特別

論文指出，逐段生成時，下一段通常得等上一段去噪完成，再等一次乾淨歷史的鍵值快取（K/V）刷新。即使去噪只做一步，每段仍佔用兩次串行前向。長片還要兼顧自然動作、主體留在畫面與鏡頭穩定。

WF 讓後面的片段提早開工，讀取前面較乾淨、仍在去噪的片段當下這一層的 K/V。前段的注意力只讀自身與更早的片段，因而可以在後段仍忙碌時繼續往下一層走。各步去噪和快取刷新都有各自的完整模型副本，管線填滿後每輪並行前向可完成一段（1F1C）。例如四步模型每段仍做四次去噪及一次刷新，五張 GPU 在同一輪處理不同片段。

- **Self Forcing、Causal Forcing** 採用已完成的歷史；按本文的快取規則，先完成同一段去噪和刷新，再開始下一段。WF 加入前段即時的中間狀態，並保留乾淨歷史。訓練也沿用 Self Forcing 讓模型從自行生成的歷史學習的思路。
- **Rolling Forcing** 已將不同噪聲的片段聯合去噪，填滿滾動視窗後每次聯合呼叫可產出一段。雙向注意力讓較早片段也能受較晚片段影響，分散到多 GPU 時需要雙向傳遞逐層 K/V。WF 保留混合噪聲，改成只從較早片段向較晚片段傳遞 K/V。論文直接替 Rolling Forcing 套因果遮罩時，短片 Dynamic Degree 由 51.39 降至 37.50，顯示訓練適配的重要性。
- **Live Avatar、HiAR** 也有分階段管線，階段之間傳遞更新後的 latent。Live Avatar 保留各階段固定時間步的 K/V 快照，HiAR 在各層級刷新符合該層級輸出時間步的 K/V。WF 額外跨副本傳送當前 Transformer 層上所有可見較乾淨片段的即時 K/V。
- **Ulysses、Ring** 在一次前向內切分注意力上下文。WP 將不同片段的不同去噪階段分配給完整模型副本，由片段的因果依賴決定哪些 GPU 要互傳 K/V。 [論文 §3、§5 與附錄 D](https://arxiv.org/html/2611.00859v1)

相關技能 `AI-Inference-and-Optimization/speculative-forcing/SKILL.md`、`Video-Generation/hy-nomas/SKILL.md`。

## 生成、訓練與執行管線

1. **生成**　文字和噪聲進入 DiT，片段內做完整注意力，片段間只讀更早片段。每步可用的上下文包含首段錨點、有限的乾淨歷史、本輪正在刷新的乾淨段，以及當輪自身和前段的 K/V。去噪完成後，store 以乾淨 latent 再做一次前向，將 K/V 寫入歷史。
2. **訓練第一階段**　承接 Rolling Forcing 的雙向混合噪聲設定，等機率取 Rolling Forcing 或 Self Forcing 的 rollout 做分布匹配蒸餾（DMD）。四步版從 Self Forcing 的 ODE 權重初始化。五步版沿用 Rolling Forcing 的權重，從第二階段開始。
3. **訓練第二階段**　沿用 LPM 1.0 的 off-policy 做法，將教師連續片段加回不同程度的噪聲，並用較早的乾淨教師片段作 K/V 歷史。同一份預測用 DMD 與感知損失 LPIPS 監督動作與主體。
4. **訓練第三階段**　等機率從 Rolling Forcing、Wave Forcing、Self Forcing 取模型自行生成的 rollout 做 on-policy DMD。WF 路徑讀取自己的 store 歷史，適配部署時的因果上下文。
5. **WaveRT**　以 SGLang Diffusion 的模型實作為基礎。較乾淨的階段往往讀取較少 K/V，能先完成投影與 RoPE，直接把 K/V 寫入接收端預定的注意力緩衝區。接收端在注意力前檢查就緒，讓傳輸與計算重疊。按實測耗時切分的串流 VAE 在專用 GPU 上與 DiT 重疊解碼。 [論文 §2–4](https://arxiv.org/html/2611.00859v1)

## 關鍵結果

下列均為作者報告。品質評測使用 832×480、16 FPS 的影片，短片每支 129 幀，長片以 200 個 MovieGen 提示詞各生成約 100 秒。

| 指標 | Rolling Forcing 五步 | Wave Forcing 五步 |
| --- | ---: | ---: |
| 短片 VBench Total | 81.15 | 81.64 |
| 短片 Dynamic Degree | 51.39 | 94.44 |
| 長片 VBench-Long Quality | 81.18 | 81.26 |
| 長片 Dynamic Degree | 36.63 | 91.45 |
| Subject Preservation ↑ / Camera Drift ↓ | 92.75 / 0.17 | 97.10 / 0.37 |

- **穩定性**　四步 Causal Forcing 的長片 Dynamic Degree 為 96.61，Subject Preservation 為 71.11，Camera Drift 為 11.14。WF 的四步消融移除第二階段後，長片 Dynamic Degree 從 74.97 降至 15.73。 [論文表 1–2](https://arxiv.org/html/2611.00859v1)
- **吞吐量**　1.3B 四步、832×480、BF16／FlashAttention-3 在單節點 8 張 H200（4 去噪、1 store、3 VAE）報告 147.6 DiT FPS 與 134.8 端到端 FPS，相對單 GPU 的 19.06 端到端 FPS 為 7.07 倍。端到端計入 VAE，排除載入和檔案編碼。專案頁將 1.3B 數字標為公開 checkpoint 測得，論文 §5.3／附錄 C.3 將系統測試標為 dummy DiT，兩來源的權重口徑有出入。 [專案頁](https://sjtu-deng-lab.github.io/WaveForcing/#speed) · [論文 §5.3 與附錄 C.3](https://arxiv.org/html/2611.00859v1)
- **平行方式比較**　1.3B–14B 六種規模的 DiT-only 測試使用 dummy 權重且關閉 VAE。同列匹配步數、GPU 數及 SageAttention＋W8A8 後，WP 為 Ulysses／Ring 中較快者的 1.025–2.530 倍，峰值出現在 1.3B。BF16 下 9B 的 WP 略慢於 Ulysses。 [論文 §5.5 與附錄 C](https://arxiv.org/html/2611.00859v1)

## 限制

- 1F1C 描述填滿後的輸出節奏，首段須等管線填充與 VAE 解碼。固定步數下，DiT 的階段數受限於去噪步數加一，每階段占用一份完整模型。端到端吞吐還受 VAE 與輸出路徑限制，論文的總體時間無法單獨歸因於解碼、傳輸或排隊。
- 主體維持與鏡頭漂移指標來自 100 個有明確主體的提示，仰賴追蹤和幾何規則。跨場景泛化、與人類判斷的一致程度，以及固定文字條件以外的提示切換、相機／動作控制和多串流服務仍待評估。
- 14B 的系統結果使用隨機初始化 DiT 與真實 VAE 權重，14B Wave Forcing 的生成品質與正式 checkpoint 為未知／未公開（2026-11-24）。 [論文 §7 與附錄 C](https://arxiv.org/html/2611.00859v1)

## 釋出與來源

- WaveRT 推論程式碼已公開，採 Apache-2.0。參考訓練程式碼也已公開，沿用 RollingForcing 的獨立學術用途授權。 [官方 GitHub](https://github.com/SJTU-DENG-Lab/WaveForcing) · [訓練指南與授權](https://github.com/SJTU-DENG-Lab/WaveForcing/tree/main/training)
- 1.3B 四步與五步 DiT 權重皆已公開，兩份模型卡均標示 Apache-2.0。文字編碼器、分詞器、VAE 及 scheduler 由 Wan2.1-T2V-1.3B 基底提供。 [Hugging Face 模型卡](https://huggingface.co/SJTU-DENG-Lab/WaveForcing-1.3B) · [ModelScope 模型卡](https://modelscope.cn/models/Osc7YuxuanLiu/WaveForcing-1.3B)
- [官方專案頁與示例](https://sjtu-deng-lab.github.io/WaveForcing/) · [arXiv 摘要](https://arxiv.org/abs/2611.00859) · [arXiv HTML 全文與附錄](https://arxiv.org/html/2611.00859v1) · [WaveRT 官方指南](https://github.com/SJTU-DENG-Lab/WaveForcing/tree/main/wave_rt)
