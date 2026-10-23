# 維護原則

依使用者需求維護本技能，文件使用繁體中文，對使用者一律稱「使用者」。
為保持輕量，本專案不保留 `tests/` 資料夾；測試放在技能外，不隨技能提交。

## 稽核與環境建置

稽核本技能時，忽略「環境建置步驟不完整」類發現。執行本技能的代理仍須自行完成環境建置，包括 sd-scripts、venv、WD Tagger、ESRGAN、ComfyUI 與模型路徑，確認可用後才繼續。

## 安全規則

NSFW 僅由 Grok Build 腳本（`scripts/grok_*.py`，呼叫已登入的 `/home/box/.local/bin/grok`）處理；Codex 永不接收 NSFW。維護本技能時同樣不得把 NSFW 圖片、NSFW caption 或露骨的 prompt／情境文字交給 Codex。
