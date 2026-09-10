---
name: transcribe-taiwan-mandarin
description: 使用 Hugging Face JacobLinCool/TEA-ASR-1.1 將台灣國語音訊轉為繁體中文逐字稿。這是繁體中文台灣國語的語音辨識模型，支援中英夾雜；搭配 Qwen3 Forced Aligner 產生字詞時間戳。當使用者要求 TEA-ASR、台灣華語、台灣國語、繁體中文語音辨識、zh-TW ASR、Taiwan Mandarin speech-to-text、強制對齊、Qwen3-ForcedAligner，或將此模型的逐字稿製作成字幕時間軸時使用。
---

# 台灣國語語音辨識 — TEA-ASR

以 `JacobLinCool/TEA-ASR-1.1` 為預設模型，辨識台灣國語並輸出繁體中文與台灣用語。將中英夾雜依原話轉錄；不要把英文翻譯成中文。此處「台灣國語」指 Taiwan Mandarin，不能視為台語／閩南語辨識能力保證。

## 確認輸入與環境

1. 取得音訊路徑及輸出位置；沒有音訊時先請使用者提供，勿虛構逐字稿。
2. 確認 Python、PyTorch 與可用運算裝置。初次載入會下載模型權重，預留磁碟與記憶體；本 skill 本身不包含權重。
3. 在工作用虛擬環境安裝 `qwen-asr`。若 CUDA／PyTorch 不相容，依下方官方套件文件處理並記錄錯誤，不宣稱已完成推論。
4. 若來源是影片，先擷取音軌。保留原檔；用 FFmpeg 轉換的範例：

```sh
ffmpeg -i input.mp4 -vn -ac 1 -ar 16000 speech.wav
```

## 執行轉錄

使用模型卡的 `qwen-asr` API，設定 `language="Chinese"`；不要傳入未確認支援的 `zh-TW` 語言參數。

```sh
python -m pip install qwen-asr
```

將以下 Python 範例中的路徑改成實際輸入與輸出，再執行：

```python
from pathlib import Path
from qwen_asr import Qwen3ASRModel

source = Path("speech.wav")
if not source.is_file():
    raise FileNotFoundError(source)

model = Qwen3ASRModel.from_pretrained("JacobLinCool/TEA-ASR-1.1")
result = model.transcribe(audio=str(source), language="Chinese")[0]
Path("transcript.txt").write_text(result.text, encoding="utf-8")
print(result.text)
```

需要人名、產品名或術語提示時，在 `transcribe` 增加 `context="使用者提供的專有名詞"`。提示只能協助辨識，不能當作音訊中確實出現的內容。

## 常用延伸：Qwen3 Forced Aligner

需要字詞時間戳、字幕或校稿後重新對齊時，搭配 `Qwen/Qwen3-ForcedAligner-0.6B`。它是 Qwen 官方提供的獨立配套模型，並非 TEA-ASR 權重的一部分；透過同一個 `qwen-asr` 套件使用，首次載入需另外下載權重。

區分兩種工作：TEA-ASR 辨識說了什麼；Forced Aligner 將文字定位到音訊時間。對齊成功不代表文字正確，也不提供說話者分離。

### 轉錄時一併取得時間戳

以此範例取代上方純文字範例。以下使用支援 BF16 的 CUDA GPU；依實際硬體調整兩個模型的裝置及 dtype，勿假設所有機器均符合此設定。

