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
- 上述 `<群組>` 使用 SFW 群組名；NSFW 的 `collected_nsfw` 執行 `python -B scripts/grok_upscale.py --workspace <WS>`，預設讀取 `resized/_needs_upscale/collected_nsfw/*.png`、輸出至 `resized/_up_grok/collected_nsfw/`。亦可如 Codex 明確傳入 `out_dir` 與圖片；預設 `--min-long 768 --model grok-4.7 --timeout 3600 --retries 2`，逐張在 `.grok_upscale_*/` 隔離目錄（`image` profile：只有 read_file、image_edit，prompt 附原圖尺寸）使用單圖 `image_edit` 保持內容，外層檢查長邊與長寬比（誤差 ≤ 3%）。支援 `--only`、`--dry-run`、`--log-dir`、`--keep-generated`，結果為輸出目錄的 `summary.json`、`failed.json` 與 `logs/`，不自動執行備案。
- 若皆失敗：`<ENV>/esrgan_venv/bin/python -B scripts/esrgan_upscale.py <WS>/05_caption/resized/_up_esrgan/<群組> <WS>/05_caption/resized/_needs_upscale/<群組>/<檔名> --model <ENV>/models/RealESRGAN_x4plus_anime_6B.pth`。

選用 `codex_upscale.py --keep-generated` 時，固定指定 `<WS>/05_caption/resized/_up_codex/<群組>/generated`。放大結果（檔名不變）複製回 `<WS>/05_caption/resized/<群組>/`，再進行編號：

```
python -B scripts/build_train_set.py --workspace <WS>
```

輸出 `<WS>/05_caption/images/0001.png…` 與 `<WS>/05_caption/images/manifest.json`（包含 filename、sha256、dims、source_group、source_file、nsfw、nsfw_dir，以及 num_repeats 建議值 = ceil(480/圖數)）。群組名須與 `<WS>/05_caption/vocab/caption_vocab_params.json` 一致。

`build_train_set.py` 在編號前自動核對來源旁的 `resize_manifest.json`：所有 `needs_upscale` 圖片都必須以同名併回 `resized/<群組>/`、可完整讀取，且長邊 ≥ 768（若設定更高的放大目標則依該目標）。任一缺少、損壞、尺寸不足或群組未傳入，就列出清單並以非零狀態停止；修正後才能編號，不可靜默略過。

**NSFW 隔離在此步驟完成**（Codex 打標程式不檢查 NSFW，會把 `<WS>/05_caption/images` 裡的圖全部交給 Codex 處理）：

- 上游分流：02 `dedup_split.py` 使用 WD Tagger 將 questionable／explicit 分流至 `<WS>/02_clean/nsfw/`，僅有 `<WS>/02_clean/sfw/` 會交給 `codex_clean.py`；`<WS>/02_clean/nsfw/` 由 `grok_clean.py` 處理後放入 `<WS>/02_clean/collected_nsfw/`，`resize_prep.py` 以 `collected_nsfw` 群組處理，放大亦由 `grok_upscale.py` 執行（不交由 `codex_upscale.py` 處理）。
- `build_train_set.py`：`群組:nsfw=dir` 的圖片在編號後存至 `<WS>/05_caption/images_nsfw/`（workspace 模式已提供 `--nsfw-out` 預設值），**不放進 `<WS>/05_caption/images`**；其他群組（收集 SFW、Codex keep、Grok keep、Codex change）放至 `<WS>/05_caption/images`。編號跨兩個資料夾連續，`<WS>/05_caption/images/manifest.json` 會列出全部圖片（`nsfw=true` 的圖片位於 `nsfw_dir`）。
- 防呆機制：若同一個來源資料夾同時被指定為一般與 NSFW 群組，或一般群組含有與 NSFW 群組 sha256 相同的圖片時，程式將直接停止。
- 因此 Codex 打標的輸入資料夾 `<WS>/05_caption/images` 僅有 SFW 圖片；`<WS>/05_caption/images_nsfw/` 則僅提供給 Grok。

## a. 詞表（Codex 起草，Grok 覆核）

僅檢視**清理後的收集圖**（`source_group = collected`，不含 Grok / Codex 生成圖）。NSFW 收集圖從 manifest 的 `nsfw_dir` 讀取，可放進拼圖，但只給 Grok；Codex 不得看到任何 NSFW 拼圖或原圖。

被 `grok_vocab.py` 叫起來時，本節會出現在隔離資料夾的 `vocab_rules.md`。那是備援撰寫：直接看完全部拼圖與至少一張原圖，依下列規則以 schema 回傳整份 vocab。不要等 Codex，也不要只列修正。

