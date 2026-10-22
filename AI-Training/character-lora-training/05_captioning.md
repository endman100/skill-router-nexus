# 05. 整理訓練集與打標

路徑依 [00_workspace.md](00_workspace.md)：`<WS>` 為本案 workspace，`<ENV>` 為共用環境。

詞表與打標腳本以 `--workspace` 執行時，若本案詞表參數尚不存在，會自動從 `templates/caption_vocab_params.json` 複製至 `<WS>/05_caption/vocab/caption_vocab_params.json`，不覆寫既有檔案；後續可直接修改這份檔案。

下列腳本的本案路徑、角色名、作品名與 trigger 皆由 `--workspace` 提供預設值；明確指定的原有參數一律優先。

## 0. 尺寸與編號

```
python -B scripts/resize_prep.py --workspace <WS>
```

輸出檔名為 `<群組>__<原檔名含副檔名>.png`，避免同主檔名的不同格式互相覆蓋；`resize_manifest.json` 保存來源路徑與輸出對照。

長邊 > 1280 以 LANCZOS 縮至 1280；長邊 < 768 則放入 `<WS>/05_caption/resized/_needs_upscale/<群組>/`。放大處理方式如下：

- SFW：`python -B scripts/codex_upscale.py <WS>/05_caption/resized/_up_codex/<群組> <WS>/05_caption/resized/_needs_upscale/<群組>/*.png`（隔離 Codex 圖像生成，外層檢查長邊 ≥ 768、長寬比誤差 ≤ 3%）。
- 上述 `<群組>` 使用 SFW 群組名；NSFW 的 `collected_nsfw` 由 Grok Bot 放大，存至 `<WS>/05_caption/resized/_up_grok/collected_nsfw/`。
- 若皆失敗：`<ENV>/esrgan_venv/bin/python -B scripts/esrgan_upscale.py <WS>/05_caption/resized/_up_esrgan/<群組> <WS>/05_caption/resized/_needs_upscale/<群組>/<檔名> --model <ENV>/models/RealESRGAN_x4plus_anime_6B.pth`。

選用 `codex_upscale.py --keep-generated` 時，固定指定 `<WS>/05_caption/resized/_up_codex/<群組>/generated`。放大結果（檔名不變）複製回 `<WS>/05_caption/resized/<群組>/`，再進行編號：

```
python -B scripts/build_train_set.py --workspace <WS>
```

輸出 `<WS>/05_caption/images/0001.png…` 與 `<WS>/05_caption/images/manifest.json`（包含 filename、sha256、dims、source_group、source_file、nsfw、nsfw_dir，以及 num_repeats 建議值 = ceil(480/圖數)）。群組名須與 `<WS>/05_caption/vocab/caption_vocab_params.json` 一致。

`build_train_set.py` 在編號前自動核對來源旁的 `resize_manifest.json`：所有 `needs_upscale` 圖片都必須以同名併回 `resized/<群組>/`、可完整讀取，且長邊 ≥ 768（若設定更高的放大目標則依該目標）。任一缺少、損壞、尺寸不足或群組未傳入，就列出清單並以非零狀態停止；修正後才能編號，不可靜默略過。

**NSFW 隔離在此步驟完成**（Codex 打標程式不檢查 NSFW，會把 `<WS>/05_caption/images` 裡的圖全部交給 Codex 處理）：

- 上游分流：02 `dedup_split.py` 使用 WD Tagger 將 questionable／explicit 分流至 `<WS>/02_clean/nsfw/`，僅有 `<WS>/02_clean/sfw/` 會交給 `codex_clean.py`；`<WS>/02_clean/nsfw/` 由 Grok 處理後放入 `<WS>/02_clean/collected_nsfw/`，`resize_prep.py` 以 `collected_nsfw` 群組處理，放大亦由 Grok 執行（不交由 `codex_upscale.py` 處理）。
- `build_train_set.py`：`群組:nsfw=dir` 的圖片在編號後存至 `<WS>/05_caption/images_nsfw/`（workspace 模式已提供 `--nsfw-out` 預設值），**不放進 `<WS>/05_caption/images`**；其他群組（收集 SFW、Codex keep、Grok keep、Codex change）放至 `<WS>/05_caption/images`。編號跨兩個資料夾連續，`<WS>/05_caption/images/manifest.json` 會列出全部圖片（`nsfw=true` 的圖片位於 `nsfw_dir`）。
- 防呆機制：若同一個來源資料夾同時被指定為一般與 NSFW 群組，或一般群組含有與 NSFW 群組 sha256 相同的圖片時，程式將直接停止。
- 因此 Codex 打標的輸入資料夾 `<WS>/05_caption/images` 僅有 SFW 圖片；`<WS>/05_caption/images_nsfw/` 則僅提供給 Grok。

