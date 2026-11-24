---
name: taomate-fvsr
description: >-
  使用或評估 TaoMate-FVSR 時使用。適合修復既有說話影片中模糊的小臉、嘴唇與牙齒，
  用原音改善口型同步，或以替換語音做視覺配音。也適用於評估 MiniMax-H3 生成片段的人臉後製。
---

# TaoMate-FVSR 音訊引導人臉影片修復

TaoMate-FVSR 用同一個影片擴散 Transformer（DiT）處理原音修復與替換語音的視覺配音。低畫質影片提供臉部結構和動作，參考影格約束外觀，目標語音引導嘴唇動作。全景輸出把修復的人臉貼回原場景，沿用原畫幅。 [論文 §3](https://arxiv.org/html/2611.03393v2#S3) · [專案示範](https://taoliveaigc.github.io/TaoMate-FVSR/)

## 方法與關鍵技術

1. **來源與噪聲混合**。以凍結的因果 VAE 編碼低畫質影片，將來源 latent 與高斯噪聲按比例混合，再從混合狀態沿 flow-matching 路徑去噪。噪聲比例控制保留多少來源資訊，讓模型有空間重建失真的嘴部細節。
2. **三種條件**。凍結的 HuBERT 擷取語音特徵，經可訓練投影與重建視窗對齊。稀疏外觀參考獨立編碼，近期生成影格以序列編碼提供動作歷史，兩者放入不同時間槽。固定的外觀參考可供每個視窗取用。
3. **兩階段訓練**。先用合成退化的人臉圖像與影片學習外觀重建，影片另受時間一致性監督。再以同一人物和場景、口型不同的退化配音片為輸入，按乾淨目標的音訊重建，並加上凍結 SyncNet 的同步損失。
4. **長片推論**。論文以 5 張條件影格加 72 張待重建影格為一窗，步幅 56，重疊 16 張。重用重疊段的 latent 去噪軌跡，並保留因果 VAE 的解碼狀態。 [論文 §3.1–3.4](https://arxiv.org/html/2611.03393v2#S3.SS1)

## 官方推論管線

- **全景**。DWPose（YOLOX／RTMW）定位並裁切成 512×512 頭部區域，準備首幀參考後修復臉部，再做色彩匹配與遮罩融合，貼回原畫幅，以 25 fps 輸出。預裁的 512×512 臉部素材可用 `--cropped` 直接處理。
- **解析度**。CLI 的 1× 與 2× 分別在 512×512 和 1024×1024 推論，預設各用同尺寸的 GPEN-BFR 增強首幀一次。2× 的結果先降回 512×512，才進行全景合成。預裁模式也輸出 512×512。
- **參考與音訊**。用原音做修復，或透過 `--audio` 指定替換語音。完成的參考圖用 `--reference` 跳過 GPEN，外部編輯的首幀用 `--edited-reference` 再經 GPEN。參考圖應保留首幀的人物身分、姿勢、口型與裁切構圖。
- **重現時記錄參考與設定**。論文的 `+` 用 GPT-Image 增強參考，模型和採樣器相同。論文量化評測的 reference guidance 是 1.5，公開 CLI 預設 1.7 且用 GPEN。兩者皆用 10 步 Euler、source noise 0.8、shift 5、audio guidance 4.0 和 seed 42。 [官方推論說明](https://github.com/TaoLiveAIGC/TaoMate-FVSR/tree/main#inference) · [技術指南](https://github.com/TaoLiveAIGC/TaoMate-FVSR/blob/main/docs/inference.md)

## 論文結果

- **原音修復**。150 段說話影片經合成退化，含 4× 降採樣再調回 512×512。基礎版用未退化首幀做參考，LPIPS 0.0793、DISTS 0.0858，皆為受測方法最低。SparkVSR 的 PSNR／SSIM 較高。
- **參考增強**。`+` 版在同一測試的四項無參考品質指標均居首，Sync-C／Sync-D 為 7.453／7.520，PSNR 從 28.67 降至 23.52，LPIPS 從 0.0793 升至 0.2402。
- **替換語音**。`+` 版在 30 段共同測試素材的六項同步與無參考品質指標均居首，Sync-C／Sync-D 為 8.175／7.083。四段原生 MiniMax-H3 示範則以定性比較呈現牙齒邊界和唇部輪廓。 [論文 §4，表 1–2、圖 3](https://arxiv.org/html/2611.03393v2#S4)

## 限制與公開狀態

- 重建的嘴唇和牙齒是生成式估計。原音量化結果依賴合成退化，且支援參考的基線可用未退化的首幀。原生 H3 片段沒有乾淨的配對目標。
- 替換語音測試無配對的目標口型影片。官方 GitHub 說明，30 段是從 44 段有效片依 `+` 版 Sync-C 事後選出的子集。 [官方評測說明](https://github.com/TaoLiveAIGC/TaoMate-FVSR/tree/main#visual-dubbing-under-replacement-audio)
- 公開推論程式與 checkpoint 已釋出。完整訓練程式與內部說話人資料集為未知／未公開（2026-11-24）。 [GitHub](https://github.com/TaoLiveAIGC/TaoMate-FVSR/tree/main) · [模型卡](https://huggingface.co/TaoLiveAIGC/TaoMate-FVSR)

## 工程推論與論文未驗證的應用

- **工程推論**。CLI 在切鏡時重置裁切濾波，模型仍延續固定參考與歷史。人物或視角突變的素材可先按鏡頭各自處理，再檢查裁切、同一人物的外觀、口型與貼回邊緣。 [官方技術指南](https://github.com/TaoLiveAIGC/TaoMate-FVSR/blob/main/docs/inference.md#default-full-scene-pipeline)
- **未驗證的串接**。若需求是 MiniMax-H3 草稿的整段 2K 重生，參考 [open-h3-regenerate-2k](../open-h3-regenerate-2k/SKILL.md)。論文的 H3 示例從原生生成片開始。與 Open-H3 2K 重生串接的處理順序與效果為未知／未公開（2026-11-24）。 [論文 §4.4](https://arxiv.org/html/2611.03393v2#S4.SS4)

## 官方來源

- [專案頁與影音對照](https://taoliveaigc.github.io/TaoMate-FVSR/)
- [論文 arXiv:2611.03393v2](https://arxiv.org/abs/2611.03393v2)
- [GitHub 正式推論版](https://github.com/TaoLiveAIGC/TaoMate-FVSR/tree/main)
- [Hugging Face 權重與設定](https://huggingface.co/TaoLiveAIGC/TaoMate-FVSR)
- [官方實驗性 ComfyUI 整合](https://github.com/TaoLiveAIGC/TaoMate-FVSR/tree/comfyui)
- [MiniMax-H3 示範素材來源模型](https://www.minimax.io/blog/minimax-h3)