**誰寫詞表：** 預設 Codex 起草，Grok 只覆核並改正看錯的特徵。不要把 Grok 從零寫詞表當成主路徑。Codex 成功交出草稿時，Grok 不重寫整份；Codex 拒絕、無法完成，或草稿嚴重不可用時，才改由 Grok 撰寫。

1. **Codex 起草（主路徑）。** 不要先跑 `grok_vocab.py`。先產生拼圖、`names.json` 與 `vocab.schema.json`：

```
python -B scripts/vocab_tools.py sheets --workspace <WS>
```

目前沒有 `codex_vocab.py`。操作者另開一次 Codex，只把下列檔案交給它（不要附上其他案件的 `vocab.json`，也不要給 NSFW）：

- 只含 SFW 圖格的 `<WS>/05_caption/vocab/contact_sheets/sheet_*.jpg`。對照 manifest，任一格是 NSFW 就整張拼圖不給 Codex。
- 至少一張清楚的 SFW 原圖（`<WS>/05_caption/images/`，建議主要服裝、正面且臉部清楚）。
- 本節規則、`<WS>/05_caption/vocab/caption_vocab_params.json` 與 `vocab.schema.json`。

Codex 依 schema 寫入 `<WS>/05_caption/vocab/vocab.json`。它看不到的 NSFW 收集圖不要猜檔名或服裝；留給下一步補進 `outfits[].images`。

2. **Grok 覆核（Codex 已交出可用草稿時）。** 沒有覆核腳本，也不要跑 `grok_vocab.py`（它會覆寫 `vocab.json`）。Grok 對照全部拼圖（含 NSFW）與至少一張原圖，檢查 Codex 的 `vocab.json`。只改正看錯的 trait（例如胸部尺寸、髮型、瀏海），並把 Codex 不能看的 NSFW 圖補進所屬服裝。直接改 `vocab.json` 裡的那些欄位。草稿大致可用時不要整份重寫。

3. **Grok 撰寫整份詞表（僅備援）。** 以下情況改跑既有腳本，由 Grok Build 從零建立並覆寫 `vocab.json`：

- Codex 因內容審核拒絕、拒絕產出或工具失敗，沒有完成草稿。
- 草稿嚴重不可用：多數特徵與畫面不符、服裝蓋不住收集圖，或只改少數 trait 後仍無法通過 check。

```
python -B scripts/grok_vocab.py --workspace <WS> [--main-outfit <主要服裝id>]
```

腳本先執行 `vocab_tools.py sheets`，再把拼圖、原圖、本節規則、params 與 `vocab.schema.json` 複製到 `05_caption/vocab/.grok_vocab_*/` 隔離資料夾，以它為 cwd 並加上 `--sandbox lora_min`（strict + 禁讀 `/tmp/*`；kernel 限制只能讀 cwd、系統路徑與 `~/.grok`）、`read` profile（只有 read_file、list_dir）及「只能讀工作資料夾內檔案」的規則呼叫 Grok Build，避免讀到 `/workspace` 其他舊詞表；Grok 檢視 `contact_sheets/sheet_*.jpg`（每格標示檔名，每張 8 格）及**至少一張原圖**（建議主要服裝、正面且臉部清楚），確認臉型、髮型、瀏海、眼睛與配件。腳本以 `vocab.schema.json` 取得 structuredOutput 寫入 `vocab.json`，並從 session 的 `chat_history.jsonl` 確認所有拼圖及至少一張原圖確實被檢視；未檢視則重試。規則如下：

- `character_features`：`[{trait, tag}]`，每個特徵對應一個 canonical tag（不再標 visibility）。
- `outfits`：`[{id: "outfit_…", name, tags: [{tag}], images: [檔名]}]`，每張收集圖恰好屬於一套。
- **每張必填 vs 可選**：`caption_vocab_params.json` 的 `fixed_traits`（預設 `height`、`body_type`、`age`）是唯一定義處；這些 trait 必須寫進詞表，逐張打標時對應欄位每張都必填、不可留空。其他角色特徵（含 `face_shape`）與所有服裝 tag 皆為可選：打標時只能從詞表列出的 tag 挑選（schema enum，不可自創），看不到就留空。
- `face_shape` 必填進詞表（看過原圖後判斷），字串、恰好一個 tag：臉部整體輪廓與臉頰的 danbooru 式 tag。候選例：`round face`、`oval face`、`long face`、`pointy chin`、`chubby cheeks`、`square jaw`；都不合適時可自行寫一個簡短 danbooru 式 tag（小寫、≤ 4 個英文單字）。表情（如 puffy cheeks、blush）不放這裡，其他頭部細節放 `head_*`。
- tag 採用 danbooru 式、小寫、≤ 4 個英文單字，不可有同義詞、佔位詞或版面用語；角色特徵 tag 不可重複出現在服裝中。
- 年齡採用 danbooru 式（例如 `girl`）。身體特徵必須包含在詞表內。