## a. 詞表（由 Grok Bot 自行建立）

僅檢視**清理後的收集圖**（`source_group = collected`，不含 Grok / Codex 生成圖）：

```
python -B scripts/vocab_tools.py sheets --workspace <WS>
```

（NSFW 收集圖從 manifest 的 `nsfw_dir` 讀取，一起放進拼圖；拼圖僅提供給 Grok 檢視。）

Grok 使用 Read 檢視 `<WS>/05_caption/vocab/contact_sheets/sheet_*.jpg`（每格標示檔名，每張 8 格），看不清楚時才開啟原圖，並撰寫 `<WS>/05_caption/vocab/vocab.json`（schema = `<WS>/05_caption/vocab/vocab.schema.json`）：

- `character_features`：`[{trait, tag, visibility}]`，每個特徵對應一個 canonical tag，`visibility` 為 `always`／`sometimes`。
- `outfits`：`[{id: "outfit_…", name, tags: [{tag, visibility}], images: [檔名]}]`，每張收集圖恰好屬於一套。
- tag 採用 danbooru 式、小寫、≤ 4 個英文單字，不可有同義詞、佔位詞或版面用語；角色特徵 tag 不可重複出現在服裝中。
- 年齡採用 danbooru 式（例如 `girl`）。身體特徵必須包含在詞表內。

trait 名稱決定歸入哪一個 caption 欄位（參考 `<WS>/05_caption/vocab/caption_vocab_params.json` 的 `field_traits`，完全相同者優先，其次為 `前綴*`）：

| trait | caption 欄位 | 例 |
|---|---|---|
| `height` | height_of_this_character | short |
| `body_type` | body_type_of_his_character | petite |
| `age` | age_of_this_character | girl |
| `hair_style`、`bangs`、`hair_style_*` | style_of_the_hair | twintails、hair between eyes |
| `hair_length` | length_of_the_hair | medium hair |
| `hair_color` | color_of_the_hair | black hair |
| `eye_color` | color_of_the_eyes | red eyes |
| `skin_color` | color_of_the_skin | fair skin |
| `chest` | size_of_the_chest | small breasts |
| `head_*` | character_head_features_tags | head_fang → fang |
| `body_*` | character_body_characteristics_tags | body_legs → slender legs |
| `accessory_*` | character_accessories_tags（角色固定配件，例如髮飾） | accessory_hair_x → x hair ornament |

服裝 tag 中屬於配件者（例如 choker、necklace、sunglasses…），由 `outfit_accessory_tags` 清單分流至 character_accessories_tags，其餘則歸入 character_clothing_tags。若角色擁有清單外的配件，請加入 `<WS>/05_caption/vocab/caption_vocab_params.json` 的清單中；驗證與打標預設使用本案版本，亦可透過 `--params` 覆寫。

驗證並記錄主要服裝（供後續測試使用）：

```
python -B scripts/vocab_tools.py check --workspace <WS> --main-outfit <主要服裝id>
```

明確指定 `--main-outfit` 時會同時寫回 `project.json` 的 `main_outfit_id`；之後可省略此參數。

驗證 PASS 後將寫入 `<WS>/05_caption/vocab/vocab_summary.md` 與 `<WS>/05_caption/vocab/main_outfit.json`（包含 main_outfit_id、name、tags、image_count），並印出各欄位的選項。若出現 ERROR（如未對應的 trait、固定欄位缺少 tag、圖片未分組等），請修正 vocab 後重新執行。

## b. 逐張打標（Codex）

先以 dry-run 檢查分組與 prompt（此步驟不呼叫 Codex）：

```
python -B scripts/codex_caption_v2.py --workspace <WS> --dry-run [--only 0001.png]
```

