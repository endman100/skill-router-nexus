---
name: voxlock
description: "VoxLock 純音訊串流目標說話者擷取（target-speaker extraction，TSE）。用於評估通話或語音代理的 ASR 前處理，從多人混音保留一位來電者，或比較語音樣本選取、串流延遲與 ONNX 量化取捨。"
---

# VoxLock 純音訊目標說話者擷取

VoxLock 從 16 kHz 單聲道混音擷取一位目標說話者的波形，供下游語音辨識使用。模型以約 3 秒的目標語音為條件。樣本可由本次通話取得，因此部署時可只接收一路音訊，免事先提供註冊語音。 [VoxLock 論文 §3](https://arxiv.org/html/2610.40727v1#S3) · [模型卡](https://huggingface.co/arbazsiddiqui/voxlock)

## 方法與管線

1. **取得目標樣本**。整段音檔預設在前 15 秒選出音量最高的 3 秒。即時自動模式先直通原音，累計約 3 秒被判定為語音的幀後才開始擷取。已有目標語音樣本時，可從第一個音訊區塊開始擷取。 [論文 §3.2](https://arxiv.org/html/2610.40727v1#S3.SS2) · [模型卡](https://huggingface.co/arbazsiddiqui/voxlock)
2. **以樣本調節分離**。27M 參數的因果頻帶切分 RNN（BSRNN）沿用 REAL-TSE 的架構。先讓混音頻譜對樣本頻譜做注意力，形成額外輸入通道。接著讓分離器的各頻帶特徵對樣本的逐幀 ECAPA-TDNN 特徵做注意力，將結果乘入各頻帶。 [論文 §3.1](https://arxiv.org/html/2610.40727v1#S3.SS1)
3. **逐塊擷取波形**。分離器預測頻譜遮罩以重建目標語音。ONNX v2 的樣本編碼圖每通話執行一次，輸出正規化的樣本頻譜和各頻帶注意力的鍵與值。逐塊推論圖重用這些特徵，並跨區塊傳遞循環狀態。 [作者說明](https://arbazsiddiqui.me/voxlock) · [論文 §6](https://arxiv.org/html/2610.40727v1#S6)

訓練從 REAL-TSE 的因果檢查點出發，以負 SI-SDR 微調全部權重，包含 ECAPA-TDNN 分支。四階段依序加入 LibriSpeech 模擬通話、AMI 耳麥串音、30 秒長語段，以及不同麥克風距離與室內底噪。 [論文 §3.3](https://arxiv.org/html/2610.40727v1#S3.SS3) · [REAL-TSE 基線](https://github.com/REAL-TSE/wesep-real-tse)

## 評測與關鍵結果

以下是作者報告的 FP32 整段音檔結果。背景漏詞率以只有背景說話的音訊分鐘數為分母。Krisp 用 Parakeet TDT 0.6B v2 轉錄，AMI 用 v3。 [論文 §4–5](https://arxiv.org/html/2610.40727v1#S4)

| 測試集 | WER 未處理 → VoxLock | 背景漏詞／分鐘 未處理 → VoxLock |
| --- | ---: | ---: |
| Krisp，265 段實錄 | 23.21% → 4.95% | 66.48 → 0.11 |
| AMI，開發時曾查看的 134 個窗段 | 33.03% → 10.12% | 78.34 → 2.12 |
| AMI，評分前凍結的 400 個盲測窗段 | 42.95% → 10.63% | 98.19 → 1.17 |

Krisp 上，FP32 即時自動取樣為 5.15% WER，預設 INT8 的整段結果為 5.11%。論文的信賴區間未顯示 FP32 整段與 Krisp VI 2.5 Default 的 WER 有顯著差異。重跑時應記錄取樣模式、模型精度與 ASR 版本。 [論文 §5–6](https://arxiv.org/html/2610.40727v1#S5) · [模型卡](https://huggingface.co/arbazsiddiqui/voxlock)

## 限制與採用判斷

- **目標選取**。自動取樣假設目標是開場較響亮的說話者。若常由旁人先講或多人同時開口，應用實際通話驗證選取，或提供已知的目標樣本。AMI 盲測固定由目標先講，換成錯誤樣本的測試中 WER 為 23.23%。 [論文 §4–5](https://arxiv.org/html/2610.40727v1#S4)
- **延遲與吞吐量**。穩態演算法延遲為 24 ms，另計音訊區塊。在作者的 Xeon 單執行緒 INT8 測試，40 ms 區塊的即時因子為 0.77，20 ms 區塊為 1.10。論文測得 1.2.1 的自動模式另有一次 2–5 秒的單執行緒追趕運算。1.3.0 起 Pipecat 將追趕移到背景執行，未處理完的音框以原音送出。部署時分別量測開場切換和穩態延遲。 [論文 §6](https://arxiv.org/html/2610.40727v1#S6) · [版本紀錄](https://github.com/arbazsiddiqui/voxlock/blob/main/CHANGELOG.md)
- **泛化與副作用**。模型以英語訓練，每次擷取一位說話者。非英語量化結果為未知／未公開（2026-11-24）。Krisp 幾乎沒有背景語音的電話子集，WER 由 3.82% 升至 5.36%。驗證時應同時檢查目標漏詞與背景漏詞，並納入原本乾淨的通話。 [論文 §5、§7](https://arxiv.org/html/2610.40727v1#S5)

## 與 Falcon 的差異

- **輸入**。VoxLock 以 16 kHz 單聲道音訊和目標語音樣本為條件，可從通話內自動取樣。Falcon 以 16 kHz 單聲道混音和同步的 25 fps 目標唇部影像為輸入。 [VoxLock 論文 §3](https://arxiv.org/html/2610.40727v1#S3) · [Falcon 模型卡](https://huggingface.co/JusperLee/Falcon)
- **串流**。VoxLock 的演算法延遲為 24 ms，另計區塊。Falcon 論文設定以 8 ms 音訊步距輸出，視訊需 120 ms 前瞻。同一硬體與輸入條件下的端到端延遲比較為未知／未公開（2026-11-24）。 [VoxLock 論文 §6](https://arxiv.org/html/2610.40727v1#S6) · [Falcon 論文附錄 E](https://arxiv.org/html/2610.32749v1#A5)
- **規模與授權**。VoxLock 約 27M 參數，Falcon 為 11.72M 總參數，含凍結的唇讀編碼器，其中約 0.5M 可訓練。兩者公開的程式碼與權重均標示 Apache-2.0。 [VoxLock 模型卡](https://huggingface.co/arbazsiddiqui/voxlock) · [VoxLock 官方 GitHub](https://github.com/arbazsiddiqui/voxlock) · [Falcon 模型卡](https://huggingface.co/JusperLee/Falcon) · [Falcon 官方 GitHub](https://github.com/JusperLee/Falcon)

## 來源與釋出狀態

- 權重庫公開 PyTorch 的 Safetensors 與設定檔，以及 ONNX v2 的 INT8、INT8-full、FP16 和 FP32 版本。模型卡標示預設 INT8 下載量約 74 MB。 [模型卡](https://huggingface.co/arbazsiddiqui/voxlock) · [檔案列表](https://huggingface.co/arbazsiddiqui/voxlock/tree/main)
- 官方 GitHub 提供訓練、推論、ONNX 匯出與評測程式。Python 套件提供檔案處理、串流及 Pipecat、LiveKit 整合。 [官方 GitHub](https://github.com/arbazsiddiqui/voxlock) · [PyPI](https://pypi.org/project/voxlock/)
- 論文提供方法及各評測的條件，Krisp 評測資料另採 CC BY-NC 4.0。 [arXiv:2610.40727](https://arxiv.org/abs/2610.40727) · [Krisp 資料集卡](https://huggingface.co/datasets/Krisp-AI/VoiceIsolation-Benchmark-Dataset)