trait 名稱決定歸入哪一個 caption 欄位（參考 `<WS>/05_caption/vocab/caption_vocab_params.json` 的 `field_traits`，Grok 隔離資料夾內為 `./caption_vocab_params.json`；完全相同者優先，其次為 `前綴*`）：

| trait | caption 欄位 | 例 |
|---|---|---|
| `height`（每張必填） | height_of_this_character | short |
| `body_type`（每張必填） | body_type_of_his_character | petite |
| `age`（每張必填） | age_of_this_character | girl |
| `face_shape` | shape_of_the_face（字串，一個 tag） | round face |
| `hair_style`、`bangs`、`hair_style_*` | style_of_the_hair | twintails、hair between eyes |
| `hair_length` | length_of_the_hair | medium hair |
| `hair_color` | color_of_the_hair | black hair |
| `eye_color` | color_of_the_eyes | red eyes |
| `skin_color` | color_of_the_skin | fair skin |
| `chest` | size_of_the_chest | small breasts |
| `head_*` | character_head_features_tags | head_fang → fang |
| `body_*` | character_body_characteristics_tags | body_legs → slender legs |
| `accessory_*` | character_accessories_tags（角色固定配件，例如髮飾） | accessory_hair_x → x hair ornament |

服裝 tag 中屬於配件者（例如 choker、necklace、sunglasses…），由 `outfit_accessory_tags` 清單分流至 character_accessories_tags，其餘則歸入 character_clothing_tags。若角色擁有清單外的配件，請加入 `<WS>/05_caption/vocab/caption_vocab_params.json` 的清單中（Grok 沒有寫檔工具，改以 structuredOutput 的 `outfit_accessory_tags_add` 回報要新增的配件，腳本把原檔備份成 `caption_vocab_params.prev_<時間>.json` 後寫回）；驗證與打標預設使用本案版本，亦可透過 `--params` 覆寫。

Codex 草稿經 Grok 改完，或依使用者回饋手動改過詞表之後，執行下列驗證（`grok_vocab.py` 在備援撰寫成功後會自己跑）。通過後記錄主要服裝，供後續測試使用：

```
python -B scripts/vocab_tools.py check --workspace <WS> --main-outfit <主要服裝id>
```

明確指定 `--main-outfit` 時會同時寫回 `project.json` 的 `main_outfit_id`；之後可省略此參數。

驗證 PASS 後將寫入 `<WS>/05_caption/vocab/vocab_summary.md` 與 `<WS>/05_caption/vocab/main_outfit.json`（包含 main_outfit_id、name、tags、image_count），並印出各欄位的選項。若出現 ERROR（如未對應的 trait、缺少每張必填的 trait、欄位缺少 tag、圖片未分組等），請修正 vocab 後重新執行。

`grok_vocab.py` 預設 `--model grok-4.7 --timeout 3600 --retries 2 --sandbox lora_min`（`strict` 仍可讀 `/tmp`，`off` 不建議），輸出預設 `05_caption/vocab/`，含 `logs/`、`summary.json`、`failed.json`；可覆寫 `--out`、`--images`、`--manifest`，`--dry-run` 只列計畫。Codex 起草這條路不使用這些參數。

**使用者確認（暫停點）：** check PASS 後必須先暫停，不要進入 b. 打標。`grok_vocab.py` 會印出 `vocab_summary.md` 與主要服裝重點後結束；除非使用者明確說要自動執行並對該腳本加上 `--auto`，否則不要加 `--auto`。Codex 起草沒有 `--auto`，跑完 check 就暫停。把 `vocab_summary.md` 的重點（每張必填的身高、體型、年齡，以及臉型、髮色、髮型、瀏海、眼睛、膚色等特徵，主要服裝及其 tags、各服裝分組與圖數）整理給使用者，請使用者確認特徵是否都正確；依回饋修改 vocab 並重新執行 check，直到使用者確認後才繼續打標。

向使用者呈現詞表供確認時，每個英文／SDXL tag 旁必須附上繁體中文翻譯（例如 `pink hair`（粉紅髮））：