正式執行（workspace 模式預設 `--final-dir <WS>/05_caption/train_set`，指定 `--final-dir` 時自動複製 manifest；預設參數即為 `--model gpt-6-luna --effort max --workers 16 --retries 2`，每張圖片獨立呼叫一次）：

```
python -B scripts/codex_caption_v2.py --workspace <WS>
```

- 分組：**A** 固定模板 + 主要服裝清單（主要服裝的收集圖、Codex keep、Grok keep）；**B_fixed** 固定模板 + 該造型清單（收集圖其他造型，按造型分批套用清單）；**B_free** 自由模板（Codex 換裝圖，服裝與配件自由發揮，schema 禁止使用主要服裝 tag）。
- 固定欄位（身高、體型、年齡、髮型、髮長、髮色、眼色、膚色、胸部、頭部特徵、身體特徵；固定版另含服裝、配件）只能從清單中勾選，由 schema enum 鎖定；若畫面中無法辨識則留空（陣列為 `[]`、字串為 `""`）。NSFW 欄位不輸出。
- 程式僅會讀取 `--images` 資料夾內的圖片（manifest 僅用於查詢 source_group；若資料夾內含有 manifest 未記錄的圖片將會報錯）。此處不做 NSFW 判斷，NSFW 圖片已由 `build_train_set.py` 移至 `<WS>/05_caption/images_nsfw/`。**正式呼叫 Codex 時，`--images` 只能指向 `<WS>/05_caption/images`。**下方 NSFW 流程僅以 `--dry-run` 在本機建立 schema，不呼叫 Codex。
- JSON → txt 轉換（`scripts/caption_convert.py`，邏輯與原 repo 相同）：去空值（drop_empty）→ 刪除 detailed_description → json_to_string → merge_all_caption([only_prefix(['anime style', trigger]), …])（透過 recreate_tags_format 去重）。此階段不做其他額外過濾，txt 一律以 `anime style, <trigger>, ` 開頭。若需單獨重新轉換：`python -B scripts/caption_convert.py <WS>/05_caption/captions/json <WS>/05_caption/captions/txt --stage-out <WS>/05_caption/captions/stage_txt --trigger <trigger>`。
- 若模型不在 Codex 的 `models_cache.json` 中，程式將直接停止：立即停下並告知使用者，不更換模型。
- 所有輸出均位於 `<WS>/05_caption/captions/`：包含 `json/`、`stage_txt/`、`txt/`、`prompts/`、`schemas/`、`params.json`、`assignment.json`、`results.json`、`summary.json`、`logs/` 與 `failed_raw/`；`--final-dir` 僅複製本次 JSON 驗證與 txt 寫入均成功的圖片及 txt，並核對 sha256。失敗項目不複製，且移除 final-dir 中該項目的舊圖與 txt；清單會印出並寫入 `summary.json` 的 `failed`，以非零狀態結束並回報使用者。可用同一指令加上 `--only <失敗檔名...>` 重跑。

## c. NSFW 打標（僅 Grok）

以 `--nsfw-schema` 使用 NSFW 輸入與輸出預設路徑，先在本機依相同詞表與分組規則建立 schema（只列檔名，不開啟圖片、不呼叫 Codex；**必須保留 `--dry-run`**）：

```
python -B scripts/codex_caption_v2.py --workspace <WS> --nsfw-schema --dry-run
```

Grok 檢視 `images_nsfw/`，依 `captions_nsfw/assignment.json` 的 group、outfit 找到 `schemas/<group>_<outfit>.schema.json`，套用同一份詞表與打標規則，將同名 JSON 寫入 `captions_nsfw/json/`。再驗證並轉成 txt（`caption_convert.py --workspace` 預設處理 `captions_nsfw`；需 jsonschema；整批含缺檔檢查，失敗會列清單並停止；欄位順序依 schema）：

```
python -B scripts/caption_convert.py --workspace <WS>
```

僅在驗證與轉換成功後，將對應圖片與同名 txt 複製至 `<WS>/05_caption/train_set/`；txt 同樣以 `anime style, <trigger>, ` 開頭，不手寫 txt。失敗先由 Grok 修正 JSON 再重跑，並回報使用者。
