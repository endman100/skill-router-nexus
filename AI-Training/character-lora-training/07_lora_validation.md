# 07. LoRA 驗證

路徑依 [00_workspace.md](00_workspace.md)：`<WS>` 為本案 workspace，`<ENV>` 為共用環境。

## 啟動 ComfyUI

先從本技能資料夾複製設定：

```bash
cp templates/extra_model_paths.example.yaml <WS>/07_validate/extra_model_paths.yaml
cp templates/animaEndToEnd_fast.json <WS>/07_validate/workflow.json
```

將 `<WS>/07_validate/extra_model_paths.yaml` 的 `base_path` 改為 `<WS>/06_train` 的絕對路徑，`loras` 保持為 `models`，即指向 `<WS>/06_train/models/`。ComfyUI 的 `models/diffusion_models/`、`text_encoders/`、`vae/` 需能讀取到 `<ENV>/models/` 的 Anima、`qwen_3_06b_base.safetensors`、`qwen_image_vae.safetensors`（workflow 預設檔名）。從 `<ENV>/ComfyUI/` 啟動，port 固定為 1121：

```bash
python main.py --port 1121 --extra-model-paths-config "<WS>/07_validate/extra_model_paths.yaml"
```

## 固定條件對照

使用者提供 UTF-8 編碼的固定正向 prompt，存為 `<WS>/07_validate/positive.txt`；結構為「風格詞 + trigger + 外觀／服裝描述 + 全身站姿」。所有 checkpoint 與 base 共用同一份檔案及 seeds。可另提供 `<WS>/07_validate/negative.txt`，未提供時為空。

需安裝 Pillow；以下請從本技能資料夾執行，路徑包含空格時請保留引號：

```bash
python scripts/eval_lora.py \
  --run-dir "<WS>/06_train" --prompt-file "<WS>/07_validate/positive.txt" \
  --workflow "<WS>/07_validate/workflow.json" \
  --comfy-url http://127.0.0.1:1121
```

- 預設比較 base、各 epoch 與 final，seeds 為 `31415926,42,1234567,20261022`，LoRA strength 為 0.8；使用 `--no-base` 可略過 base。
- 預設模型為 `novaAnimeAM_v6029B.safetensors`，參數為 720×1280、40 steps、CFG 4、`er_sde`／`simple`。可用 `--unet`、`--width`、`--height`、`--steps`、`--cfg`、`--sampler`、`--scheduler` 調整。
- `--negative-file "<WS>/07_validate/negative.txt"`、`--seeds "<逗號分隔整數>"`、`--strength`、`--workflow` 可覆寫預設值；`--timeout` 為每張圖片的秒數（預設 600）。
- 加入 `--dry-run` 僅列出 labels、LoRA 檔、seeds 與輸出路徑，不連線也不產圖。正式執行前請先確認 ComfyUI 能讀取到全部 LoRA；若已有既有圖片則會跳過，回傳全黑圖則停止。此腳本不會啟動 ComfyUI。

## 輸出與挑選

- `<WS>/06_train/lora_test/`：`base_seed….png`、`e5_seed….png`、…、`final_seed….png`。
- `<WS>/06_train/lora_test/test_meta.json`：正負向檔案路徑與內容、seeds、strength、workflow、unet，以及每張圖片的 sha256、檔案大小與尺寸。
- `<WS>/06_train/checkpoint_comparison.png`：列為 base／各 epoch／final，欄為 seeds，兩軸皆有文字標籤。

使用者可從對照圖挑選 epoch，保留對應的 `<WS>/06_train/models/` LoRA 檔。
