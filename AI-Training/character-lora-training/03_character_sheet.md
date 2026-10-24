# 03. 三視圖（步驟 2 清理前產出；已有則跳過）

路徑請參照 [00_workspace.md](00_workspace.md)；`<WS>` 為本案 workspace。此步驟已移入 [02_cleaning.md](02_cleaning.md)：去重與 WD Tagger 分流完成後、任何清理之前執行，保留 `03_sheet/` 資料夾名稱。

若使用者已提供角色設定圖，存至 `<WS>/03_sheet/character-sheet.png`；腳本偵測已存在便跳過生成。否則執行：

```bash
python -B scripts/codex_sheet.py --workspace <WS>
```

單次隔離 Codex 執行（預設 `--model gpt-6.1-sol --effort high --timeout 3600`，啟用 image_generation），取得 `<WS>/02_clean/sfw/` 最多 `--max-images` 張（預設 30）與複製的 `Image-Generation/character-sheet` 技能資料夾。依 `<WS>/02_clean/rating.json`，先按檔名選入 `source` 為 `reference` 的使用者參考圖，再從其餘按檔名排序的 SFW 圖等距取樣補足上限；只選輸入中存在的檔案，NSFW 參考圖不會進入。缺少 `rating.json` 時全部按檔名排序後等距取樣。Codex 瀏覽輸入並挑選 **4 張**主要服裝代表圖，優先使用 prompt 列出的使用者參考圖，依複製的 `SKILL.md` 生成。

- 版面採用預設 unmeasured 5×3：正面、左側、背面全身，手部、鞋子、服裝細節，兩個表情與一張正面頭像。
- 服裝維持參考圖原樣。
- 輸出至 `<WS>/03_sheet/character-sheet.png`，供 Codex／Grok 清理與步驟 04 參考。
- 選圖清單 `chosen-inputs.json` 與呼叫紀錄存入 `<WS>/03_sheet/codex_sheet/`；紀錄由 `run_isolated` 寫入 `sheet/`。

`--inputs <檔案或目錄...>` 可覆寫 SFW 輸入；使用者參考圖先經步驟 2 去重與分流。`--rating` 可覆寫 rating.json 路徑（workspace 預設 `<WS>/02_clean/rating.json`）。`--sheet-skill` 可覆寫技能資料夾（預設為本技能資料夾相對的 `../../Image-Generation/character-sheet`）；`--out`、`--log-dir` 可覆寫輸出與紀錄位置，`--codex` 指定執行檔，`--dry-run` 只印出 JSON 計畫與選入清單，不呼叫 Codex。

生成後腳本印出設定圖路徑，以狀態碼 0 結束。主助理只有在使用者確認角色設定圖之後，或使用者在對話中明確表示全自動（full auto）時，才執行下列指令；預設由使用者手動確認。已有設定圖同樣需要核准：

```bash
python -B scripts/ws.py approve-sheet --workspace <WS>
```

指令將 `sheet`（`03_sheet/character-sheet.png`）、目前圖片的 `sha256` 與含時區偏移的 ISO-8601 `approved_at` 寫入 `<WS>/03_sheet/sheet_approved.json`；缺少設定圖即停止。Codex／Grok 清理前檢查核准紀錄與目前圖片的 sha256，缺少或不符即停止；`grok_clean --dry-run` 可略過。替換設定圖後須重新確認並執行核准。
