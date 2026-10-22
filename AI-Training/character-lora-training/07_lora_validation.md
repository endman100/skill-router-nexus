# 07. LoRA 驗證

## 啟動 ComfyUI

先將 `templates/extra_model_paths.example.yaml` 複製為自己的 `extra_model_paths.yaml`，把 `base_path` 改成含有 `models/` 的訓練輸出資料夾（06 的 `<work-dir>`），讓 `loras` 指向 `<run>/models`。從 ComfyUI 資料夾啟動，port 固定為 1121：

```bash
python main.py --port 1121 --extra-model-paths-config "<extra_model_paths.yaml>"
```

## 固定條件對照

使用者提供 UTF-8 固定正向 prompt 檔案；結構為「風格詞 + trigger + 外觀／服裝描述 + 全身站姿」。所有 checkpoint 與 base 共用同一份檔案及 seeds。可另提供負向檔案，未提供時為空。

需安裝 Pillow；以下從本技能資料夾執行，路徑含空白時保留引號：

```bash
python scripts/eval_lora.py \
  --run-dir "<run>" --prompt-file "<使用者的固定正向文字檔>" \
  --comfy-url http://127.0.0.1:1121
```

- 預設比較 base、各 epoch、final，seeds 為 `31415926,42,1234567,20261022`，LoRA strength 為 0.8；`--no-base` 可略過 base。
- 預設模型 `novaAnimeAM_v6029B.safetensors`，720×1280、40 steps、CFG 4、`er_sde`／`simple`。可用 `--unet`、`--width`、`--height`、`--steps`、`--cfg`、`--sampler`、`--scheduler` 調整。
- `--negative-file "<負向文字檔>"`、`--seeds "<逗號分隔整數>"`、`--strength`、`--workflow` 可覆寫；`--timeout` 是每張秒數（預設 600）。
- 加 `--dry-run` 只列 labels、LoRA 檔、seeds 與輸出路徑，不連線、不寫圖。正式執行先確認 ComfyUI 看得到全部 LoRA；既有圖片跳過，回傳全黑圖則停止。腳本不會啟動 ComfyUI。

## 輸出與挑選

- `<run>/lora_test/`：`base_seed….png`、`e5_seed….png`、…、`final_seed….png`。
- `<run>/lora_test/test_meta.json`：正負向檔案路徑與內容、seeds、strength、workflow、unet，以及每張圖的 sha256、檔案大小與尺寸。
- `<run>/checkpoint_comparison.png`：列為 base／各 epoch／final，欄為 seeds，兩軸皆有文字標籤。

使用者從對照圖挑選 epoch，保留對應的 `models/` LoRA 檔。
