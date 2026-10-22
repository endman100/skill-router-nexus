# 06. LoRA 訓練（Grok Bot 直接訓練）

路徑依 [00_workspace.md](00_workspace.md)：`<WS>` 為本案 workspace，`<ENV>` 為共用環境。

由 Grok Bot 直接執行訓練。訓練集為 `<WS>/05_caption/train_set`（`0001.png…` + 同名 txt + `manifest.json`）。

## 環境設定（首次才需要）

sd-scripts 固定在下列 commit：

| repo | commit | 用途 |
|---|---|---|
| https://github.com/endman100/sd-scripts | `08d86febb0f9f2fba06517a1983647d02b1337bc` | `anima_train_network.py`、`networks/lori_D_anima.py`、`library/anima_utils.py`（從 checkpoint 自動判斷 DiT block 數） |

```bash
git clone https://github.com/endman100/sd-scripts "<ENV>/sd-scripts"
git -C "<ENV>/sd-scripts" checkout 08d86febb0f9f2fba06517a1983647d02b1337bc
```

venv（Python 3.12；torch 先單獨安裝 cu130 版本，再安裝 sd-scripts 的 requirements，最後固定為已驗證版本）：

```bash
python3.12 -m venv "<ENV>/.venv"     # Windows: py -3.12 -m venv "<ENV>\.venv"
. "<ENV>/.venv/bin/activate"          # Windows: "<ENV>\.venv\Scripts\activate"
pip install torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu130
cd "<ENV>/sd-scripts"
pip install -r requirements.txt     # 含 -e .，要在 sd-scripts 裡執行
pip install accelerate==1.12.0 transformers==5.2.0 diffusers==0.36.0 bitsandbytes==0.49.2 safetensors==0.7.0
# 完成後回到本技能資料夾
```

已驗證可用版本：torch 2.10.0+cu130、accelerate 1.12.0、transformers 5.2.0、diffusers 0.36.0、bitsandbytes 0.49.2、safetensors 0.7.0。`train_lora.py` 本身僅使用 Python 標準函式庫。

模型檔案放置於 `<ENV>/models/`：Anima base（nova：`novaAnimeAM_v6029B.safetensors`，40 block，sd-scripts 會自動判斷）、text encoder `qwen_3_06b_base.safetensors`、VAE `qwen_image_vae_train.safetensors`。

## 訓練

```bash
python scripts/train_lora.py \
  --train-dir "<WS>/05_caption/train_set" --trigger <trigger> --work-dir "<WS>/06_train" \
  --sd-scripts "<ENV>/sd-scripts" --venv "<ENV>/.venv" \
  --model "<ENV>/models/novaAnimeAM_v6029B.safetensors" \
  --qwen3 "<ENV>/models/qwen_3_06b_base.safetensors" \
  --vae "<ENV>/models/qwen_image_vae_train.safetensors"
```

- `--prepare-only`：僅寫入 `<WS>/06_train/kwargs_train.json` 與 `<WS>/06_train/config.toml`，先檢查圖片數量、num_repeats、caption 是否齊全。
- `--venv` 可改為 `--python <訓練環境的 python>`。Linux / Windows 使用相同指令。
- 直接以 `accelerate launch --mixed_precision bf16 --num_cpu_threads_per_process 1 <ENV>/sd-scripts/anima_train_network.py` 啟動，工作目錄為 sd-scripts。路徑可包含空格，命令列上的路徑請用引號包覆。
- 輸出皆位於 `<WS>/06_train/models/`：`<trigger>-0000NN.safetensors`（每 5 個 epoch）、`<trigger>.safetensors`（最終模型）、`*-state/`（續訓用）、`train.log`（完整 log）。
- 中斷後使用同一個指令重新執行，會從 `<WS>/06_train/models/` 中該 trigger 的最新 `*-state` 續訓：epoch 優先讀取 `train_state.json` 的 `current_epoch`，若無有效值才採用資料夾名稱中的數字。若已達 `--epochs` 則直接結束，不啟動訓練。
- 失敗後最多重試 `--max-retries` 次（預設為 3，即包含首次執行最多 4 次；設為 0 則不重試），每次會先重新尋找最新 state；重試次數耗盡後以非零狀態結束。啟動器與訓練輸出皆同步寫入 console 與 `<WS>/06_train/models/train.log`。

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
| `--reg-dir` | 無 | 預設不使用正則化圖；指定 `<WS>/06_train/regularization/` 才使用，train:reg 取 1:1；需要截取時寫到 `<WS>/06_train/images_regularization_1to1/` |
| `--max-retries` | 3 | 首次失敗後最多重試次數 |

固定設定：`class_tokens` 與輸出名稱 = trigger；num_repeats = ceil(480 / 圖數)；bf16、`--network_train_unet_only`、`--gradient_checkpointing`、`--cache_latents_to_disk`、sdpa、`timestep_sampling sigmoid`、`discrete_flow_shift 1.0`、`--save_state`。

## 注意事項

- 啟動後觀察 `<WS>/06_train/models/train.log` 的每步速度：**若訓練明顯變慢或記憶體不足，請中止訓練，調降 `--batch` 或 `--max-bucket` 後重新執行**（同一個 `<WS>/06_train/` 會自動續訓）。
- checkpoint 對照測試與固定 prompt 檔案：請依照 [07_lora_validation.md](07_lora_validation.md) 執行。
- 訓練結果保留於 `<WS>/06_train/models/`；對照圖由步驟 07 產生，由使用者從圖中挑選 checkpoint。