- 翻譯角色固定特徵（`fixed_traits`）、可選角色特徵，以及每套服裝的 tag。
- 服裝分組 id（例如 `outfit_white_dress`）維持原樣；翻譯的是人可讀的 tag 清單。
- 只翻譯 `vocab.json` 已列出的 tag，不可自創詞表沒有的項目。
- 這是確認步驟的呈現要求，不改變 `vocab.json` 的 schema，也不把中文寫進詞表檔。

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
- 詞表欄位（身高、體型、年齡、臉型、髮型、髮長、髮色、眼色、膚色、胸部、頭部特徵、身體特徵；固定版另含服裝、配件）只能從清單中勾選，由 schema enum 鎖定，不可自創 tag。`fixed_traits` 對應的身高、體型、年齡每張必填、不可留空（字串 enum 不含 `""`，陣列 `minItems: 1`）；其餘詞表欄位為可選，畫面中無法辨識則留空（陣列為 `[]`、字串為 `""`）。prompt 依此分成 Required／Optional vocabulary 兩段（模板變數 `{{required_vocab_lines}}`、`{{optional_vocab_lines}}`，依 `template_vars` 順序產生）。NSFW 欄位不輸出。
- 程式僅會讀取 `--images` 資料夾內的圖片（manifest 僅用於查詢 source_group；若資料夾內含有 manifest 未記錄的圖片將會報錯）。此處不做 NSFW 判斷，NSFW 圖片已由 `build_train_set.py` 移至 `<WS>/05_caption/images_nsfw/`。**正式呼叫 Codex 時，`--images` 只能指向 `<WS>/05_caption/images`。**下方 NSFW 流程僅以 `--dry-run` 在本機建立 schema，不呼叫 Codex。
- JSON → txt 轉換（`scripts/caption_convert.py`，邏輯與原 repo 相同）：去空值（drop_empty）→ 刪除 detailed_description → json_to_string → merge_all_caption([only_prefix(['anime style', trigger]), …])（透過 recreate_tags_format 去重）。此階段不做其他額外過濾，txt 一律以 `anime style, <trigger>, ` 開頭。若需單獨重新轉換：`python -B scripts/caption_convert.py <WS>/05_caption/captions/json <WS>/05_caption/captions/txt --stage-out <WS>/05_caption/captions/stage_txt --trigger <trigger>`。
- 若模型不在 Codex 的 `models_cache.json` 中，程式將直接停止：立即停下並告知使用者，不更換模型。
- 所有輸出均位於 `<WS>/05_caption/captions/`：包含 `json/`、`stage_txt/`、`txt/`、`prompts/`、`schemas/`、`params.json`、`assignment.json`、`results.json`、`summary.json`、`logs/` 與 `failed_raw/`；`--final-dir` 僅複製本次 JSON 驗證與 txt 寫入均成功的圖片及 txt，並核對 sha256。失敗項目不複製，且移除 final-dir 中該項目的舊圖與 txt；清單會印出並寫入 `summary.json` 的 `failed`，以非零狀態結束並回報使用者。可用同一指令加上 `--only <失敗檔名...>` 重跑。

## c. NSFW 打標（僅 Grok）

```
python -B scripts/grok_caption_nsfw.py --workspace <WS>
```

預設輸入 `<WS>/05_caption/images_nsfw/`、輸出 `captions_nsfw/`、成功項目複製至 `train_set/`。若 `assignment.json` 不存在，腳本先執行本機 `codex_caption_v2.py --workspace <WS> --nsfw-schema --dry-run` 建立 schema 與 prompt（只列檔名，不開啟圖片、不呼叫 Codex；**必須保留 `--dry-run`**）。

再逐張把圖片與 schema 複製到 `.grok_caption_*/` 隔離目錄，以 `read` profile（只有 read_file、list_dir，max-turns 10）呼叫 Grok Build 檢視圖片，依 `assignment.json` 的 group、outfit 使用 `schemas/<group>_<outfit>.schema.json` 與 `prompts/<stem>.txt`，將 structuredOutput 寫入 `json/<stem>.json`。預設 `--model grok-4.7 --timeout 3600 --retries 2`；`--images`、`--out`、`--final-dir` 可覆寫，`--dry-run` 只準備本機 schema／列計畫，不呼叫 Grok，`--only <失敗檔名...>` 重跑指定圖片。此腳本永不呼叫 Codex。

腳本接著執行 `caption_convert.py --workspace <WS>`，以 `--only` 僅驗證與轉換本次 JSON 成功的項目，欄位順序依 schema。僅在 JSON 驗證與 txt 寫入均成功後，複製對應圖片及同名 txt 至 `train_set/`，並核對 sha256；txt 以 `anime style, <trigger>, ` 開頭，不手寫 txt。失敗項目不複製，並移除最終資料夾中的舊圖與 txt；清單寫入 `summary.json`、`failed.json`，以非零狀態結束並回報使用者。呼叫紀錄位於 `captions_nsfw/logs/`。也可單獨執行 `python -B scripts/caption_convert.py --workspace <WS>` 驗證並轉換整批 JSON。
