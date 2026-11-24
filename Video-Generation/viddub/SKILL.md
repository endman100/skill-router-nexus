---
name: viddub
description: >-
  使用或評估 VidDub 時使用。適合已有說話影片與目標語音，要離線重建口型、
  保留原人物與場景，或要判讀替換語音的同步品質與長片接縫時。
---

# VidDub 離線視覺配音

VidDub 接收既有說話影片與目標語音，重建下半臉的口型以匹配目標發音，並以原片約束人物外觀、頭部動作及背景。若流程包含翻譯或語音合成，先產出目標音軌再交給 VidDub。 [論文](https://arxiv.org/abs/2611.03404v2) · [模型卡](https://huggingface.co/AIPeanutman/VidDub)

## 方法

1. **依音訊是否配對調整監督**。原音樣本做全畫面重建。未配對的替換語音樣本遮掉原口型的重建損失，讓凍結的 StableSyncNet 以目標語音監督口型，並保留遮罩外的來源重建。 [論文 §3.1](https://arxiv.org/html/2611.03404v2#S3.SS1)
2. **整窗雙向建模**。Wan2.1-VACE-1.3B 提供影片骨幹與視覺條件，VACE 編碼遮罩後的來源影格及參考圖，音訊轉接器將凍結的 Whisper-small 特徵對齊影格。DiT 在一窗內用雙向注意力處理所有時間位置。 [論文 §3.2](https://arxiv.org/html/2611.03404v2#S3.SS2)
3. **兩步蒸餾**。用 48 步教師模型在原音與替換語音兩種條件下的引導軌跡，訓練兩步學生模型，再用分布匹配蒸餾（DMD）改善壓縮後的視覺品質。公開學生模型每窗固定去噪兩步，推論音訊 CFG 為 1。 [論文 §3.3](https://arxiv.org/html/2611.03404v2#S3.SS3) · [公開設定](https://huggingface.co/AIPeanutman/VidDub/blob/main/config.json)

## 官方推論管線

1. **準備素材與依賴**。選一段至少 81 幀、單一可偵測且大致正面的說話臉。先確認目標語音與畫面長度，公開 CLI 會將音訊重採樣為 16 kHz 單聲道，超長時截斷，過短時補靜音。另備 Wan 的 VAE、T5／tokenizer 與 Whisper-small。 [官方快速入門](https://github.com/LAW1223/VidDub#quick-start) · [推論入口](https://github.com/LAW1223/VidDub/blob/main/scripts/infer.py)
2. **裁切及分窗**。用 MediaPipe 定位人臉，建立臉部裁切、下半臉遮罩及參考影格。正好 81 幀推論一次，長片使用 81 幀視窗、步幅 64、重疊 17 幀的預設設定。每窗使用個別隨機種子並以對應的原片影格為條件。 [論文 §3.4](https://arxiv.org/html/2611.03404v2#S3.SS4) · [官方 GitHub](https://github.com/LAW1223/VidDub)
3. **融合及檢查**。線性融合重疊影格，預設調和下半臉色彩，羽化嘴部遮罩後貼回原場景，保留來源幀率與解析度。驗收時用目標音軌檢查口型，並檢查接縫、牙齒閃爍與遮罩邊界。 [模型卡](https://huggingface.co/AIPeanutman/VidDub) · [論文附錄 K](https://arxiv.org/html/2611.03404v2#A11)

## 關鍵結果與評估

- **遮罩消融**。三個訓練種子的實驗中，移除衝突的原口型重建監督，使替換語音的 Sync-C 提高 0.833 ± 0.040。 [論文 §4.3](https://arxiv.org/html/2611.03404v2#S4.SS3)
- **兩步模型**。替換語音 Sync-C 在 HDTF-30 為 10.102，在 VidDub-Bench 為 8.709。VidDub-Bench 的 256 段合成說話影片都完成生成，FVD 17.50，高於 Lip Forcing 的 15.78 與 Teacher-48 的 15.23。 [論文 §4.2](https://arxiv.org/html/2611.03404v2#S4.SS2) · [專案結果](https://law1223.github.io/viddub-project-page/)
- **長片**。Long-20 的 20 組 60 秒素材全數完成，平均 Sync-C／Sync-D 為 9.399／6.162，末段 5 秒的 Sync-C 為 9.585。單張 H20 的 11.3 fps 來自條件已備妥的計時，含去噪與 VAE 解碼。 [論文 §4.6](https://arxiv.org/html/2611.03404v2#S4.SS6) · [論文附錄 B](https://arxiv.org/html/2611.03404v2#A2)
- 重現時沿用 VidDub-Bench 固定的原音與替換語音配對，分開報告兩種條件。比較分數時一併記錄成功比例與各方法共同得分的子集。Sync-C 衡量同步信心，音素正確性可另用視覺語音辨識評估。 [官方評測指南](https://github.com/LAW1223/VidDub/blob/main/docs/BENCHMARK.md) · [論文 §4.5](https://arxiv.org/html/2611.03404v2#S4.SS5)

## 限制與公開狀態

- 公開模型採離線分窗。大幅度頭動、側臉、遮擋、多臉、嚴重畫質瑕疵與不足 81 幀的片段可能失敗。多臉時 CLI 選每幀最大的人臉。 [官方 GitHub](https://github.com/LAW1223/VidDub#scope-and-limitations)
- 推論與訓練程式已釋出。模型檔案包含 DiT、VACE、音訊轉接器的權重，以及設定和雜湊清單。 [官方 GitHub](https://github.com/LAW1223/VidDub) · [權重檔案列表](https://huggingface.co/AIPeanutman/VidDub/tree/main)
- 程式及權重採 VidDub Individual Commercial and Research License 1.0。個人可商用作品，也允許非商業學術研究。代表營利組織使用須取得書面許可，僅供內部評估且未投入正式營運者除外。對第三方提供 API、網站、機器人或託管推論也須另外取得書面授權。 [授權原文 §2–4](https://huggingface.co/AIPeanutman/VidDub/blob/main/LICENSE)

## 與 TaoMate-FVSR 的差異

- **任務與監督**。VidDub 聚焦替換語音的視覺配音，未配對的訓練樣本遮掉原口型重建損失。[TaoMate-FVSR](../taomate-fvsr/SKILL.md) 支援用原音修復低畫質人臉，也支援替換語音配音。它以配對的退化配音片與乾淨目標訓練，同時保留重建損失及同步監督。 [VidDub §3.1](https://arxiv.org/html/2611.03404v2#S3.SS1) · [TaoMate-FVSR §3.3](https://arxiv.org/html/2611.03393v2#S3.SS3)
- **推論**。VidDub 使用 Whisper-small、兩步去噪，長片以原片條件分窗並線性融合。TaoMate-FVSR 使用 HuBERT、預設 10 步 Euler，跨窗重用重疊區的 latent 去噪軌跡及因果 VAE 解碼狀態。 [VidDub 模型卡](https://huggingface.co/AIPeanutman/VidDub) · [TaoMate-FVSR 官方推論指南](https://github.com/TaoLiveAIGC/TaoMate-FVSR/blob/main/docs/inference.md)
- 相同素材與評測流程下的兩者直接比較為未知／未公開（2026-11-24）。兩篇論文各自報告的 Sync-C 使用不同的測試組合。 [VidDub §4](https://arxiv.org/html/2611.03404v2#S4) · [TaoMate-FVSR §4](https://arxiv.org/html/2611.03393v2#S4)

## 官方來源

- [Hugging Face 模型卡與檔案](https://huggingface.co/AIPeanutman/VidDub)
- [論文 arXiv:2611.03404v2](https://arxiv.org/html/2611.03404v2)
- [專案頁與影音對照](https://law1223.github.io/viddub-project-page/)
- [GitHub 推論、訓練與重現說明](https://github.com/LAW1223/VidDub)
- [VidDub-Bench 固定評測集](https://huggingface.co/datasets/AIPeanutman/VidDub-Bench)
