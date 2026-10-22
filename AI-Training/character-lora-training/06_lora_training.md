# 06. LoRA 訓練（Grok Bot 直接訓練）

Grok Bot 直接訓練。訓練集是 `<訓練集輸出資料夾>`（`0001.png…` + 同名 txt + `manifest.json`）。

## 參數（sd-scripts `anima_train_network.py`）

- Base model：nova（`novaAnimeAM_v6029B.safetensors`），text encoder `qwen_3_06b_base.safetensors`，VAE Qwen-Image VAE（`qwen_image_vae_train.safetensors`）。
- `networks.lori_D_anima`，dim 32；lr 5e-5 constant，AdamW8bit；bf16，`--network_train_unet_only`，`--gradient_checkpointing`，`--cache_latents --cache_latents_to_disk`，sdpa。
- `timestep_sampling sigmoid`，`discrete_flow_shift 1.0`。
- 資料集：resolution 1024，bucket 512–1280，batch 12，num_repeats = ceil(480 / 圖數)，`class_tokens` = trigger，caption 副檔名 txt。
- 20 epochs，每 5 epoch 存一次，`--save_state`（可續訓）。
- caption：`--shuffle_caption --keep_tokens=2 --caption_tag_dropout_rate=0.2`。
- 輸出名 = trigger。

## 注意

- 開跑後確認速度：明顯變慢就停掉，降 batch 或最大 bucket 後重跑。
- checkpoint 對照測試 prompt：`anime style, <trigger>, ` + `main_outfit.json` 的主要服裝 tag + 詞表的角色特徵 tag。
- 結果（各 epoch LoRA、對照圖、log）放到 `<run 資料夾>/train_results/`，由 使用者 挑 checkpoint。
