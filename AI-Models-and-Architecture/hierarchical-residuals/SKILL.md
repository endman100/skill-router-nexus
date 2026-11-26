---
name: hierarchical-residuals
description: "在設計或評估 decoder-only Transformer 時，使用 Hierarchical Residuals（HiRes）獨立調整跨區塊殘差寬度與每層運算寬度。適用於比較殘差擴張方法、規劃密集模型或稀疏 MoE 預訓練，以及查閱 arXiv:2610.41711 的架構與基準。"
---

# Hierarchical Residuals（HiRes）

Ziteng Wang 等人的論文 **Hierarchical Residuals: A Minimalist Decoupling of Residual Width from Compute Width**（2026）把 Transformer 的隱藏狀態分成兩個層級。內層以寬度 `d` 執行 attention 與 FFN，外層以寬度 `D` 在區塊間傳遞殘差。`D/d` 和區塊數 `B` 可獨立於 `d` 選擇。

## 架構與前向管線

1. 將 `L` 層切成 `B` 個連續區塊。論文使用等長區塊，每塊有 `L/B` 層，以及 `2L/B` 個 attention／FFN 子層。
2. 將 token embedding 由 `d` 維投影至 `D` 維，得到初始外層狀態。每個區塊入口用專屬的可學習稠密讀取投影 `D → d` 取得內層狀態。
3. 在區塊內依序執行標準 PreNorm 子層。每個子層先對輸入做 RMSNorm，再將 attention 或 FFN 的輸出加回內層殘差。
4. 用專屬的可學習稠密寫回投影 `d → D` 轉換完整的區塊輸出，加到區塊入口的外層狀態，再對總和做 RMSNorm（PostNorm）。
5. 將最後的外層狀態投影回 `d` 維，經最終正規化與語言模型輸出頭得到 logits。推論的前向流程見附錄 A。

讀寫集中在區塊邊界，加上輸入與輸出端共 `2B + 2` 個投影。新增的稠密投影、加法與 RMSNorm 可用標準 PyTorch 執行。增加 `B` 或 `D` 都會提高投影成本。

## 訓練與對照設計

- 以論文預設的 `D/d = 2`、`B = 4` 起步。讀取投影以截取前 `d` 維為近恆等映射，寫回投影以零填充回 `D` 維為近恆等映射。各自用可學習的 sigmoid 純量門控與稠密投影插值，將稠密部分的初始占比設為 `0.1`，改善訓練初期表現。
- 密集模型實驗使用 OLMoE 程式庫、GQA、RoPE、SwiGLU、4,096-token 上下文及 AdamW。學習率先線性暖身至峰值（前 2% 的訓練 tokens），再以 cosine decay 降到峰值的 10%。訓練用 OLMo 2 第一階段語料與 Dolma2 tokenizer。同一規模的各架構使用相同資料順序和全域樣本索引。
- 稀疏 MoE 實驗沿用 OLMoE-1B-7B 配方，64 個專家中每 token 路由至 8 個，使用 4,096-token 上下文、768 的全域 batch size、`4 × 10⁻⁴` 的峰值學習率和 2% 暖身。完整設定見附錄表 9。
- 用標準 PreNorm 殘差做基線。用 HiNorm（每個區塊結束後加 RMSNorm）測量邊界正規化的效果，再用 `D = d` 的 HiRes 對照外層殘差與投影，最後用 `D = 2d` 測量擴寬的效果。
- 依附錄 B 比較 Paloma 的 11 個保留領域的平均驗證損失，以及 MMLU、ARC、HellaSwag 等 12 項任務的平均準確率。比較等 token 的品質時，同時記錄參數與 FLOPs。比較等品質的成本時，按驗證損失對齊。

## 論文結果

