---
name: mimo-agentic-rl
description: 使用 MiMo-V2.6（arXiv 2610.11959）進行多模態 agentic reinforcement learning、混合任務 GRPO、groupwise agentic grading、MOPD2 蒸餾與工具使用；包含 MiMo-V2.6-Distill-Qwen-9B 推論、官方 verl 訓練入口及 Pro／Flash 權重選擇。適用於重現 MiMo 的 agent 強化學習方法或部署其模型。
---

# MiMo-V2.6：擴展 Agent 強化學習

[MiMo-V2.6: Scaling Reinforcement Learning Towards Self-Improvement](https://arxiv.org/abs/2610.11959) 是小米的多模態模型與後訓練方法。Pro 為 1.02T 總參數／42B 啟用，Flash 約 310B／15B；hybrid sliding-window／global attention MoE 支援最長 1M tokens，接收文字、圖片、影片與音訊，生成文字與工具呼叫。

核心是在一次非同步 GRPO 訓練混合程式、通用、視覺與資安任務及多種 agent harness，同時擴大 batch、環境多樣性與評分算力。GRS 從離線 rollout 比較合成 rubric；GAR 在線比較同組解答，把正 advantage 分配給較好的成功解答。另以長度／行為懲罰、凍結 MoE router、reward-hacking 防護與訓練／推論一致性維持穩定；MOPD2 再整合多教師的自主 rollout、teacher-prefix 與 SFT-prefix 蒸餾。[論文 §4–6](https://arxiv.org/html/2610.11959v1#S4)

## 何時使用與權重選擇

- 研究或重現 MiMo 的混合任務 RL、群組式評分、多 harness 泛化，或以小模型繼續 agent RL。
- 小規模入口：[MiMo-V2.6-Distill-Qwen-9B](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B) 是以 MiMo 軌跡微調 Qwen3.5-9B 的 **SFT checkpoint**，供後續 GRPO 使用；不能直接宣稱具有論文中進一步 RL 後的成績。
- 重現原始大型 RL 結果：選 [Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL)／[Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL)。新 agent 部署依目前官方 recipe 優先選 [Pro-MOPD](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-MOPD)／[Flash-MOPD](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-MOPD)，改善原始 RL 版反覆呼叫工具卻不前進的問題。

## 先跑 9B 文字推論

依 [9B model card 的 Quickstart](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B#quickstart)，需支援 Qwen3.5 與 `mimo` reasoning parser 的近期 SGLang。以下以官方 SGLang 映像包住 model card 的啟動命令；需 NVIDIA GPU、相容驅動與 NVIDIA Container Toolkit：

```bash
docker pull lmsysorg/sglang:latest
docker run --gpus all --ipc=host --shm-size 32g \
  -p 127.0.0.1:30000:30000 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  lmsysorg/sglang:latest \
  sglang serve \
    --model-path XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B \
    --reasoning-parser mimo --host 0.0.0.0 --port 30000
```

首次啟動從 HF 下載權重與 tokenizer；離線使用可將 `--model-path` 換成已掛載的完整 HF checkpoint 目錄。另開終端呼叫 `/v1/chat/completions`，以下把官方 Python client 範例等價改為 curl，明確開啟 thinking：

```bash
curl http://localhost:30000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B","messages":[{"role":"user","content":"What is 15% of 240?"}],"max_tokens":2048,"chat_template_kwargs":{"enable_thinking":true}}'
```

讀取 `choices[0].message.content` 與可選 `reasoning_content`。9B 的官方 quickstart 只示範文字；圖片能力依 Qwen3.5 processor／服務端支援確認，勿把 Pro／Flash 的音訊、影片與 1M context 規格直接套用到 9B。

## 官方 9B GRPO 訓練入口

使用 [XiaomiMiMo/verl 的 `mimo-oss` 分支](https://github.com/XiaomiMiMo/verl/tree/mimo-oss)，不是上游 verl 的通用範例。先依其 [安裝指南](https://verl.readthedocs.io/en/latest/start/install.html)備妥 CUDA／PyTorch、Megatron 訓練與 SGLang rollout 環境，再安裝 fork 及指定 submodule 的依賴：

```bash
git clone --branch mimo-oss https://github.com/XiaomiMiMo/verl.git
cd verl
git submodule update --init third_party/mimoagent-osr third_party/uni_agent
pip install -e .
```

`pip install -e .` 不等於完成 GPU backend／submodule 安裝；以該 checkout 的 `setup.py`、各 submodule 安裝說明及集群環境為準。mimoagent 要求 Python 3.12，支援 `pip install -e .` 或 `uv sync`。不要把推論用 `sglang:latest` 視為訓練依賴鎖定；fork 的 `sglang` extra 目前指定 SGLang 0.5.8、torch 2.9.1。

程式任務範例，依 [`scripts/code/env.example`](https://github.com/XiaomiMiMo/verl/blob/mimo-oss/scripts/code/env.example)填入真實路徑；訓練與驗證資料應分開準備：

```bash
export MODEL_PATH=/path/to/MiMo-V2.6-Distill-Qwen-9B
export TRAIN_DATA=/path/to/code.parquet
export VAL_DATA=/path/to/code-val.parquet
export KUBECONFIG=/path/to/kubeconfig
bash scripts/code/train.sh
```

資料取自 [MiMo-V2.6-RL-oss](https://huggingface.co/datasets/XiaomiMiMo/MiMo-V2.6-RL-oss) 的 `code` subset，需保留 `extra_info.dataset_type=opensource-code` 等環境欄位。此入口使用四個 white-box harness、已啟動的 Ray cluster 與 Kubernetes task pods；所有 worker 必須能存取模型、資料與 kubeconfig。預設為 **8 nodes × 8 GPUs**、group size 16、262144-token 上限，並非單 GPU 範例；用 `env.example` 調整 topology 與配額，保留提供設定的 `anti_hack_cleanup: true`。

其他官方入口：通用 `scripts/general/general.sh`、視覺 `scripts/design/webdev.sh`、音樂 `scripts/design/music.sh`、資安 `scripts/arvo/arvo.sh`。各自先填相鄰 `*.env.example`；通用與視覺還需可用的 grader endpoint／環境資產。這些是 §7 的開放環境實驗，不代表完整重現 Pro／Flash 的萬億參數混合 RL。[訓練 README](https://github.com/XiaomiMiMo/verl/blob/mimo-oss/README.md)

## 大型模型部署與硬體

目前 [vLLM Flash recipe](https://recipes.vllm.ai/XiaomiMiMo/MiMo-V2.6-Flash-RL)／[Pro recipe](https://recipes.vllm.ai/XiaomiMiMo/MiMo-V2.6-Pro-RL)要求 **vLLM ≥0.31.0**，才能載入 MXFP4 儲存格式；HF card 仍連到 V2.5 recipe，部署時優先核對 V2.6 專屬說明。

```bash
docker pull vllm/vllm-openai:v0.31.0
docker run --gpus all --ipc=host \
  -p 127.0.0.1:8000:8000 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  vllm/vllm-openai:v0.31.0 \
  --model XiaomiMiMo/MiMo-V2.6-Flash-MOPD \
  --trust-remote-code --tensor-parallel-size 8 \
  --max-model-len auto --gpu-memory-utilization 0.95 \
  --reasoning-parser mimo --tool-call-parser mimo \
  --enable-auto-tool-choice --generation-config vllm
```

這是 recipe 預設的 8×H200 Flash 設定；Pro 改用 `XiaomiMiMo/MiMo-V2.6-Pro-MOPD` 並重新核對容量。官方列 Flash 約 173 GB 權重、參考最低聚合 VRAM ≥208 GB（4×H200 TP4 等），Pro 約 566 GB、≥680 GB（8×H200 TP8 等）；這些不是所有 context／batch 的記憶體保證。啟用參數量不等於權重容量。API 同上，改 port 8000 與 model id；Pro／Flash card 建議 `temperature=1.0`、`top_p=0.95`。

## 輸入、輸出與限制

| 工作 | 輸入 | 輸出 |
|---|---|---|
| 推論 | messages、可選 tools；Pro／Flash 另支援影像／影片／音訊理解，格式依 backend | 文字、可選 reasoning 與 tool calls；工具執行需外部 harness |
| 開放環境 GRPO | 9B SFT 權重、任務 parquet、環境映像／資產、verifier／grader、cluster 設定 | 更新後 checkpoint、rollout 軌跡、reward 與訓練指標；程式入口預設寫入 `outputs/<EXP_NAME>/<RUN_ID>/` |

- [大型模型 card 的評測表](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL#3-evaluation-results)：Pro／Flash 在 DeepSWE v1.1 為 **71.9／67.9**、AutomationBench v1.0.6 為 **53.1／52.3**；需依官方 harness 與採樣條件比較。
- [論文 §7 Table 6](https://arxiv.org/html/2610.11959v1)：9B SFT → 各領域 GRPO 後，SWE-bench Pro **44.6 → 47.6**（avg@3），Terminal Bench 2.1 **37.1 → 52.8**（avg@1）。這些分領域 RL 模型與發布的 SFT 權重不同，內部 mini benchmarks 也不能當作公開測試集結果。
- **未知／未驗證**：9B 最低推論 VRAM、各訓練設定最低 GPU 型號／顯存，以及 §7 所有 RL 後 checkpoint 的公開下載位置，以上來源未明列。1M 是大型模型架構上限，不保證當前硬體／backend 可跑滿。本 skill 已核對文件與訓練設定，未下載模型或執行 GPU 推論／RL。

## 授權與來源

Pro／Flash（RL、MOPD）與 9B model cards 標示 **MIT**；訓練 fork 為 **Apache-2.0**，mimoagent 為 **MIT** 並附 NOTICE，RL-oss dataset 標示 **Apache-2.0**。模型卡另有 Use Restrictions 提醒，並說明不修改模型授權；各環境、子模組與第三方資料仍按自身授權使用。

- [HF 論文頁](https://huggingface.co/papers/2610.11959)／[arXiv 摘要](https://arxiv.org/abs/2610.11959)／[全文](https://arxiv.org/html/2610.11959v1)／[PDF](https://arxiv.org/pdf/2610.11959)
- [官方 HF collection](https://huggingface.co/collections/XiaomiMiMo/mimo-v26)／[官方介紹](https://mimo.xiaomi.com/mimo-v2-6)
- [訓練 GitHub](https://github.com/XiaomiMiMo/verl/tree/mimo-oss)／[agent harness](https://github.com/XiaomiMiMo/mimoagent/tree/mimo-oss)／[uni-agent](https://github.com/XiaomiMiMo/uni-agent)
- [SGLang cookbook（模型卡連結的 V2.5 參考）](https://docs.sglang.io/cookbook/autoregressive/Xiaomi/MiMo-V2.5)

分類決策：`KEEP_FLAT`，放在 `AI-Training`；本 skill 主題是 MiMo 的 agent 後訓練方法與開放實驗，未與通用 verl／GRPO skill 重複。
