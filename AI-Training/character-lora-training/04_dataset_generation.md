# 04. 資料集生成

路徑請參照 [00_workspace.md](00_workspace.md)；`<WS>` 為本案 workspace。

`--workspace` 預設使用本案角色設定圖與輸出路徑；補圖模式的資料夾與目標張數預設為 `change_outfit/` 與 2N（補圖未給 N 時為 30）。仍可明確傳入路徑、`--reference`、`--fill-existing <資料夾>` 或 `--target` 覆寫。

N 預設為 30，若使用者有指定則依指定數量。

| 來源 | 維持服裝（keep） | 換服裝（change） |
|---|---|---|
| Codex | N | 2N |
| Grok Build | N | —（Grok 僅生成相同服裝） |

## Codex

```
python -B scripts/codex_batch_image_gen.py --workspace <WS> N
```

執行一次即可在 `<WS>/04_generate/codex/` 生成 `keep_outfit/` N 張與 `change_outfit/` 2N 張（檔名為 `01.png`、`02.png`…，接續既有編號），預設使用 `gpt-6.1-sol`、effort 為 `medium`。各組數量不足時僅補足缺額張數，最多重試 3 輪；若仍不足則寫入 `<WS>/04_generate/codex/missing.json`（記錄各組缺額張數與最後錯誤），並回報使用者。

### 換裝圖不足：補圖模式

當 `<WS>/04_generate/codex/missing.json` 顯示 `change_outfit` 不足 2N 時，僅補換裝圖（不重新生成既有圖，亦不生成維持服裝圖）：

```
python -B scripts/codex_batch_image_gen.py --workspace <WS> N --fill-existing --dry-run      # 先看計畫：既有有效 PNG 數、要補幾張、下一個檔名
python -B scripts/codex_batch_image_gen.py --workspace <WS> N --fill-existing
```

- 計算資料夾內有效的 PNG（檢查 PNG 結構；損壞檔案不計，列於 `existing_invalid`），僅向 Codex 請求 `2N − 有效張數` 張，並使用換裝 prompt。
- 新檔案接在最大編號之後，以獨佔方式建立，不覆蓋既有檔案；若回傳圖片與既有圖片的 sha256 相同則予以捨棄。
- 隔離方式與一般模式相同。結束後更新 `<WS>/04_generate/codex/missing.json`（若已補齊則刪除）；若仍不足則回報使用者。

## Grok Build（keep N）

```
python -B scripts/grok_batch_image_gen.py --workspace <WS> N
```

N 預設 30，參考圖預設 `<WS>/03_sheet/character-sheet.png`，輸出預設 `<WS>/04_generate/grok/`。先呼叫一次 Grok（`read` profile，max-turns 5）規劃 N 個不同的 SFW 場景，由腳本寫入 `scenes.json`；重試或補圖沿用此檔，也可用 `--scenes <檔案>` 覆寫。每張在 `.grok_gen_*/` 隔離目錄（參考圖複製為 `reference.*`，`image` profile：只有 read_file、image_edit）由腳本要求一次 `image_edit`，`image=[sheet, sheet]` 讓長寬比生效，依檔案編號在 1:1、4:3、3:4、16:9、9:16 輪換。prompt 如下：

```
幫我維持服裝設計與角色特徵 生成1張這個角色在不同背景 不同姿勢 不同動作 不同表情 不同長寬比的一張圖 採用乾淨的日系動畫賽璐璐上色，線稿俐落，色塊均勻，陰影簡潔，漸層平滑。皮膚與服裝表面乾淨，不添加膠片顆粒、紙張紋理、斑駁筆觸、細碎雜點或過度銳化。背景使用簡潔的動畫美術風格，避免密集零碎的材質細節。保留角色與服裝的必要細節。
```

- 每張圖於後方加上各自的背景、姿勢、表情與鏡頭；服裝請註明 `outfit identical to the reference front view`。
- 背景須為乾淨、具真實場景感的動畫美術背景。若服裝走樣，則重新生成該張圖片。
- Grok 必須檢視結果，服裝走樣時重新生成；工具拒絕則記錄失敗，不改寫要求繞過限制。
- 腳本從新 session 取出最終圖片並轉成真正 PNG，存至 `keep_outfit/01.png`、`02.png`…，接續既有最大編號，以獨佔方式建立、不覆寫，sha256 重複圖捨棄。
- 只補有效 PNG 的缺額，損壞檔列於 `existing_invalid`，最多 3 輪（`--max-rounds` 可調）；未補齊寫入 `grok/missing.json` 的缺額與最後錯誤，完成後刪除。`summary.json` 與 `logs/` 保存結果及呼叫紀錄。
- 預設 `--model grok-4.7 --timeout 3600`；場景呼叫預設重試 2 次，逐張補圖使用上述輪數。可用 `--reference`、`--out` 覆寫路徑，`--only <檔名...>` 限定補圖編號，`--dry-run` 只列計畫。
