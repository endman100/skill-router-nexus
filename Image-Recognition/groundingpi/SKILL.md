---
name: groundingpi
description: "使用 GroundingPI（GroundingPI/GroundingPI；Hugging Face Papers／arXiv:2609.39601；A Grounding Foundation Model towards Physical Intelligence with Visual Primitives）進行 visual grounding、open-vocabulary object detection、指代表達物件框定位、pointing、GUI 元件定位、OCR 與文件版面辨識；提供官方權重、vLLM 部署、圖片加文字推論與 GAM 座標解析流程。"
---

# GroundingPI

論文：**GroundingPI: A Grounding Foundation Model towards Physical Intelligence with Visual Primitives**。

自回歸視覺定位基礎模型，結合 MoonViT-V2／Kimi K3 視覺編碼器、可學習 projector 與 Qwen3-4B-Instruct-2507 語言骨幹，以共享詞表輸出語意標籤、點與框。訓練包含多模態與空間預訓練、SFT、GRPO。名稱中的 4B 指語言骨幹家族；論文附錄列完整多模態模型約 **4.844B** 參數。

## 何時使用

- 依圖片與文字描述、類別清單或參考框定位物件，進行密集場景標註、GUI 點定位、OCR 文字區域或文件版面辨識。
- 研究視覺定位表徵對機器人與自駕的遷移。已釋出的 checkpoint 提供 grounding；下游動作策略需要另外的環境、訓練與策略權重，官方比較工作流未提供此 checkpoint 的直接動作策略 adapter。
- GroundAnything（arXiv:2609.39600）的擴散平行解碼與獨立 GroundAnything-VLM checkpoint 屬於另一個 skill；此處使用 GroundingPI 自回歸權重及其 vLLM runtime。

## 執行：官方 vLLM 路徑

環境：**Linux x86_64、Python 3.12**，預先具備與加速器相容的 **Torch、vLLM 0.18.x** 與 kernel runtime。官方列出的已測硬體為 NVIDIA **B300、B200、H200、H800** 及 **PPU**；最低 VRAM、消費級 GPU 與 CPU 推論相容性未在所讀官方資料明確列出。

在獨立模型工作目錄執行，後續命令均從 GroundingPI repo 根目錄執行：

```bash
git clone https://github.com/groundingpi/GroundingPI.git
cd GroundingPI
python3 -m pip install -r requirements.txt huggingface_hub
hf download GroundingPI/GroundingPI --local-dir weights/vlm
python3 run.py setup serve --platform gpu
python3 run.py serve --config configs/release/vlm_vllm_gpu.yaml
```

`requirements.txt` 僅準備輕量 HTTP 客戶端、視覺化與安裝工具。`setup serve` 建立新的服務環境，繼承平台 runtime 並安裝隨 repo 提供的 **Transformers 5.7.0 fork**；它不會從零安裝加速器 runtime。官方指出 PPU 系統 Transformers 4.57.0 雖能載入 checkpoint，卻產生錯誤定位輸出，應使用提供的安裝器與模型 adapter。

若尚無 NVIDIA runtime，官方提供容器起點：在已 clone 的 repo 根目錄執行下列命令，再於容器內從安裝依賴步驟繼續。主機須具備 Docker、NVIDIA Container Toolkit 與相容驅動；這是安裝配方，並非更多硬體已通過驗證。

```bash
docker run --rm -it --gpus 'device=0' \
  --network host --shm-size 8g \
  -v "$PWD":/workspace/GroundingPI -w /workspace/GroundingPI \
  --entrypoint bash vllm/vllm-openai:v0.18.0
```

PPU 使用匹配的 vendor runtime image，將 GPU 的 setup／serve 命令改為：

```bash
python3 run.py setup serve --platform ppu
python3 run.py serve --config configs/release/vlm_vllm_ppu.yaml
```

重用已建立的環境時跳過 setup；需另建環境時，setup 與 serve 使用相同 `--venv`。下載完整權重包及 tokenizer、processor、自訂程式；切換 checkpoint 時在服務設定選用新的 `--overlay` 目錄。

## 推論與輸入輸出

服務為 `http://127.0.0.1:8000/v1`，模型 ID 為 `groundingpi`。保持服務運行，另開終端使用已安裝 `requirements.txt` 的客戶端環境，從模型 repo 根目錄執行：

```bash
curl --fail http://127.0.0.1:8000/v1/models
python3 examples/predict.py \
  --image your_image.jpg --phrase "the red car" \
  --task bbox --output outputs/car
```

換成實際圖片，每次選用新的輸出目錄。命令輸出 `result.json`，有效結果另存 `prediction.png`。模型清單只能確認服務可達，仍須檢查定位結果。

```python
from grounding_pi import GroundingPi, visualize

client = GroundingPi(base_url="http://127.0.0.1:8000/v1", model="groundingpi")
result = client.predict("your_image.jpg", "the red car", task="bbox")
print(result.to_dict())
if result.valid:
    visualize("your_image.jpg", result).save("prediction.png")
point = client.predict("your_image.jpg", "the center of the red car", task="point")
print(point.to_dict())
```

