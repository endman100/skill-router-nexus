# 01. 資料收集

路徑依 [00_workspace.md](00_workspace.md)；`<WS>` 為本案 workspace。

作品名、角色名與輸出路徑預設取自 `project.json`；仍可明確傳入查詢字串與輸出路徑覆寫。

輸入作品名 + 角色名，Codex 與 Grok Build 同時使用同一句指令各自收集，各存入一個資料夾：

```
幫我收集 <作品名> <角色名> 可以用來訓練 LoRA 的資料
```

## Codex

```
python -B scripts/codex_collect.py --workspace <WS>
```

執行一次隔離的 `codex exec`（可連網、僅寫入工作目錄），結果複製至 `<WS>/01_collect/codex/`，包含 `sources.json`（檔名與來源網址）。預設參數為 `--model gpt-6.1-sol --effort high --timeout 3600`。同一資料夾不可重複執行（不覆寫）。

## Grok Build

```
python -B scripts/grok_collect.py --workspace <WS>
```

使用同一句查詢，透過已登入的 `/home/box/.local/bin/grok`（`web` profile：只有 read_file、web_search、web_fetch，無 shell／寫檔，隔離 cwd + 沙箱）以 web_fetch 驗證後回傳圖片網址清單（structuredOutput `images[{image_url, source_url}]`），由腳本自行下載（僅 http/https、≤40MB、PIL 驗證、sha256 去重、獨佔建立不覆寫）至 `<WS>/01_collect/grok/`，包含 `sources.json`（filename、source_url、image_url）與下載失敗清單 `download_failed.json`。預設 `--model grok-4.7 --timeout 3600 --retries 2`；`--query`、`--out` 可覆寫查詢與目的地，非空目的地會停止，不覆寫。呼叫紀錄存於 `grok/logs/`，結果寫入 `summary.json`、`failed.json`；可先加 `--dry-run` 查看計畫。
