---
name: video-coder
description: >-
  說明 Video-Coder 如何用可執行的 Blender 白模草稿引導影片生成。使用者問到 Video-Coder、
  用 3D 場景控制物件配置、動作與運鏡，或想評估、重現這種兩階段影片生成方法時使用。
---

# Video-Coder

Video-Coder 是以 Qwen3.5-9B 為底座的多模態編程代理。它把文字描述轉為可執行的 Blender Python 場景，讓幾何、物件數量、運動與相機可在生成成片前檢查。下游影片生成器接收原始文字及白模草稿，依文字補上材質與外觀。 [專案頁](https://cywang735.github.io/Video-Coder/) · [論文 §3](https://arxiv.org/html/2611.09894#S3)

## 架構與推論

1. 從提示詞拆出物件與數量、空間關係、動作及運鏡。代理用關鍵影格或 Blender 物理模擬建立動態場景，渲染為固定解析度與幀率的無紋理灰階白模。
2. 在隔離的 Video-Coder Harness 裡反覆編寫、執行和修正。`check_script` 做靜態檢查，`run_blender` 渲染草稿。失敗時回傳錯誤，成功時檢查格式、空畫面、靜止或出框，並回傳等距抽幀供代理觀察。
3. 提交後，Harness 在乾淨目錄從頭重跑腳本，通過檢查才採用重渲染結果。官方批次推論輸入 ID 與文字提示，輸出 Blender 腳本、草稿 MP4 與交接清單。失敗的提示最多嘗試三次，重跑可續接。
4. 官方推論用 MiniMax-H3 Ref2VA 接收提示詞與草稿並輸出成片。 [論文 §3.2](https://arxiv.org/html/2611.09894#S3.SS2) · [官方推論說明](https://github.com/CYWang735/Video-Coder)

## 資料與訓練

- 資料經四階段產生。先改寫公開影片資料的字幕，保留能用 3D 場景表達的描述。用 Gemini 3.8 Flash 在 Harness 產生多輪軌跡，再由 MiniMax-H3 用提示詞與草稿合成參考影片。最後檢查執行有效性、白模品質，並以 Seed2.0 篩掉提示與白模不一致的樣本。
- SFT 使用完整工具互動軌跡學習建場、呼叫工具、判讀回饋及修正。RL 使用提示與參考影片，在同一 Harness 取樣多輪軌跡，以 GRPO 更新代理。下游生成器在訓練中保持固定。
- 執行獎勵為 0 或 1，所有工具呼叫格式正確且最終程式通過檢查才得 1。通過後用 H3 生成成片，由 DashScope 的 Qwen3.8-omni-flash 根據提示與參考片評估物件、佈局、運動、相機，得到 0–1 的影片獎勵。
- 總獎勵是影片獎勵乘 0.5，加上執行獎勵乘 `exp(−目前步數／總步數)`。執行權重從 1 降到約 0.37。
- 論文設定兩階段都用 AdamW，批次大小為 8，SFT 與 RL 學習率分別為 1e−5 與 1e−6。RL 每組 8 條軌跡、最多 100 輪、上下文上限 120K，並遮罩未完成軌跡。
- 官方 README 的 SFT 配方用 ms-swift 全參數微調、128k 上下文及 4 張 H100。RL 用 Apptainer 隔離 Blender，使用 8 張 H100 訓練代理，另用 4 組各 4 張 GPU 供應 H3 rollout。 [論文 §3–4](https://arxiv.org/html/2611.09894#S3) · [官方訓練說明](https://github.com/CYWang735/Video-Coder)
- 資料規模記載不一。專案頁與論文 §3 為 SFT 6k／RL 2k，論文 §4.1、結論及 HF 卡片為 10k／4k。HF 提供 SFT 軌跡及 RL JSON、參考片壓縮檔，公開 RL JSON 有 1,678 筆。各 checkpoint 實際使用的資料筆數與版本為未知／未公開（2026-11-26）。 [專案頁](https://cywang735.github.io/Video-Coder/) · [論文 §4.1](https://arxiv.org/html/2611.09894#S4.SS1) · [HF 資料檔](https://huggingface.co/datasets/Video-Coder/Train-Data/tree/main)

## 基準與限制

| 評估 | 生成器直接生成 | 加入 Video-Coder-9B |
| --- | --- | --- |
| PhyGenBench 平均，MiniMax-H3 | 0.61 | 0.67 |
| PhyGenBench 平均，OmniWeaving | 0.48 | 0.51 |
| VBench-2.0 三項物理維度平均，MiniMax-H3 | 54.58% | 78.19% |

- 以論文表 1–3 為準。PhyGenBench 用 GPT-4o 依官方協議評估。H3 消融中，僅 SFT 得 0.63、固定雙獎勵權重得 0.65、完整退火得 0.67。VBench-2.0 的增幅為 23.61 個百分點，範圍涵蓋力學、熱學與材質。
- 白模主要表達結構與運動。資料篩掉依賴細緻外觀或表情的提示，VBench-2.0 材質分數為 75.02%，低於 CogVideoX-1.5 的 83.19%。跨生成器結果來自 OmniWeaving，其他骨幹成效及端到端推論延遲為未知／未公開（2026-11-26）。 [論文 §4](https://arxiv.org/html/2611.09894#S4)
- **工程推論，論文未驗證**　除錯時先逐項核對白模的物件數量、相對位置、運動時序與相機取景。若白模正確而成片偏離，可固定提示與草稿來比較下游設定，定位哪一階段引入偏差。

## 公開狀態與授權

- 官方 GitHub 公開 Harness、訓練與推論程式，根目錄及 README 未見專案整體授權，整體程式碼授權為未知／未公開（2026-11-26）。 [官方 GitHub](https://github.com/CYWang735/Video-Coder)
- Hugging Face 公開 SFT 與 RL 權重及訓練資料，三個卡片皆標示 Apache-2.0。 [SFT 權重](https://huggingface.co/Video-Coder/Video-Coder-SFT-9B) · [RL 權重](https://huggingface.co/Video-Coder/Video-Coder-9B) · [訓練資料](https://huggingface.co/datasets/Video-Coder/Train-Data)
- 論文為 CC BY 4.0。下游 MiniMax-H3 採 MiniMax H3 Community License Agreement。 [arXiv 摘要](https://arxiv.org/abs/2611.09894) · [MiniMax-H3 授權](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE)
