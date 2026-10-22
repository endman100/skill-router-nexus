# 04. 資料集生成

路徑請參照 [00_workspace.md](00_workspace.md)；`<WS>` 為本案 workspace。

`--workspace` 預設使用本案角色設定圖與輸出路徑；補圖模式的資料夾與目標張數預設為 `change_outfit/` 與 2N（補圖未給 N 時為 30）。仍可明確傳入路徑、`--reference`、`--fill-existing <資料夾>` 或 `--target` 覆寫。

N 預設為 30，若使用者有指定則依指定數量。

| 來源 | 維持服裝（keep） | 換服裝（change） |
|---|---|---|
| Codex | N | 2N |
| Grok Bot | N | —（Grok 僅生成相同服裝） |

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

## Grok Bot（keep N）

使用 GenerateImage，將 `reference_image_paths` 設定為 `<WS>/03_sheet/character-sheet.png`，每張圖片呼叫一次，`aspect_ratio` 依序在 1:1、4:3、3:4、16:9、9:16 之間輪換。prompt 如下：

```
幫我維持服裝設計與角色特徵 生成1張這個角色在不同背景 不同姿勢 不同動作 不同表情 不同長寬比的一張圖 採用乾淨的日系動畫賽璐璐上色，線稿俐落，色塊均勻，陰影簡潔，漸層平滑。皮膚與服裝表面乾淨，不添加膠片顆粒、紙張紋理、斑駁筆觸、細碎雜點或過度銳化。背景使用簡潔的動畫美術風格，避免密集零碎的材質細節。保留角色與服裝的必要細節。
```

- 每張圖於後方加上各自的背景、姿勢、表情與鏡頭；服裝請註明 `outfit identical to the reference front view`。
- 背景須為乾淨、具真實場景感的動畫美術背景。若服裝走樣，則重新生成該張圖片。
- 儲存至 `<WS>/04_generate/grok/keep_outfit/`，檔名使用兩位數流水號（`01`、`02`…，副檔名依 GenerateImage 輸出）。
