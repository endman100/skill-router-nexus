# 04. 資料集生成

路徑請參照 [00_workspace.md](00_workspace.md)；`<WS>` 為本案 workspace。

先完成**全部**案例規劃並寫入 JSON，再依該計畫**一次只生成一張圖**。重跑、`--only` 與 `--fill-existing` 都沿用已存的計畫，只補缺少或損壞的檔案；不重新設計案例，也不覆寫有效 PNG。要重做某一張，先刪除該檔，再用原來的案例 id 生成。

N 預設為 30。總張數維持不變：

| 來源 | 維持服裝（keep） | 換服裝（change） |
|---|---|---|
| Codex | N | 2N |
| Grok Build | N | —（Grok 僅生成相同服裝） |

案例編號穩定，不接在最大編號後面補洞：`keep_01`…、`change_01`…，檔名為各組資料夾內的 `01.png`、`02.png`…。長寬比依該組編號在 1:1、4:3、3:4、16:9、9:16 輪換，並寫進案例。`--only` 可寫案例 id，或 `群組/檔名`（例如 `change_02`、`change_outfit/02.png`）；只寫 `02.png` 時，本次會處理的每個群組裡的同名檔都會對上。

內容一律 SFW。keep 的服裝固定為參考圖正面（`identical to the reference front view`）；change 每張的 `outfit` 都不同，且不改臉、髮型、瞳色。已存在的有效 `01.png` 視為該案例完成。損壞的同名 PNG 會在重試時替換。與同資料夾既有圖 sha256 相同的新圖捨棄。

`--workspace` 預設使用本案角色設定圖與輸出路徑。仍可傳入路徑、`--reference`、`--cases` / `--scenes`、`--fill-existing` 或 `--target` 覆寫。`--dry-run` 不呼叫模型：尚無計畫檔時只列出將建立的張數與案例 id；已有計畫檔時列出即將生成的案例內容。

## Codex

計畫檔：`<WS>/04_generate/codex/cases.json`。

```
python -B scripts/codex_batch_image_gen.py --workspace <WS> N --dry-run
python -B scripts/codex_batch_image_gen.py --workspace <WS> N --design-only
python -B scripts/codex_batch_image_gen.py --workspace <WS> N
python -B scripts/codex_batch_image_gen.py --workspace <WS> N --only change_02 keep_05
```

1. 若 `cases.json` 不存在，先用隔離的 Codex **一次**設計全部 keep N + change 2N 案例（不啟用 `image_generation`；沙箱、權限與停用功能與生圖相同，只附參考圖），檢查欄位、SFW 與重複後寫入 `cases.json`。規劃失敗會重試，次數與 `--max-rounds` 相同。已有計畫且 N 相同則直接沿用；N 不同或案例對不上則停止，不覆寫舊計畫。
2. `--design-only` 在寫入計畫後結束，不生圖。`--dry-run` 優先於 `--design-only`，兩者都給時不呼叫 Codex。
3. 其餘情況依計畫逐張生圖：每張一次 `image_generation`，提示只要求 1 張，由腳本存成該案例檔名。最多 `--max-rounds`（預設 3）輪。未完成的案例 id 與最後錯誤寫入 `<WS>/04_generate/codex/missing.json`；全部完成則刪除該檔。

預設模型 `gpt-6.1-sol`、effort `medium`。單張逾時預設 900 秒（`--timeout`），規劃逾時預設 1800 秒（`--plan-timeout`）。計畫 JSON 印在 stderr，完成的圖片路徑印在 stdout。

案例欄位：`id`、`group`（`keep_outfit` 或 `change_outfit`）、`filename`、`background`、`pose`、`action`、`expression`、`camera`、`aspect_ratio`、`outfit`。例如：