- **輸入**：單張 RGB 圖片及文字指令；客戶端接受 JPEG、PNG、WebP。`predict()` 僅封裝指代表達的框／點提示。
- **輸出**：GAM 空間 token 文字與解析結果。座標為 **0–999** 整數網格；框為 `(x1,y1,x2,y2)`、點為 `(x,y)`，缺失目標為 `None`。視覺化時才映射回原圖像素。
- `to_dict()` 包含 `task`、`predictions`、`raw_output`、`finish_reason`、`usage`、`parse_error`、`valid`。截斷或格式錯誤時 `valid=False`，先檢查原始輸出再作標註。
- 其他任務直接請求 `/v1/chat/completions`，在同一 user message 放文字與 base64 data URI 的 `image_url`。使用 checkpoint 自身的 tokenizer、processor、chat template，保留 **`skip_special_tokens=false`、`spaces_between_special_tokens=false`**；完整 HTTP 範例見官方 [vLLM 文件](https://github.com/groundingpi/GroundingPI/blob/main/docs/VLLM.md)。

| 任務 | 官方提示 |
|---|---|
| 多類別物件定位 | `Locate all the instances that match the following categories: car</c>person.` |
| OCR | `OCR task detect all the text in box format.` |
| 文件版面 | `Detect all document layout elements that match the following categories: title</c>text.` |
| GUI 點定位 | `Point to the UI element to click for the following instruction: open the settings menu.` |

## 結果與限制

論文與 44 個基線比較，評估 34 個基準、11 種感知能力；11 個能力分數的 headline 聚合平均為 **73.68%**，比較的 GPT-6 Astra 為 **71.54%**。此分數不是 34 張基準表格的直接平均，也不是單一偵測準確率。下游 RoboTwin 2.0 四種 OOD 設定皆領先所比較骨幹，最高相對提升 **24.8%**；RoboCasa-GR1 用 50% 示範勝過基線用 75%；nuScenes 平均開環 L2 誤差為 **0.296 m**。這些是論文的特定實驗結果，非下載 grounding 權重即可取得的動作能力。

- 預設服務為 **BF16、eager、TP=1、單活動序列、16,384 context tokens、0.7 加速器記憶體使用比例**；每請求一張圖，影片輸入停用，CUDA Graph 未啟用。
- 微小框、高 IoU 邊界、TotalText OCR、FSC147 visual prompting 與 GUI 定位仍有缺口；遮擋可能導致漏檢、重複或錯誤文字／座標。GUI 點座標不會執行點擊，輸出亦不提供像素遮罩。
- 自駕僅評估開環；機器人骨幹比較雖固定下游配方，預訓練規模、架構及資料仍不同，不能推論所有場景的效果。
- 重現評測使用 **GAM** 模式與官方 34-task suite；隨附 eval template 僅為 8-sample smoke test。單次完整 suite 不等同論文十次執行的統計平均，詳見 [評測指南](https://github.com/groundingpi/GroundingPI/blob/main/eval/README.md)。
- HF 模型卡列 `inference: false`。本次收錄核對官方文件，未實際下載權重或執行 GPU 推論。

## 授權

原創程式與模型貢獻採 **Apache-2.0**；組合權重的 HF 授權名稱為 **`apache-2.0-with-upstream-kimi-k3`**。Kimi 衍生素材及適用衍生作品仍受 **Kimi K3 License** 約束，包含特定商業服務條件；Apache-2.0 不替代上游授權。使用、部署與再散布前閱讀完整權重授權及上游文本，並保留 notices。論文本身採 CC BY 4.0。

## 官方來源

- [指定 Hugging Face Paper：2609.39601](https://huggingface.co/papers/2609.39601) · [arXiv 摘要](https://arxiv.org/abs/2609.39601) · [全文 v2](https://arxiv.org/html/2609.39601v2)
- [HF 權重／模型卡](https://huggingface.co/GroundingPI/GroundingPI) · [專案頁](https://groundingpi.github.io/) · [線上 Demo](https://huggingface.co/spaces/GroundingPI/GroundingPI)
- [GitHub／快速開始](https://github.com/groundingpi/GroundingPI) · [環境](https://github.com/groundingpi/GroundingPI/blob/main/environments/README.md) · [推論](https://github.com/groundingpi/GroundingPI/blob/main/docs/INFERENCE.md) · [下游整合範圍](https://github.com/groundingpi/GroundingPI#physical-intelligence)
- [模型授權範圍](https://huggingface.co/GroundingPI/GroundingPI/blob/main/LICENSE) · [Kimi K3 授權全文](https://huggingface.co/GroundingPI/GroundingPI/blob/main/LICENSE-Kimi-K3) · [程式授權](https://github.com/groundingpi/GroundingPI/blob/main/LICENSE) · [第三方 notices](https://github.com/groundingpi/GroundingPI/blob/main/THIRD_PARTY_NOTICES.md)
