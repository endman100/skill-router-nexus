---
name: groundanything
description: "使用 GroundAnything、GroundAnything-VLM（GroundingPI/GroundAnything；arXiv:2609.39600；groundingpi.github.io/groundanything）進行 visual grounding、open-vocabulary object detection、指代表達物件框定位、pointing、GUI 元件定位、OCR 文字區域與文件版面辨識；提供官方 Hugging Face 權重、定制 SGLang 部署及圖片加文字推論流程。"
---

# GroundAnything

論文：**GroundAnything: Reconciling Parallel Decoding with Precise Visual Grounding at Flash Speed**。

GroundingPI 的 4B 視覺定位基礎模型，以分塊雙向擴散平行預測空間 token。結合 MoonViT-V2 / Kimi K3 視覺編碼器與 Qwen3-4B 語言架構，經 grounding 預訓練、AR-to-diffusion 聯合目標轉換、SFT 及 GRPO 後訓練。GroundAnything-VLM 是獨立的自回歸 checkpoint。

## 何時使用

- 從圖片依文字描述、類別或參考框找物件，輸出框或點；適合密集場景標註、GUI 點定位、文字區域及文件版面定位。
- 需要權衡視覺定位品質與平行解碼延遲時，比較 DLM 熵引導、自推測與 VLM 自回歸模式。
- 輸出以標籤和座標為主；像素遮罩需求應另選分割模型，GUI 點座標本身不會執行點擊。

## 執行：官方 SGLang 路徑

環境為 Linux x86_64、Python 3.12。官方列出的已測硬體為 NVIDIA B300、B200、H200、H800 及 PPU；以下安裝器是 CUDA/GPU 配方，PPU 須使用對應平台 runtime。最低 VRAM 與消費級 GPU 相容性未由所讀官方資料明確列出。

在獨立模型工作目錄執行，後續命令均從 GroundAnything repo 根目錄執行：

```bash
git clone https://github.com/groundingpi/GroundAnything.git
cd GroundAnything
python3 -m pip install -r requirements.txt huggingface_hub
hf download GroundingPI/GroundAnything --local-dir weights/dlm_bundle
python3 run.py setup serve
python3 run.py serve --decoder denoise
```

`requirements.txt` 僅準備輕量 HTTP 客戶端等依賴；`setup serve` 才建立 `.venv-serve` 並安裝隨 repo 提供的定制引擎。服務配方固定 Torch 2.9.1、Transformers 5.5.4 等版本，勿以單獨安裝上游 SGLang 取代。完整 HF DLM 包已含 tokenizer 和定制程式，無須 `prepare-model`；該步驟供其他原始 checkpoint 組裝使用。

服務為 `http://127.0.0.1:8101/v1`，模型 ID `groundinganything`。熵引導預設 block size 32、sub-block 4、threshold 0.8。切換自推測模式前先停止現有 DLM 服務，再重用相同權重：

```bash
python3 run.py serve --decoder speculative
```

若選擇獨立的 VLM 自回歸權重，在完成上述服務環境安裝後執行：

```bash
hf download GroundingPI/GroundAnything-VLM --local-dir weights/vlm
python3 run.py serve --config configs/release/vlm_sglang.yaml
```

VLM endpoint 為 `http://127.0.0.1:8102/v1`、模型 ID `groundinganything-vlm`。官方另有 VLM 專用 vLLM adapter，但端到端加速器驗證仍待完成；DLM 使用定制 SGLang。

## 推論與輸入輸出

保持服務運行，在另一終端使用已安裝 `requirements.txt` 的客戶端環境，從模型 repo 根目錄執行：

```bash
python3 examples/predict.py \
  --image your_image.jpg --phrase "the red car" \
  --task bbox --output outputs/car
```

將 `your_image.jpg` 換成實際圖片；每次選用新的輸出目錄。命令輸出 `result.json`，有效結果另存 `prediction.png`。VLM 加上 `--base-url http://127.0.0.1:8102/v1 --model groundinganything-vlm`。

Python 客戶端範例：

```python
from grounding_anything import GroundingAnything

client = GroundingAnything(
    base_url="http://127.0.0.1:8101/v1", model="groundinganything"
)
result = client.predict("your_image.jpg", "the red car", task="bbox")
print(result.to_dict())
point = client.predict("your_image.jpg", "the center of the red car", task="point")
print(point.to_dict())
```

