# 07. LoRA 驗證

路徑依 [00_workspace.md](00_workspace.md)：`<WS>` 為本案 workspace，`<ENV>` 為共用環境。

## 啟動 ComfyUI

先從本技能資料夾複製設定：

```bash
cp templates/extra_model_paths.example.yaml "<WS>/07_validate/extra_model_paths.yaml"
```

將 `<WS>/07_validate/extra_model_paths.yaml` 的 `base_path` 改為 `<WS>/06_train` 的絕對路徑，`loras` 保持為 `models`，即指向 `<WS>/06_train/models/`。ComfyUI 的 `models/diffusion_models/`、`text_encoders/`、`vae/` 需能讀取到 `<ENV>/models/` 的 Anima、`qwen_3_06b_base.safetensors`、`qwen_image_vae.safetensors`（workflow 預設檔名）。從 `<ENV>/ComfyUI/` 啟動，port 固定為 1121：

```bash
python main.py --port 1121 --extra-model-paths-config "<WS>/07_validate/extra_model_paths.yaml"
```

可選擇將 `templates/animaEndToEnd_fast.json` 複製至 `<WS>/07_validate/workflow.json` 調整；未提供時直接使用模板。驗證腳本不會啟動 ComfyUI。

## 執行兩項測試

需安裝 Pillow；從本技能資料夾執行：

```bash
python scripts/eval_lora.py --workspace "<WS>"
```

預設讀取 `<WS>/06_train/models/*.safetensors`，比較 base、各 epoch（如 e5）與 final，輸出至 `<WS>/07_validate/`。trigger 優先取自 `<WS>/05_caption/train_set/manifest.json` 的 `trigger`；缺少時從訓練 caption 推斷：`anime style, <trigger>, …` 取第二個逗號分隔詞，其他格式取第一個詞。無法推斷時使用 `--trigger` 指定。

- `reconstruction`：重現訓練資料。預設挑選 4 組訓練 PNG 與同名 caption，依檔名長度、檔名字序排序，略過缺少 caption 的圖片，複製至 `reconstruction/reference/`；不足時依序循環複製補齊。reference 已足夠時直接沿用，否則補入尚未存在的檔案。每個案例預設僅使用 seed `31415926`，共 4 欄，對照圖集中於一張；可用 `--seeds` 指定多個逗號分隔的 seeds。
- `scenario`：換裝情境測試。將 `templates/validate_scenarios.txt` 逐行去除首尾空白、略過空行，依序編為 s00、s01 等，以 `templates/validate_scenario_prompt.tmpl` 的 `{trigger}`、`{character_features}`、`{scenario}` 組成 prompt。第 i 個情境（從 0 起算）的 seed 固定為 `31415926 + i*10000`，每列每個情境各生成一張。

角色特徵預設由 `<WS>/05_caption/vocab/vocab.json` 的 `character_features`，依 vocab-params 的 `field_traits` 順序與共用 trait 映射組成，包含身高、體型、年齡、髮型／長度／顏色、眼色、膚色、胸部、頭部與身體特徵，不受 visibility 影響；排除配件欄位與 `main_outfit.json` 的 tags，去重後以逗號連接。若存在 `<WS>/07_validate/prompts/character_features.txt`，則改用該檔內容。兩項測試共用 `<WS>/07_validate/prompts/negative.txt`，未提供時為空。

可選參數：

- 路徑：`--checkpoints`、`--out-dir`、`--workflow`、`--negative-file`、`--scenario-template`、`--scenarios`、`--character-features`、`--vocab-params`。預設 workflow 優先使用 `<WS>/07_validate/workflow.json`，vocab-params 優先使用 `<WS>/05_caption/vocab/caption_vocab_params.json`，否則各自使用技能內模板。
- 案例：`--trigger`、`--num-reconstruction`、`--seeds`（逗號分隔整數，僅用於 reconstruction）、`--no-base`。
- 生成：`--strength` 預設 0.8；`--unet` 預設 `novaAnimeAM_v6029B.safetensors`；`--width`／`--height` 預設 720×1280；`--steps` 預設 40；`--cfg` 預設 4；`--sampler`／`--scheduler` 預設 `er_sde`／`simple`。
- 連線：`--comfy-url` 預設 `http://127.0.0.1:1121`，`--timeout` 為每張圖片的秒數，預設 600。

```bash
python scripts/eval_lora.py --workspace "<WS>" --dry-run
```

`--dry-run` 列出 JSON：trigger、workflow、checkpoints、預計挑選的 reference、兩項測試的完整工作清單（含 prompt）與各項／總工作數；不複製、不寫檔、不連線。正式執行先透過 `/object_info/LoraLoaderModelOnly` 確認全部 LoRA 可見；缺少時會提示將 extra_model_paths 的 `loras` 指向 checkpoints 資料夾。已存在的生成圖會略過生成並重新檢查，全黑圖則停止。

## 輸出與挑選

兩項測試各自存於 `<WS>/07_validate/reconstruction/` 與 `<WS>/07_validate/scenario/`：

- `lora_test/{label}_{case}_seed{seed}.png`：base／各 epoch／final 的生成圖。
- `test_meta.json`：每項工作的 prompt、負向檔案與文字、seeds、strength、workflow、模型與生成參數，以及各圖的 sha256、檔案大小與尺寸；reconstruction 另列 reference 檔案。
- `checkpoint_comparison_01.png` 等：列為 base／各 epoch／final，欄為案例與 seed（reconstruction 先按案例再按 seed）；兩軸均有標籤，每張最多 6 欄，24 個情境會產生 4 張。reconstruction 最上方另有 `reference` 列，顯示縮至格子內的訓練原圖。
- reconstruction 的 `reference/` 保留選定的 PNG 與同名 caption；scenario 的 `prompts.json` 保留 trigger、角色特徵及來源、模板與情境檔路徑，以及各情境、seed 和完整 prompt。

使用者可從兩項測試的對照圖挑選 epoch，保留對應的 `<WS>/06_train/models/` LoRA 檔。
