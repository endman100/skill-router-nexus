---
name: dynamic-band-splitting
description: "Dynamic Band Splitting（DBS）、DBS-BSRNN、DBS-TIGER 音源分離方法與官方推論。用於動態頻帶切分、audio source separation、電影音軌 speech/music/SFX 分離、音樂 stems、語者分離，或查詢論文 Learning Where to Split（arXiv:2610.14993）的架構、權重與重現方式。"
---

# Dynamic Band Splitting（DBS）

## 方法與適用情境

論文 **Learning Where to Split: Dynamic Band Splitting for Audio Source Separation**（Bingzhe Zhang、Kai Li、Xiaolin Hu，2026）提出依混合音訊內容調整頻帶邊界的端到端分離框架。適合研究固定頻帶的替代方案，或用已釋出的模型拆解電影音軌。

- 在固定的粗頻率區塊內預測邊界分數，以 hard Top-K 選出固定數量的頻帶，再以內容加權 pooling 形成 band tokens。
- 分離骨幹處理 tokens 後，平滑、展開至原 STFT 網格、沿頻率細化，預測複數遮罩並以 iSTFT 還原波形。訓練以 straight-through estimator 傳遞邊界梯度。
- 支援 BSRNN、TIGER、BS-RoFormer、MelRoFormer。官方 repo 的 DBS-MelRoFormer 另採連續邊界位移與 soft memberships；實作時依對應模型與設定，不將所有變體視為相同 hard Top-K 流程。

## 輸入、輸出與權重選擇

| 場景 | 輸入 → 輸出 | 官方資源 |
| --- | --- | --- |
| DnR v2 電影音軌 | 44.1 kHz mono 混音 → `music, sfx, speech` 三條波形，順序固定 | `JusperLee/DBS-BSRNN-DnR`（約 4.7M 參數）、`JusperLee/DBS-TIGER-DnR`（約 1.0M） |
| MUSDB18-HQ 音樂 | 44.1 kHz stereo 音樂 → vocals、drums、bass、other | repo 的 `configs/musdb/`；已查官方資源未確認對應預訓練權重 |
| EchoSet 語者分離 | 16 kHz、6 秒雙語者混音 → 兩條語音波形 | repo 的 `configs/echoset/`；已查官方資源未確認對應預訓練權重 |

DnR 權重倉庫均包含 `config.json` 與 `model.safetensors`，透過 `from_pretrained` 載入。Python 範例輸入 tensor 為 `[batch, 1, samples]`，把 stereo 取聲道平均成 mono；必須事先準備 44.1 kHz 音檔，`sample_rate=44100` 只是指定分窗所用取樣率，**不會重新取樣**。`return_aux=True` 可取得各區塊預測邊界。

## 官方安裝與推論