| 實驗 | 基線與 HiRes 的比較 |
| --- | --- |
| 密集模型，基線 70M–626M 參數、30B–350B tokens | 驗證損失為 3.00 時，擬合估計基線所需訓練 FLOPs 是 HiRes（`D/d = 2`）的 1.30 倍。 |
| 深度擴展，`d = 512`、30B tokens、8–128 層 | 各測試深度的 HiRes 驗證損失皆低於基線。128 層時從 2.9765 降到 2.9017（`D/d = 2`、`B = 8`）。 |
| 密集模型，`d = 768`、12 層、50B tokens | 驗證損失 3.1941 → 3.1300，平均準確率 46.91% → 47.15%。同一組比較中，VWN-4 的驗證損失更低，mHC-4 的平均準確率更高。 |
| 稀疏 OLMoE-1B-7B，500B tokens | 基線 6.9B 總參數、每 token 啟用 1.3B。HiRes 採 `d = 2048`、`D = 4096`、16 層、4 區塊，加 83.9M 參數。訓練損失 2.3663 → 2.3455，驗證損失 2.3491 → 2.3311，12 項平均準確率 64.24% → 65.38%。 |

- 附錄 F 在 8 GPU、FSDP FULL_SHARD、BF16 的三種密集模型規模上測量完整訓練步。HiRes 的 PyTorch 版本達基線吞吐量的 91.7–93.0%，峰值顯存多 5.5–5.7%。Triton 版吞吐量為 91.7–93.1%，峰值顯存多 3.3–3.4%。附錄 E 的解析計數也顯示 HiRes 的殘差 activation I/O 低於 mHC-4、VWN-4 與 4 區塊 AttnRes。

## 限制與工程推論

- 論文未在固定算力下聯合搜尋 `d`、`D` 和深度，也未測試不等長的區塊。外層狀態保留哪些資訊、內層如何重新利用這些資訊，仍待研究。
- 在 `d = 768`、12 層、50B tokens 的消融中，`D/d` 超過 2 或 `B` 超過 4 後，品質增益趨緩。更深的 128 層實驗中，`B = 8` 的驗證損失仍低於 `B = 4`。
- 自回歸推論的 prefill／decode 延遲、吞吐量與 KV cache 實測為未知／未公開（2026-11-26）。上表的 1.30 倍來自訓練 FLOPs 的擬合，附錄 F 的吞吐量涵蓋前向、反向與最佳化器更新。
- 工程推論，論文未驗證。移植到現有 serving stack 時，可沿用原寬度 attention 的 KV cache 配置，並單獨量測區塊投影與 RMSNorm 對 prefill／decode 的成本。

## 開源、授權與來源

- arXiv 論文採 CC BY 4.0。附錄 A 提供前向偽碼，arXiv 另有論文排版原始檔。[arXiv 摘要](https://arxiv.org/abs/2610.41711) · [PDF 全文](https://arxiv.org/pdf/2610.41711v1) · [TeX 原始檔](https://arxiv.org/src/2610.41711) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- HiRes 專案頁、獨立程式庫、實驗權重、完整訓練設定檔、HiRes 專屬資料釋出與相應授權為未知／未公開（2026-11-26）。HF Papers 未列出連結此論文的模型或資料集，Seed 官方出版條目連到論文 PDF。[Hugging Face Papers](https://huggingface.co/papers/2610.41711) · [ByteDance Seed 出版列表](https://seed.bytedance.com/en/public_papers)
- 基礎 OLMoE 程式與原版模型卡均標示 Apache-2.0。[Ai2 OLMoE GitHub](https://github.com/allenai/OLMoE) · [原版 OLMoE-1B-7B-0924 模型卡](https://huggingface.co/allenai/OLMoE-1B-7B-0924)
- 公開的密集模型訓練語料 OLMo-mix-1124 標示 ODC-BY，Paloma 依子集適用不同條款，下載檔案須同意存取條件。[OLMo-mix-1124 資料卡](https://huggingface.co/datasets/allenai/olmo-mix-1124) · [Paloma 資料卡](https://huggingface.co/datasets/allenai/paloma)
