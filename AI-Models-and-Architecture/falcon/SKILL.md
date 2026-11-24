---
name: falcon
description: "Falcon 串流音視訊目標說話者擷取（audio-visual target speaker extraction，AVTSE）。用於評估或比較如何以同步唇部影像從多人混音擷取指定說話者的語音，或查詢 Falcon 架構、RealSSA 評測、延遲與重現限制。"
---

# Falcon 串流音視訊目標說話者擷取

Falcon 以指定說話者的唇部影像為條件，從重疊語音、環境噪聲和混響中擷取該說話者在麥克風端的語音波形。可作為通話、會議或下游 ASR 的語音前處理。選型時先確認能取得同步的唇部影像，再比較分離品質與端到端延遲。

## 方法與管線

1. **對齊輸入**。準備 16 kHz 單聲道混音，以及目標說話者同步的 25 fps、96 × 96 灰階唇部裁切影像。官方推論介面會將影像中心裁切為 88 × 88 並正規化。 [Falcon 模型卡](https://huggingface.co/JusperLee/Falcon)
2. **編碼與融合**。音訊經 STFT，將實部、虛部、幅度送入卷積編碼器，再經 AudioBlock 細化。視訊經凍結的 FRCNN 唇讀編碼器與具因果 LSTM 的 VideoBlock，對齊至音訊幀率後沿頻率軸廣播，與音訊特徵相加。 [論文 §4.1](https://arxiv.org/html/2610.32749v1#S4.SS1)
3. **單次多尺度分離**。非對稱 U-Net 對時間與頻率下採樣三次，形成四個尺度。瓶頸的粗尺度上下文經閘控注入跳接，解碼器逐級還原解析度。時頻細化區塊（TFRB）依序使用頻率軸雙向 LSTM、時間軸單向 LSTM、具時間因果遮罩的二維自注意力。 [論文 §4.2](https://arxiv.org/html/2610.32749v1#S4.SS2)
4. **重建波形**。以分離器輸出預測複數遮罩，乘上原始音訊的編碼特徵，再由音訊解碼器映回複數頻譜，經 iSTFT 生成目標語音。 [論文 §4.1](https://arxiv.org/html/2610.32749v1#S4.SS1)

訓練在負 SI-SNR 重建損失上加入編碼空間的說話者對比損失。共享音訊編碼器以乾淨目標為正例、各近場干擾語音為負例，參照分支停止梯度。負例加權逐步偏向與估計值最相似的干擾語者，以減少串音。此對比損失只在訓練時使用，推論沒有額外運算。 [論文 §4.3](https://arxiv.org/html/2610.32749v1#S4.SS3)

## 評測與關鍵結果

RealSSA-Sim 模擬小型會議室、中型室內、大型公共空間和戶外，包含 1–5 名近場干擾者，部分場景另有 10–15 名遠場干擾者，並變化混響、環境噪聲和突發噪聲。RealSSA-Real 為保留的實錄測試集，涵蓋 8 個場景、10 位說話者及約 84 分鐘音訊。 [RealSSA-Sim](https://huggingface.co/datasets/JusperLee/RealSSA-Sim) · [RealSSA-Real](https://huggingface.co/datasets/JusperLee/RealSSA-Real)

論文表 3 的 SI-SNRi 和 SDRi 均為相對原始混音的改善量，單位為 dB。 [論文 §6.1](https://arxiv.org/html/2610.32749v1#S6.SS1)

| 測試集 | SI-SNRi（dB） | SDRi（dB） |
| --- | ---: | ---: |
| RealSSA-Sim | 7.7 | 8.2 |
| LRS2-2Mix | 14.1 | 14.7 |
| LRS3-2Mix | 16.4 | 16.7 |
| VoxCeleb2-2Mix | 10.5 | 11.8 |

- RealSSA-Sim 的消融中，加入對比損失後，Falcon 的 SI-SNRi 由 7.3 升至 7.7 dB。RealSSA-Real 上，以 RealSSA-Sim 訓練的 Falcon 達到 NISQA 3.615 和 DNSMOS 3.276，後者與 Swift-Net-12 並列。 [論文 §6](https://arxiv.org/html/2610.32749v1#S6)
- 論文報告 0.5M 可訓練參數及 10.6G MACs，含凍結視訊編碼器的釋出模型共有 11.72M 參數。單筆 2 秒片段的前向中位數為 RTX 3090 上 51.3 ms、單執行緒 Xeon Gold 6226R 上 1361.2 ms。 [論文附錄 E](https://arxiv.org/html/2610.32749v1#A5) · [Falcon 模型卡](https://huggingface.co/JusperLee/Falcon)

## 限制與採用判斷

- **串流延遲**。論文設定以 8 ms 音訊步距輸出，視訊需三個未來影格（120 ms）。51.3 ms 測量的是整段前向運算。論文該設定的端到端實測延遲為未知／未公開（2026-11-24）。官方 Studio 每 0.5 秒重算一次 2 秒視窗，比較部署時應記錄實際擷取、緩衝、運算與播放延遲。 [論文附錄 E](https://arxiv.org/html/2610.32749v1#A5) · [Studio 文件](https://github.com/JusperLee/Falcon/blob/main/studio/README.md)
- **視訊依賴**。在 RealSSA-Sim 的 500 筆消融子集中，連續缺失 75% 視訊幀時，SI-SNRi 降至 0.01 dB，完全缺失時為 −9.91 dB。唇部裁切偏移與追蹤錯人的量化結果為未知／未公開（2026-11-24）。 [論文附錄 M](https://arxiv.org/html/2610.32749v1#A13)
- **資料與重現**。模型採單聲道。使用公開的多聲道資料時，記錄取聲道與影音對齊策略。RealSSA-Sim 的公開分片缺少原始逐一近場干擾波形，重現對比訓練需另外取得近場負例。RealSSA-Real 缺少對齊的獨立目標波形，可用 DNSMOS、NISQA 或依其協議計算 WER 和說話者相似度。 [RealSSA-Sim 資料集卡](https://huggingface.co/datasets/JusperLee/RealSSA-Sim) · [RealSSA-Real 資料集卡](https://huggingface.co/datasets/JusperLee/RealSSA-Real)

## 來源與釋出狀態

- 方法圖、音視訊範例與結果。 [Falcon 專案頁](https://cslikai.cn/Falcon/) · [arXiv:2610.32749](https://arxiv.org/abs/2610.32749)
- 訓練、評測與推論程式碼及論文模型權重已公開，採 Apache 2.0。 [官方 GitHub](https://github.com/JusperLee/Falcon) · [Falcon 權重](https://huggingface.co/JusperLee/Falcon/tree/main)
- 兩個資料集均需人工核准，限各資料集卡允許的非商業研究用途。RealSSA-Sim 資料集卡標示 CC BY-NC-ND 4.0 並列出來源素材條款，RealSSA-Real 依其同意及使用條款提供。 [RealSSA-Sim 資料集卡](https://huggingface.co/datasets/JusperLee/RealSSA-Sim) · [RealSSA-Real 資料集卡](https://huggingface.co/datasets/JusperLee/RealSSA-Real)
