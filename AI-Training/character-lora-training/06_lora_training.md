# 06. LoRA 訓練（Grok Bot 直接訓練）

Grok Bot 直接訓練。訓練集是 `<訓練集輸出資料夾>`（`0001.png…` + 同名 txt + `manifest.json`）。

## 環境（第一次才需要）

sd-scripts 固定在下列 commit：

| repo | commit | 用途 |
|---|---|---|
| https://github.com/endman100/sd-scripts | `08d86febb0f9f2fba06517a1983647d02b1337bc` | `anima_train_network.py`、`networks/lori_D_anima.py`、`library/anima_utils.py`（從 checkpoint 自動判斷 DiT block 數） |

```bash
mkdir repos && cd repos
git clone https://github.com/endman100/sd-scripts
git -C sd-scripts checkout 08d86febb0f9f2fba06517a1983647d02b1337bc
```

venv（Python 3.12；torch 先單獨裝 cu130 版，再裝 sd-scripts 的 requirements，最後固定成已驗證版本）：

```bash
python3.12 -m venv .venv            # Windows: py -3.12 -m venv .venv
. .venv/bin/activate                # Windows: .venv\Scripts\activate
pip install torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu130
cd sd-scripts
pip install -r requirements.txt     # 含 -e .，要在 sd-scripts 裡執行
cd ..
pip install accelerate==1.12.0 transformers==5.2.0 diffusers==0.36.0 bitsandbytes==0.49.2 safetensors==0.7.0
cd ..                              # 回到 repos 的上一層
```

已驗證可用：torch 2.10.0+cu130、accelerate 1.12.0、transformers 5.2.0、diffusers 0.36.0、bitsandbytes 0.49.2、safetensors 0.7.0。`train_lora.py` 本身只用 Python 標準函式庫。

模型檔：Anima base（nova：`novaAnimeAM_v6029B.safetensors`，40 block，sd-scripts 會自動判斷）、text encoder `qwen_3_06b_base.safetensors`、VAE `qwen_image_vae_train.safetensors`。

## 訓練

```bash
python scripts/train_lora.py \
  --train-dir "<訓練集輸出資料夾>" --trigger <trigger> --work-dir "<run 資料夾>/lora_work" \
  --sd-scripts repos/sd-scripts --venv repos/.venv \
  --model "<nova checkpoint>" --qwen3 "<qwen_3_06b_base.safetensors>" --vae "<qwen_image_vae_train.safetensors>"
```

- `--prepare-only`：只寫 `kwargs_train.json` 與 `config.toml`，先檢查圖數、num_repeats、caption 是否齊全。
- `--venv` 可改成 `--python <訓練環境的 python>`。Linux / Windows 同一個指令。
- 直接以 `accelerate launch --mixed_precision bf16 --num_cpu_threads_per_process 1 <sd-scripts>/anima_train_network.py` 啟動，工作目錄為 sd-scripts。路徑可含空白，命令列上的路徑用引號包住。
- 輸出：`<work-dir>/models/<trigger>-0000NN.safetensors`（每 5 epoch）、`<trigger>.safetensors`（最後）、`*-state`（續訓用）、`train.log`（完整 log）。
- 中斷後用同一個指令重跑，從 `models/` 中該 trigger 的最新 `*-state` 續訓：epoch 優先讀 `train_state.json` 的 `current_epoch`，沒有有效值才用資料夾名稱中的數字。已達 `--epochs` 就直接結束，不啟動訓練。
- 失敗後最多重試 `--max-retries` 次（預設 3，即含首次最多 4 次；設 0 不重試），每次先重新尋找最新 state；重試用盡以非零狀態結束。啟動器與訓練輸出都同步寫入 console 和 `models/train.log`。

## 參數（預設值）

| 參數 | 預設 | 說明 |
|---|---|---|
| `--batch` | 10 | batch size |
| `--resolution` | 1024 | |
| `--min-bucket` / `--max-bucket` | 512 / 1280 | aspect bucket 範圍 |
| `--epochs` / `--save-every` | 20 / 5 | |
| `--lr` | 5e-5 | constant，AdamW8bit |
| `--dim` | 32 | `networks.lori_D_anima` |
| `--keep-tokens` / `--tag-dropout` | 2 / 0.2 | 搭配 `--shuffle_caption` |
| `--reg-dir` | 無 | 預設不用正則化圖；給了才用，train:reg 取 1:1 |
| `--max-retries` | 3 | 首次失敗後最多重試次數 |

固定設定：`class_tokens` 與輸出名 = trigger；num_repeats = ceil(480 / 圖數)；bf16、`--network_train_unet_only`、`--gradient_checkpointing`、`--cache_latents_to_disk`、sdpa、`timestep_sampling sigmoid`、`discrete_flow_shift 1.0`、`--save_state`。

## 注意

- 開跑後看 `train.log` 的每步速度：**訓練明顯變慢或記憶體溢出，就停掉，降 `--batch` 或 `--max-bucket` 後重跑**（同一個 work-dir 會續訓）。
- checkpoint 對照測試與固定 prompt 檔案：照 [07_lora_validation.md](07_lora_validation.md) 執行。
- 訓練結果保留在原輸出資料夾；對照圖由步驟 07 產生，使用者從圖中挑 checkpoint。
