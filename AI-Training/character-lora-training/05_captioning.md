# 05. 整理訓練集與打標

以下 `<T>` = 訓練資料夾，`<V>` = 詞表資料夾，`<C>` = 打標輸出資料夾。

## 0. 尺寸與編號

```
python3 scripts/resize_prep.py <R> collected=<清理後收集圖> collected_nsfw=<Grok處理的NSFW收集圖> \
    gen_codex_keep=<生成>/codex/keep_outfit gen_grok_keep=<生成>/grok/keep_outfit gen_codex_change=<生成>/codex/change_outfit
```

長邊 >1280 用 LANCZOS 縮到 1280；長邊 <768 放進 `<R>/_needs_upscale/<群組>/`。放大：

- SFW：`python3 scripts/codex_upscale.py <R>/_up_codex <R>/_needs_upscale/<SFW群組>/*.png`（隔離 Codex 圖像生成，外層檢查長邊 ≥768、長寬比誤差 ≤3%）。
- NSFW：Grok Bot 放大。
- 都失敗：`<esrgan venv>/bin/python scripts/esrgan_upscale.py <R>/_up_esrgan <失敗的圖>`（模型 `--model` 或 `ESRGAN_MODEL`）。

放大結果（檔名不變）複製回 `<R>/<群組>/`，再編號：

```
python3 scripts/build_train_set.py <T> --character "<角色名> (<作品名>)" --trigger <trigger> \
    collected=<R>/collected collected:nsfw=<R>/collected_nsfw \
    gen_codex_keep=<R>/gen_codex_keep gen_grok_keep=<R>/gen_grok_keep gen_codex_change=<R>/gen_codex_change
```

輸出 `<T>/0001.png…` 與 `<T>/manifest.json`（filename、sha256、dims、source_group、source_file、nsfw、nsfw_dir、num_repeats 建議值 = ceil(480/圖數)）。群組名要與 `templates/caption_vocab_params.json` 一致。

**NSFW 隔離在這一步完成**（Codex 打標程式不檢查 NSFW，會把 `<T>` 裡的圖全部交給 Codex）：

- 上游分流：02 `dedup_split.py` 用 WD Tagger 把 questionable／explicit 分到 `nsfw/`，只有 `sfw/` 交給 `codex_clean.py`；`nsfw/` 由 Grok 處理後放在獨立資料夾，`resize_prep.py` 以 `collected_nsfw` 群組處理，放大由 Grok 做（不交 `codex_upscale.py`）。
- `build_train_set.py`：`群組:nsfw=dir` 的圖編號後放到 `<T>_nsfw/`（可用 `--nsfw-out` 指定），**不放進 `<T>`**；其他群組（收集 SFW、Codex keep、Grok keep、Codex change）放 `<T>`。編號跨兩個資料夾連續，`<T>/manifest.json` 列出全部圖（`nsfw=true` 的在 `nsfw_dir`）。
- 防呆：同一個來源資料夾同時當一般與 NSFW 群組、或一般群組含有與 NSFW 群組 sha256 相同的圖時，程式直接停止。
- 所以 Codex 打標的輸入資料夾 `<T>` 只有 SFW；`<T>_nsfw/` 只給 Grok。

## a. 詞表（Grok Bot 自己做）

只看**清理後的收集圖**（`source_group = collected`，不含 Grok/Codex 生成圖）：

```
python3 scripts/vocab_tools.py sheets --images <T> --manifest <T>/manifest.json --out <V>
```

（NSFW 收集圖從 manifest 的 `nsfw_dir` 讀，一起放進拼圖；拼圖只給 Grok 看。）

Grok 用 Read 看 `<V>/contact_sheets/sheet_*.jpg`（每格標檔名，8 格一張），看不清才開原圖，寫 `<V>/vocab.json`（schema = `<V>/vocab.schema.json`）：