```python
import json
from pathlib import Path
import torch
from qwen_asr import Qwen3ASRModel

model = Qwen3ASRModel.from_pretrained(
    "JacobLinCool/TEA-ASR-1.1",
    dtype=torch.bfloat16,
    device_map="cuda:0",
    max_inference_batch_size=1,
    max_new_tokens=4096,
    forced_aligner="Qwen/Qwen3-ForcedAligner-0.6B",
    forced_aligner_kwargs={
        "dtype": torch.bfloat16,
        "device_map": "cuda:0",
    },
)
result = model.transcribe(
    audio="speech.wav",
    language="Chinese",
    return_time_stamps=True,
)[0]
if result.time_stamps is None:
    raise RuntimeError("未取得對齊時間戳")
spans = [
    {"text": item.text, "start": item.start_time, "end": item.end_time}
    for item in result.time_stamps
]
Path("transcript.txt").write_text(result.text, encoding="utf-8")
Path("alignment.json").write_text(
    json.dumps(spans, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

### 對齊已校正的繁體逐字稿

已有與音訊一致的逐字稿時，可單獨載入 aligner，不必重新辨識。以原始辨識稿或逐字校正稿為輸入，勿使用摘要、翻譯或任意改寫過的稿件。

```python
import json
from pathlib import Path
import torch
from qwen_asr import Qwen3ForcedAligner

text = Path("transcript.txt").read_text(encoding="utf-8").strip()
if not text:
    raise ValueError("逐字稿不可為空")
aligner = Qwen3ForcedAligner.from_pretrained(
    "Qwen/Qwen3-ForcedAligner-0.6B",
    dtype=torch.bfloat16,
    device_map="cuda:0",
)
aligned = aligner.align(audio="speech.wav", text=text, language="Chinese")[0]
spans = [
    {"text": item.text, "start": item.start_time, "end": item.end_time}
    for item in aligned
]
Path("alignment.json").write_text(
    json.dumps(spans, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

### 對齊品質與字幕處理

- 時間單位為秒；中文輸出可能以字為單位，英文則為詞，不要假設每項都是完整中文詞。保留原始繁體逐字稿，對齊結果中的標點及分詞不一定與原稿一一對應。
- 官方模型範圍為最長 5 分鐘的語音。單獨呼叫 `align` 前，將更長音訊切成不超過 5 分鐘且文字一致的片段；重組時加回各段時間偏移。不要假設 standalone API 會自動切段。
- 核對時間非負、起點不晚於終點、時間順序及音訊長度；對零長度、異常重疊、漏字與中英切換處抽聽檢查。發現漂移時先檢查文字與音訊是否一致。
- 製作 SRT／VTT 時，依停頓、標點與可讀性合併字詞，使用實際對齊起訖時間。此 JSON 是對齊資料，還不是字幕檔。
- 此處以官方 Qwen3-ASR API 配合 TEA-ASR 的相容載入方式編寫；仍須以實際音訊驗證繁體中文及中英夾雜的對齊品質。

## 檢查與交付

- 確认輸出檔可讀，並抽聽片段核對繁體字、台灣用語、專有名詞與英文保留情形。不要預設套用簡繁轉換或潤稿；若需修訂，保留原始辨識稿與修訂稿。
- 空輸出時檢查音軌、靜音、解碼錯誤與執行紀錄；不要填入推測內容。
- 純文字流程輸出逐字稿；需要字幕時間軸時使用上方 Qwen3 Forced Aligner 流程，勿以字數估算時間冒充模型時間戳。說話者標籤仍需另外的分離工具。
- 長錄音若需切段，記錄片段順序、偏移及接縫；合併時檢查漏字與重複。
- 交付 UTF-8 逐字稿、模型 ID、實際執行環境及未能核實的片段。只有真正跑過音訊才能宣稱轉錄完成。

## 官方來源

- [TEA-ASR-1.1 模型卡](https://huggingface.co/JacobLinCool/TEA-ASR-1.1)：模型定位、載入方式、語言參數與 context 用法。查閱日期：2026-09-10。
- [Qwen3-ASR 官方套件](https://github.com/QwenLM/Qwen3-ASR)：部署需求、裝置設定及進階功能；需要這些設定時再查閱。
- [Qwen3 Forced Aligner 模型卡](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B)：配套模型及音訊範圍。
- [官方 ForcedAligner 用法](https://github.com/QwenLM/Qwen3-ASR#forcedaligner-usage)：獨立對齊 API；同頁 Quick Inference 提供整合時間戳用法。查閱日期：2026-09-10。

本 skill 提供操作流程，不代表本機已安裝模型或已完成辨識品質評測。
