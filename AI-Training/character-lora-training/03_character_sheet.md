# 03. 三視圖（步驟 2 清理前產出；已有則跳過）

路徑請參照 [00_workspace.md](00_workspace.md)；`<WS>` 為本案 workspace。此步驟已移入 [02_cleaning.md](02_cleaning.md)：去重與 WD Tagger 分流完成後、任何清理之前執行，保留 `03_sheet/` 資料夾名稱。

若使用者已提供角色設定圖，存至 `<WS>/03_sheet/character-sheet.png`；腳本偵測已存在便跳過生成。否則執行：

```bash
python -B scripts/codex_sheet.py --workspace <WS>
```

單次隔離 Codex 執行（預設 `--model gpt-6.1-sol --effort high --timeout 3600`，啟用 image_generation），只取得 `<WS>/02_clean/sfw/` 全部圖片與複製的 `Image-Generation/character-sheet` 技能資料夾。Codex 瀏覽輸入並挑選 **4 張**主要服裝代表圖，依複製的 `SKILL.md` 生成。

- 版面採用預設 unmeasured 5×3：正面、左側、背面全身，手部、鞋子、服裝細節，兩個表情與一張正面頭像。
- 服裝維持參考圖原樣。
- 輸出至 `<WS>/03_sheet/character-sheet.png`，供 Codex／Grok 清理與步驟 04 參考。
- 選圖清單 `chosen-inputs.json` 與呼叫紀錄存入 `<WS>/03_sheet/codex_sheet/`；紀錄由 `run_isolated` 寫入 `sheet/`。

`--inputs <檔案...>` 可傳入使用者提供的參考圖，僅限 SFW。`--sheet-skill` 可覆寫技能資料夾（預設為本技能資料夾相對的 `../../Image-Generation/character-sheet`）；`--out`、`--log-dir` 可覆寫輸出與紀錄位置，`--codex` 指定執行檔，`--dry-run` 只印出 JSON 計畫，不呼叫 Codex。

**使用者確認（暫停點）：** 生成後腳本印出設定圖路徑與中文暫停訊息，以狀態碼 0 結束。代理必須先停止並等待使用者確認設定圖或替換此圖，確認後才執行清理。使用者明確要求自動執行時加上 `--auto`，不要求確認，直接繼續步驟 2 的逐張清理。