- `character_features`：`[{trait, tag, visibility}]`，每個特徵一個 canonical tag，`visibility` 為 `always`／`sometimes`。
- `outfits`：`[{id: "outfit_…", name, tags: [{tag, visibility}], images: [檔名]}]`，每張收集圖恰屬一套。
- tag 用 danbooru 式、小寫、≤4 個英文單字，不可有同義詞、佔位詞或版面用語；角色特徵 tag 不可再出現在服裝。
- 年齡用 danbooru 式（例 `girl`）。身體特徵必須在詞表內。

trait 名決定進哪個 caption 欄位（`caption_vocab_params.json` 的 `field_traits`，完全相同優先，其次 `前綴*`）：

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

服裝 tag 中屬於配件的（choker、necklace、sunglasses…）由 `outfit_accessory_tags` 清單分到 character_accessories_tags，其餘進 character_clothing_tags。角色有清單外的配件時，複製 params 另存、加進清單，打標時用 `--params` 指定。

驗證並記錄主要服裝（之後測試用）：

```
python3 scripts/vocab_tools.py check --vocab <V>/vocab.json --names <V>/names.json --main-outfit <主要服裝id>
```

PASS 後寫 `<V>/vocab_summary.md` 與 `<V>/main_outfit.json`（main_outfit_id、name、tags、image_count），並印出每個欄位的選項。有 ERROR（未對應的 trait、固定欄位沒有 tag、圖片未分組…）就修 vocab 再跑。

## b. 逐張打標（Codex）

先 dry-run 檢查分組與 prompt（不呼叫 Codex）：

```
python3 scripts/codex_caption_v2.py --character "<角色名>" --work "<作品名>" --trigger <trigger> \
    --images <T> --manifest <T>/manifest.json --vocab <V>/vocab.json --main-outfit <V>/main_outfit.json \
    --out <C> --dry-run [--only 0001.png]
```

正式執行（預設即 `--model gpt-6-luna --effort max --workers 16 --retries 2`，一張一呼叫）：

```
python3 scripts/codex_caption_v2.py <同上參數> --out <C> --final-dir <訓練集輸出資料夾>
```

- 分組：**A** 固定模板 + 主要服裝清單（主要服裝的收集圖、Codex keep、Grok keep）；**B_fixed** 固定模板 + 該造型清單（收集圖其他造型，按造型分批套清單）；**B_free** 自由模板（Codex 換裝圖，服裝／配件自由，schema 禁止用主要服裝 tag）。
- 固定欄位（身高、體型、年齡、髮型、髮長、髮色、眼色、膚色、胸部、頭部特徵、身體特徵；固定版另含服裝、配件）只能從清單勾，schema enum 鎖住；看不到留空（陣列 `[]`、字串 `""`）。NSFW 欄位不輸出。
- 程式只讀 `--images` 資料夾裡的圖（manifest 只用來查 source_group；資料夾裡有 manifest 沒有的圖就報錯）。不做 NSFW 判斷，NSFW 已由 `build_train_set.py` 放到 `<T>_nsfw/`。**`--images` 只能指向 `<T>`，不可指向 `<T>_nsfw/` 或混合資料夾。**
- JSON → txt（`scripts/caption_convert.py`，與原 repo 相同）：去空值（drop_empty）→ 刪 detailed_description → json_to_string → merge_all_caption([only_prefix(['anime style', trigger]), …])（recreate_tags_format 去重）。不做其他過濾。txt 以 `anime style, <trigger>, ` 開頭。單獨重轉：`python3 scripts/caption_convert.py <C>/json <txt輸出> --trigger <trigger>`。
- `<T>_nsfw/` 的圖由 Grok 照同一份詞表與規則寫同名 txt，再連同圖片複製到訓練集輸出資料夾。
- 模型不在 Codex 的 `models_cache.json` 時程式直接停止：停下告知 使用者，不換模型。
- 輸出：`<C>/json/`、`stage_txt/`、`txt/`、`prompts/`、`schemas/`、`assignment.json`、`results.json`、`summary.json`、`logs/`、`failed_raw/`；`--final-dir` 把圖與 txt 複製過去並核對 sha256。重試後仍失敗的列在 `summary.json` 的 `failed`，回報 使用者。
