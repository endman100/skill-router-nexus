# 06. LoRA 訓練（Grok Bot 直接訓練）

Grok Bot 直接訓練。訓練集是 `<訓練集輸出資料夾>`（`0001.png…` + 同名 txt + `manifest.json`）。

## 環境（第一次才需要）

兩個 repo 固定在下列 commit：

| repo | commit | 用途 |
|---|---|---|
| https://github.com/endman100/sd-scripts | `08d86febb0f9f2fba06517a1983647d02b1337bc` | `anima_train_network.py`、`networks/lori_D_anima.py`、`library/anima_utils.py`（從 checkpoint 自動判斷 DiT block 數） |
| https://github.com/endman100/sd-scripts-wrap | `0fb250e184bbab2a8d704d7af3309c8113e43589` | `train_with_resume.py`：組 accelerate 指令、寫 config.toml、從最新 state 自動續訓 |

sd-scripts **必須 clone 在 sd-scripts-wrap 裡面、資料夾名 `sd-scripts`**（wrap 固定用 `<wrap>/sd-scripts/anima_train_network.py`；不是 submodule，wrap 的 `.gitignore` 已忽略它）：

```bash
mkdir repos && cd repos
git clone https://github.com/endman100/sd-scripts-wrap
git -C sd-scripts-wrap checkout 0fb250e184bbab2a8d704d7af3309c8113e43589
git clone https://github.com/endman100/sd-scripts sd-scripts-wrap/sd-scripts
git -C sd-scripts-wrap/sd-scripts checkout 08d86febb0f9f2fba06517a1983647d02b1337bc
```

venv（Python 3.12；torch 先單獨裝 cu130 版，再裝 sd-scripts 的 requirements，最後固定成已驗證版本）：

```bash
python3.12 -m venv .venv            # Windows: py -3.12 -m venv .venv
. .venv/bin/activate                # Windows: .venv\Scripts\activate
pip install torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu130
cd sd-scripts-wrap/sd-scripts && pip install -r requirements.txt && cd ../..   # requirements 含 -e .，要在 sd-scripts 裡執行
pip install accelerate==1.12.0 transformers==5.2.0 diffusers==0.36.0 bitsandbytes==0.49.2 safetensors==0.7.0
```

已驗證可用：torch 2.10.0+cu130、accelerate 1.12.0、transformers 5.2.0、diffusers 0.36.0、bitsandbytes 0.49.2、safetensors 0.7.0。wrap 本身只多用到 `toml`（sd-scripts requirements 已含）。路徑不要有空白（wrap 組指令時 sd-scripts 路徑沒加引號）。

模型檔：Anima base（nova：`novaAnimeAM_v6029B.safetensors`，40 block，sd-scripts 會自動判斷）、text encoder `qwen_3_06b_base.safetensors`、VAE `qwen_image_vae_train.safetensors`。

## 訓練

```bash
python scripts/train_lora.py \
  --train-dir <訓練集輸出資料夾> --trigger <trigger> --work-dir <run 資料夾>/lora_work \
  --sd-scripts-wrap repos/sd-scripts-wrap --venv repos/.venv \
  --model <nova checkpoint> --qwen3 <qwen_3_06b_base.safetensors> --vae <qwen_image_vae_train.safetensors>
```

- `--prepare-only`：只寫 `kwargs_train.json` 與 `config.toml`，先檢查圖數、num_repeats、caption 是否齊全。
- `--venv` 可改成 `--python <訓練環境的 python>`。Linux / Windows 同一個指令。
- 輸出：`<work-dir>/models/<trigger>-0000NN.safetensors`（每 5 epoch）、`<trigger>.safetensors`（最後）、`*-state`（續訓用）、`train.log`（完整 log）。
- 中斷後用同一個指令重跑，會從最新的 state 續訓；已到 20 epoch 就直接結束。
- 指令失敗時 wrap 會每 60 秒自動重試；要停止就結束整個行程（含 accelerate 子行程）。

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

固定（wrap 決定）：`class_tokens` 與輸出名 = trigger；num_repeats = ceil(480 / 圖數)；bf16、`--network_train_unet_only`、`--gradient_checkpointing`、`--cache_latents_to_disk`、sdpa、`timestep_sampling sigmoid`、`discrete_flow_shift 1.0`、`--save_state`。

## 注意

- 開跑後看 `train.log` 的每步速度：**訓練明顯變慢或記憶體溢出，就停掉，降 `--batch` 或 `--max-bucket` 後重跑**（同一個 work-dir 會續訓）。
- checkpoint 對照測試 prompt：`anime style, <trigger>, ` + `main_outfit.json` 的主要服裝 tag + 詞表的角色特徵 tag。
- 結果（各 epoch LoRA、對照圖、`train.log`、`kwargs_train.json`、`config.toml`）放到 `<run 資料夾>/train_results/`，由使用者挑 checkpoint。
