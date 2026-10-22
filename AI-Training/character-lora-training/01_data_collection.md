# 01. 資料收集

路徑依 [00_workspace.md](00_workspace.md)；`<WS>` 為本案 workspace。

作品名、角色名與輸出路徑預設取自 `project.json`；仍可明確傳入查詢字串與輸出路徑覆寫。

輸入作品名 + 角色名，Codex 與 Grok Bot 同時使用同一句指令各自收集，各存入一個資料夾：

```
幫我收集 <作品名> <角色名> 可以用來訓練 LoRA 的資料
```

## Codex

```
python -B scripts/codex_collect.py --workspace <WS>
```

執行一次隔離的 `codex exec`（可連網、僅寫入工作目錄），結果複製至 `<WS>/01_collect/codex/`，包含 `sources.json`（檔名與來源網址）。預設參數為 `--model gpt-6.1-sol --effort high --timeout 3600`。同一資料夾不可重複執行（不覆寫）。

## Grok Bot

Grok Bot 同時使用同一句指令自行收集，存至 `<WS>/01_collect/grok/`，同樣會寫入 `sources.json`。