使用 Python ≥3.11；先依機器安裝適合的 PyTorch。下列安裝與 Python 範例出自[官方 README](https://github.com/JusperLee/Dynamic-Band-Splitting#-installation)與模型卡。

```bash
git clone https://github.com/JusperLee/Dynamic-Band-Splitting.git
cd Dynamic-Band-Splitting
pip install -r requirements.txt
pip install --no-deps -e .
```

使用 DBS-BSRNN 分離事先準備好的 `soundtrack.wav`：

```python
import soundfile as sf
import torch
from dbs.models import DBSBSRNN
from dbs.engine import separate

model = DBSBSRNN.from_pretrained("JusperLee/DBS-BSRNN-DnR").eval()
audio, rate = sf.read("soundtrack.wav", dtype="float32", always_2d=True)  # 44.1 kHz
mixture = torch.from_numpy(audio.mean(1)).view(1, 1, -1)
with torch.inference_mode():
    music, sfx, speech = separate(
        model, mixture,
        {"mode": "chunked", "chunk_seconds": 3.0, "hop_seconds": 1.5},
        sample_rate=44100,
    )[0]
```

改用 TIGER 時，從 `dbs.models` 匯入 `DBSTIGER`，載入 `DBSTIGER.from_pretrained("JusperLee/DBS-TIGER-DnR")`，改成 6 秒視窗、3 秒 hop。使用模型卡的評測分窗設定比較結果；demo 預設視窗不同。

需要直接上傳音訊／影片、播放、匯出 WAV 與邊界 JSON 時，使用[官方 HF demo](https://huggingface.co/spaces/JusperLee/DBS-Demo)，或在 clone 的 repo 根目錄執行官方本地指令（FFmpeg 須在 PATH）：

```bash
pip install -r demo/requirements.txt
python demo/app.py
```

本地介面位於 `http://127.0.0.1:7860`，首次使用從 Hub 下載權重。demo 支援 CPU／CUDA，`--device cuda` 可指定 GPU；會解碼為 44.1 kHz mono，輸入上限為 10 分鐘、500 MB，影片可匯出替換音軌的 MP4。

## 評測與硬體

重現訓練／評測時使用官方 `configs/dnr/`、`configs/musdb/`、`configs/echoset/`，依資料集準備 manifests 或音樂目錄。以下是 README 對釋出 TIGER 權重的評測指令；`/data/dnr/test` 必須換成已備妥 `mix.json`、`s1.json`、`s2.json`、`s3.json` 的 DnR 測試目錄：

```bash
python -m dbs.evaluate configs/dnr/dbs_tiger.yaml --pretrained JusperLee/DBS-TIGER-DnR data.test_dir=/data/dnr/test
```

論文附錄 F.3 記載訓練使用 8 張 RTX 5090；目前 repo 的 [DnR DBS-BSRNN YAML](https://github.com/JusperLee/Dynamic-Band-Splitting/blob/main/configs/dnr/dbs_bsrnn.yaml) 則設定 4 張 GPU、每卡 batch 1。兩者需分別記錄，依實際配置調整 `trainer.devices`、`data.batch_size`。CPU 可跑本地 demo，CUDA 可用於加速；**最低推論 VRAM、延遲與即時吞吐量未確認**，不可從參數量推算保證值。

## 關鍵結果與限制

以下為[論文](https://arxiv.org/html/2610.14993v1)報告結果，未在本 skill 中重新執行評測：

| 資料集／指標 | 對照 → DBS | 解讀 |
| --- | --- | --- |
| DnR v2，平均 SI-SDR | BSRNN (128)：7.69 → 9.07 dB | 同為 128 bands，增加 1.38 dB |
| DnR v2，平均 SI-SDR | TIGER (128)：8.74 → 10.13 dB | 同為 128 bands，增加 1.39 dB |
| MUSDB18-HQ，四 stem 平均 SDR | MelRoFormer：7.25 → 8.07 dB | 單模型共同估計四 stems，僅使用該資料集訓練資料 |
| EchoSet，SDRi | TIGER：14.22 → 14.55 dB | 雙語者分離；不要與 SI-SDR 混用 |

- 摘要的 **29.0%** 是 DBS-BSRNN 的 9.07 相對原始報告 BSRNN 的 7.03 dB，並非 128-band 對照的相對增益。
- 固定的是 band-token 數量；每個推論視窗只有一組邊界，不在視窗內逐影格改動，也不自動調整 token 預算。
- 固定 token 數不代表算力下降：DnR 的 DBS-BSRNN 為 124.0 G MACs/s，128-band 靜態對照為 76.6 G MACs/s。
- 分離結果可能有串音與人工痕跡；DnR 權重輸出三類音源，音樂四 stems／EchoSet 需使用各自模型與訓練設定。

## 授權與來源

查核日期：2026-11-11。官方程式與兩份 DnR 模型卡標示 **Apache-2.0**；衍生自 BS-RoFormer、Music-Source-Separation-Training、TIGER 的部分程式須保留 [THIRD_PARTY.md](https://github.com/JusperLee/Dynamic-Band-Splitting/blob/main/THIRD_PARTY.md) 內 MIT 聲明。arXiv 論文採 non-exclusive distribution 授權，與程式／權重授權分開看待。

- [HF 論文頁（2610.14993）](https://huggingface.co/papers/2610.14993)
- [arXiv 摘要](https://arxiv.org/abs/2610.14993) · [全文與附錄](https://arxiv.org/html/2610.14993v1) · [PDF](https://arxiv.org/pdf/2610.14993)
- [官方專案頁與音訊比較](https://cslikai.cn/Dynamic-Band-Splitting/)
- [官方 GitHub／安裝與評測](https://github.com/JusperLee/Dynamic-Band-Splitting)
- [DBS-BSRNN-DnR 模型卡](https://huggingface.co/JusperLee/DBS-BSRNN-DnR) · [DBS-TIGER-DnR 模型卡](https://huggingface.co/JusperLee/DBS-TIGER-DnR)
- [官方互動 demo 與本地操作說明](https://huggingface.co/spaces/JusperLee/DBS-Demo/blob/main/README.md)
