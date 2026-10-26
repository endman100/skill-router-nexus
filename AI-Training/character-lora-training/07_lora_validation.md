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

## 執行三項測試

需安裝 Pillow；從本技能資料夾執行：

```bash
python scripts/eval_lora.py --workspace "<WS>"
```

預設讀取 `<WS>/06_train/models/*.safetensors`，比較 base、各 epoch（如 e5）與 final，輸出至 `<WS>/07_validate/`。未加 `--outfit` 時，showcase 會同時產出 `<WS>/07_validate/showcase_change/` 與 `<WS>/07_validate/showcase_keep/`。trigger 優先取自 `<WS>/05_caption/train_set/manifest.json` 的 `trigger`；缺少時從訓練 caption 推斷：`anime style, <trigger>, …` 取第二個逗號分隔詞，其他格式取第一個詞。無法推斷時使用 `--trigger` 指定。

未指定 `--tests` 時執行全部三項測試。可用 `--tests showcase` 只執行展示測試，或以逗號分隔多項，例如 `--tests scenario,showcase`；只會讀取所選測試需要的案例輸入。未選擇 reconstruction 時，不會複製 reference 圖片與 caption。

- `reconstruction`：重現訓練資料。預設挑選 4 組訓練 PNG 與同名 caption，依檔名長度、檔名字序排序，略過缺少 caption 的圖片，複製至 `reconstruction/reference/`；不足時依序循環複製補齊。reference 已足夠時直接沿用，否則補入尚未存在的檔案。每個案例預設僅使用 seed `31415926`，共 4 欄，對照圖集中於一張；可用 `--seeds` 指定多個逗號分隔的 seeds。
- `scenario`：換裝情境測試。將 `templates/validate_scenarios.txt` 逐行去除首尾空白、略過空行，依序編為 s00、s01 等，以 `templates/validate_scenario_prompt.tmpl` 的 `{trigger}`、`{character_features}`、`{scenario}` 組成 prompt。第 i 個情境（從 0 起算）的 seed 固定為 `31415926 + i*10000`，每列每個情境各生成一張。
- `showcase`：展示情境測試，使用與 scenario 相同的 workflow 與生成流程，每列為 base 或一個 checkpoint，每個案例各生成一張。`--outfit both`（預設）依序執行 change 與 keep，分別寫入 `showcase_change/` 與 `showcase_keep/`。`--outfit change` 只執行 change，讀取 `templates/showcase_change_outfit.txt`。`--outfit keep` 只執行 keep，讀取 `templates/showcase_keep_outfit.txt`，並加入角色原本／主要服裝。keep 模式優先使用 `<WS>/07_validate/prompts/main_outfit_tags.txt`，內容可為單行或多行，以逗號與換行分隔 tags，去除各項首尾空白並略過空項；該檔不存在時，改讀 `<WS>/05_caption/vocab/main_outfit.json` 的 `tags`，項目可為帶有 `tag` 的物件或字串。兩個來源皆不存在時停止並列出兩個路徑。change 模式不加入主要服裝。

showcase 資料檔每行一個 prompt 片段，只放場景／服裝／構圖文字，不含品質 tags；change 行包含服裝描述，keep 行只放場景與構圖。載入時逐行去除首尾空白、略過空行，保留其餘文字原樣，依序編為 c00、c01 等。`templates/showcase_prompt.tmpl` 為單行 `masterpiece, best quality, highres, ultra detailed, {trigger}, {character_features}, {cloth_feature}, {other}`，不含 `8K` 與固定的 `looking at viewer`。`{other}` 為 `solo_focus, human focus, ` 加上同序號 keep 行的場景；`{cloth_feature}` 在 keep 模式為主要服裝 tags，在 change 模式為 change 行去掉該場景後綴後的服裝描述。模板不固定 `full body`，構圖取自每行資料。第 i 個案例（從 0 起算）的 seed 為 `--showcase-seed-base`（預設 `31415926`）`+ i*10000`，並寫入 prompts.json，不從資料行讀取尺寸或 seed；解析度與步數沿用生成參數，預設 720×1280、40 steps。

角色特徵預設由 `<WS>/05_caption/vocab/vocab.json` 的 `character_features`，依 vocab-params 的 `field_traits` 順序與共用 trait 映射組成，包含身高、體型、年齡、臉型、髮型／長度／顏色、眼色、膚色、胸部、頭部與身體特徵，以及角色本身的配件（`accessory_*` trait，詞表中所有角色特徵都納入，不論打標時是每張必填或可選）；僅排除服裝欄位與 `main_outfit.json` 的 tags，去重後以逗號連接。若存在 `<WS>/07_validate/prompts/character_features.txt`，則改用該檔內容。三項測試的負向 prompt 均原樣使用 workflow 中 KSampler negative 所連接節點的文字（模板為 node 12），不設定逐圖負向 prompt；如需調整，請編輯 `<WS>/07_validate/workflow.json`。