```json
{
  "n": 30,
  "cases": [
    {
      "id": "keep_01",
      "group": "keep_outfit",
      "filename": "01.png",
      "background": "清晨的學校走廊，光線乾淨",
      "pose": "站立，重心在右腳",
      "action": "抱著書本轉身",
      "expression": "平靜",
      "camera": "膝上中景",
      "aspect_ratio": "1:1",
      "outfit": "identical to the reference front view"
    },
    {
      "id": "change_01",
      "group": "change_outfit",
      "filename": "01.png",
      "background": "雨後的商店街",
      "pose": "坐下，身體微側",
      "action": "撐傘看向櫥窗",
      "expression": "輕微驚訝",
      "camera": "遠景全身",
      "aspect_ratio": "1:1",
      "outfit": "深藍水手領大衣與格紋裙，棕色肩包"
    }
  ]
}
```

### 換裝圖不足：補圖模式

只補 `change_outfit`（不生 keep，不覆寫有效圖）。沒有 `cases.json` 時仍先設計完整計畫（含 keep），再只生缺少的換裝圖。

```
python -B scripts/codex_batch_image_gen.py --workspace <WS> N --fill-existing --dry-run
python -B scripts/codex_batch_image_gen.py --workspace <WS> N --fill-existing
```

`--target` 在 `--workspace` 下預設 2N，表示從 `change_01` 起要完成的換裝案例數，不可大於計畫中的 2N。補圖未給 N 時 N 為 30。結束後更新 `missing.json`（已補齊則刪除）。

## Grok Build（keep N）

計畫檔仍是 `<WS>/04_generate/grok/scenes.json`。新檔內容為帶穩定 id 的 `cases`（欄位同上，但沒有 change，且 `outfit` 固定為參考圖正面）。舊版 `scenes` 字串清單會依順序對上 `keep_01`…，場景文字原樣留在 `legacy_scene`；正式執行時改寫成上述格式，`--dry-run` 不改檔。

```
python -B scripts/grok_batch_image_gen.py --workspace <WS> N --dry-run
python -B scripts/grok_batch_image_gen.py --workspace <WS> N --design-only
python -B scripts/grok_batch_image_gen.py --workspace <WS> N
python -B scripts/grok_batch_image_gen.py --workspace <WS> N --only keep_02
```

N 預設 30，參考圖預設 `<WS>/03_sheet/character-sheet.png`，輸出預設 `<WS>/04_generate/grok/`。場景設計呼叫一次 Grok（`read` profile，max-turns 5，`--retries` 預設 2）：一次要回 N 個互不相同的 SFW 案例（背景、姿勢、動作、表情、鏡頭）。可用 `--scenes` 或 `--cases` 指定計畫檔。

每張在 `.grok_gen_*/` 隔離目錄（參考圖複製為 `reference.*`，`image` profile：只有 read_file、image_edit）要求一次 `image_edit`，`image=[sheet, sheet]`，長寬比用該案例記錄的值。提示基底如下，其後附上該案例的場景、`outfit identical to the reference front view` 與長寬比：

```
幫我維持服裝設計與角色特徵 生成1張這個角色在不同背景 不同姿勢 不同動作 不同表情 不同長寬比的一張圖 採用乾淨的日系動畫賽璐璐上色，線稿俐落，色塊均勻，陰影簡潔，漸層平滑。皮膚與服裝表面乾淨，不添加膠片顆粒、紙張紋理、斑駁筆觸、細碎雜點或過度銳化。背景使用簡潔的動畫美術風格，避免密集零碎的材質細節。保留角色與服裝的必要細節。
```

- 重跑沿用 `scenes.json`，只補缺少或損壞的 `keep_XX.png`。
- 服裝走樣時由 Grok 在該次呼叫內重做該張；工具拒絕則記錄失敗，不改寫要求繞過限制。
- 腳本把 session 裡的最終圖片轉成 PNG，以獨佔方式寫入案例檔名。sha256 重複則捨棄。
- 逐張最多 `--max-rounds`（預設 3）輪。未補齊寫入 `grok/missing.json`（張數、案例 id、最後錯誤），完成後刪除。`summary.json` 與 `logs/` 保存結果及呼叫紀錄。
- 預設 `--model grok-4.7 --timeout 3600`。可用 `--reference`、`--out` 覆寫路徑。stdout 為本次計畫 JSON。