- **輸入**：單張 RGB 圖片與文字指令；客戶端接受 JPEG、PNG、WebP。`predict()` 封裝指代表達框／點提示。
- **輸出**：GAM 空間 token 文字與解析結果；座標為 0–999 整數網格，框 `(x1,y1,x2,y2)`、點 `(x,y)`；缺失目標以 `None` 表示。視覺化函式才映射回原圖像素。
- `to_dict()` 含 `task`、`predictions`、`raw_output`、`finish_reason`、`usage`、`parse_error`、`valid`。截斷或格式錯誤時 `valid=False`，先檢查原始輸出再用作標註。
- 其他任務直接呼叫 `/v1/chat/completions`，使用 checkpoint 的 processor、tokenizer 與 chat template；同一 user message 放文字與 base64 data URI 的 `image_url`。保留 `skip_special_tokens=false`、`spaces_between_special_tokens=false`。

官方任務提示（其他任務不要經過僅封裝指代表達的 `predict()`）：

| 任務 | 提示 |
|---|---|
| 多類別物件定位 | `Locate all the instances that match the following categories: car</c>person.` |
| OCR | `OCR task detect all the text in box format.` |
| 文件版面 | `Detect all document layout elements that match the following categories: title</c>text.` |
| GUI 點定位 | `Point to the UI element to click for the following instruction: open the settings menu.` |

## 結果與限制

論文報告 30 個 grounding 基準平均：GroundAnything-VLM **72.42%**；GroundAnything 熵引導 **61.75%**，比較的 LocateAnything 為 **53.32%**。這是跨基準聚合分數，並非單一偵測準確率。可選自推測在特定 COCO 設定達 AR **4.51×** 吞吐量、F1mIoU 下降 **0.74 個百分點**；不可泛化為所有硬體或請求的加速保證。

- 預設服務為 BF16、Triton attention、eager、單 GPU、單活動請求及兩個排隊請求；客戶端並發不代表模型批次推論。CUDA Graph 與 FP8 是另行研究的設定，以上命令不會啟用。
- 小物件、遮擋、密集場景可能漏檢、重複或產生錯誤文字／座標。
- 自推測的因果驗證對應轉換模型自身的 causal branch，不保證與獨立 GroundAnything-VLM 輸出一致。
- 一般客戶端請求不會自動套用 benchmark 任務策略；重現論文使用官方 eval 入口與 **GAM** 模式，參閱評測文件。
- HF 模型卡列 `inference: false`；DLM runtime 不支援 ZeroGPU。此 skill 記錄官方執行方法，未在本次收錄時實際載入權重或跑 GPU 推論。

## 授權

原創程式／模型貢獻採 Apache-2.0；組合權重的 HF 授權名稱為 `apache-2.0-with-upstream-kimi-k3`。Kimi 衍生素材及適用衍生作品仍受 **Kimi K3 License** 約束；Apache-2.0 不替代上游授權。使用及再散布時閱讀權重 LICENSE 和各完整授權文本並保留 notices。

## 官方來源

- [專案頁](https://groundingpi.github.io/groundanything/)
- [論文摘要 arXiv:2609.39600](https://arxiv.org/abs/2609.39600) · [全文](https://arxiv.org/html/2609.39600v2)
- [HF DLM 權重／模型卡](https://huggingface.co/GroundingPI/GroundAnything) · [HF VLM 權重／模型卡](https://huggingface.co/GroundingPI/GroundAnything-VLM)
- [GitHub／快速開始](https://github.com/groundingpi/GroundAnything) · [環境](https://github.com/groundingpi/GroundAnything/blob/main/environments/README.md) · [推論](https://github.com/groundingpi/GroundAnything/blob/main/docs/INFERENCE.md) · [評測](https://github.com/groundingpi/GroundAnything/blob/main/eval/README.md)
- [模型授權範圍](https://huggingface.co/GroundingPI/GroundAnything/blob/main/LICENSE) · [Kimi K3 授權全文](https://huggingface.co/GroundingPI/GroundAnything/blob/main/LICENSE-Kimi-K3) · [程式授權](https://github.com/groundingpi/GroundAnything/blob/main/LICENSE)
