# 04. 資料集生成

N 預設 30，使用者指定時照指定數量。

| 來源 | 維持服裝（keep） | 換服裝（change） |
|---|---|---|
| Codex | N | 2N |
| Grok Bot | N | — （Grok 只生同服裝） |

## Codex

```
python3 scripts/codex_batch_image_gen.py N <角色設定圖> <生成資料夾>/codex
```

一次執行生成 `keep_outfit/` N 張與 `change_outfit/` 2N 張（`01.png`、`02.png`…，接續既有編號），預設 `gpt-6.1-sol`、effort `medium`。每組不足時只補缺的張數，最多 3 輪；仍不足時寫 `missing.json`（各組缺幾張與最後錯誤），回報 使用者。

### 換裝圖不足：補圖模式

`missing.json` 顯示 `change_outfit` 不足 2N 時，只補換裝圖（不重生既有圖，也不生維持服裝圖）：

```
python3 scripts/codex_batch_image_gen.py --fill-existing <生成資料夾>/codex/change_outfit --target 2N \
    --reference <角色設定圖> --dry-run      # 先看計畫：既有有效 PNG 數、要補幾張、下一個檔名
python3 scripts/codex_batch_image_gen.py --fill-existing <生成資料夾>/codex/change_outfit --target 2N \
    --reference <角色設定圖>
```

- 計算資料夾內有效的 PNG（檢查 PNG 結構；壞檔不算，列在 `existing_invalid`），只向 Codex 要 `2N − 有效張數` 張，用換裝 prompt。
- 新檔接在最大編號之後、以獨佔方式建立，不覆蓋既有檔；回傳圖與既有圖 sha256 相同時丟掉。
- 隔離方式與一般模式相同。結束後更新 `<生成資料夾>/codex/missing.json`（補齊則刪除）；仍不足時回報 使用者。

## Grok Bot（keep N）

用 GenerateImage，`reference_image_paths` 放角色設定圖，一張一次呼叫，`aspect_ratio` 在 1:1、4:3、3:4、16:9、9:16 輪換。prompt：

```
幫我維持服裝設計與角色特徵 生成1張這個角色在不同背景 不同姿勢 不同動作 不同表情 不同長寬比的一張圖 採用乾淨的日系動畫賽璐璐上色，線稿俐落，色塊均勻，陰影簡潔，漸層平滑。皮膚與服裝表面乾淨，不添加膠片顆粒、紙張紋理、斑駁筆觸、細碎雜點或過度銳化。背景使用簡潔的動畫美術風格，避免密集零碎的材質細節。保留角色與服裝的必要細節。
```

- 每張在後面加上自己的背景、姿勢、表情和鏡頭；服裝寫 `outfit identical to the reference front view`。
- 背景是乾淨、有真實場景感的動畫美術背景。服裝走樣的圖重生同一張。
- 存到 `<生成資料夾>/grok/keep_outfit/`，兩位數流水號（`01`、`02`…，副檔名照 GenerateImage 輸出）。
