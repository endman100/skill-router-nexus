# 03. 三視圖（已有則跳過）

路徑請參照 [00_workspace.md](00_workspace.md)；`<WS>` 為本案 workspace。

若已有角色設定圖（三視圖），請直接存至 `<WS>/03_sheet/character-sheet.png` 使用。若無，則交由 Codex 溝通者，請 Codex 使用 skill-router-nexus 的 [`Image-Generation/character-sheet`](https://github.com/endman100/skill-router-nexus/tree/main/Image-Generation/character-sheet) skill 生成，並附上參考圖：使用者提供的 `<WS>/01_collect/reference/` 參考圖；若無，則從 `<WS>/02_clean/collected_sfw/` 挑選 **4 張**主要服裝的代表圖提供給 Codex。

- 版面採用預設的 unmeasured 5×3：正面、左側、背面全身，手部、鞋子、服裝細節，兩個表情與一張正面頭像。
- 服裝維持參考圖原樣。
- 輸出至 `<WS>/03_sheet/character-sheet.png`，即為步驟 04 的參考圖。