可選參數：

- 路徑：`--checkpoints`、`--out-dir`、`--workflow`、`--scenario-template`、`--scenarios`、`--showcase-template`、`--showcase-change`、`--showcase-keep`、`--character-features`、`--vocab-params`。showcase 的三個路徑參數依序覆寫展示模板、change 資料檔、keep 資料檔，預設為上述技能內檔案。預設 workflow 優先使用 `<WS>/07_validate/workflow.json`，vocab-params 優先使用 `<WS>/05_caption/vocab/caption_vocab_params.json`，否則各自使用技能內模板。
- 案例：`--tests`（`reconstruction`、`scenario`、`showcase`，多項以逗號分隔，預設全部）、`--trigger`、`--num-reconstruction`、`--seeds`（逗號分隔整數，僅用於 reconstruction）、`--no-base`、`--outfit change|keep|both`（僅用於 showcase，預設 both；both 依序執行 change 與 keep）、`--showcase-seed-base`（showcase 第一個案例的 seed，預設 `31415926`）。
- 生成：`--strength` 預設 0.8；`--unet` 預設 `novaAnimeAM_v6029B.safetensors`；`--width`／`--height` 預設 720×1280；`--steps` 預設 40；`--cfg` 預設 4；`--sampler`／`--scheduler` 預設 `er_sde`／`simple`。
- 連線：`--comfy-url` 預設 `http://127.0.0.1:1121`，`--timeout` 為每張圖片的秒數，預設 600。

```bash
python scripts/eval_lora.py --workspace "<WS>" --dry-run
```

`--dry-run` 列出 JSON：trigger、workflow、checkpoints、預計挑選的 reference、所選測試（`selected_tests`）、所選測試的完整工作清單（含 prompt）與各項／總工作數。未指定 `--tests` 時 `selected_tests` 列出全部三項；showcase 預設展開為 change 與 keep 兩份工作清單，`tests` 的鍵為 `showcase_change`、`showcase_keep`（change 在前），`selected_tests` 仍只記一次 `showcase`，每筆工作的 `test` 仍為 `showcase`。明確指定 `--outfit change` 或 `--outfit keep` 時只列該一種，鍵名仍為 `showcase`。未選擇 reconstruction 時 reference 清單為空。不複製、不寫檔、不連線。正式執行先透過 `/object_info/LoraLoaderModelOnly` 確認全部 LoRA 可見；缺少時會提示將 extra_model_paths 的 `loras` 指向 checkpoints 資料夾。已存在的生成圖會略過生成並重新檢查，全黑圖則停止。

## 輸出與挑選

reconstruction 與 scenario 各自存於 `<WS>/07_validate/reconstruction/`、`<WS>/07_validate/scenario/`。showcase 依服裝模式存於 `<WS>/07_validate/showcase_change/` 與 `<WS>/07_validate/showcase_keep/`。預設 `--outfit both` 兩個目錄都會寫入；明確指定 `--outfit change` 或 `--outfit keep` 只寫入對應目錄。兩種模式的生成圖、prompts.json、test_meta.json 與對照圖分開保存，測試名稱仍為 `showcase`。使用 `--out-dir` 時改存於指定目錄下的同名子目錄：

- `lora_test/{label}_{case}_seed{seed}.png`：base／各 epoch／final 的生成圖。
- `test_meta.json`：本次所選測試（`selected_tests`）、每項工作的 prompt、workflow 中實際使用的負向文字（`negative`）、seeds、strength、workflow、模型與生成參數，以及各圖的 sha256、檔案大小與尺寸；reconstruction 另列 reference 檔案。showcase 另列 `outfit`、`data_file`、`template`、角色特徵與來源，keep 模式再列 `outfit_tags` 與 `outfit_source`（實際使用的 tags 文字檔或 JSON 路徑，prompts.json 亦同）。
- `checkpoint_comparison_01.png` 等：列為 base／各 epoch／final，欄為案例與 seed（reconstruction 先按案例再按 seed）；兩軸均有標籤，每張最多 6 欄，24 個情境會產生 4 張。reconstruction 最上方另有 `reference` 列，顯示縮至格子內的訓練原圖。
- reconstruction 的 `reference/` 保留選定的 PNG 與同名 caption；scenario 的 `prompts.json` 保留 trigger、角色特徵及來源、模板與情境檔路徑，以及各情境、seed 和完整 prompt。showcase 的 `prompts.json` 保留 trigger、角色特徵及來源、`outfit`、`data_file`、`template`、`showcase_seed_base`，以及各案例的原始片段（`showcase`）、`cloth_feature`、`other`、seed 與完整 prompt；keep 模式另列 `outfit_tags` 與 `outfit_source`。

使用者可從三項測試的對照圖挑選 epoch，保留對應的 `<WS>/06_train/models/` LoRA 檔。
