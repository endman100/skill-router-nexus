# 02. 清理

路徑依 [00_workspace.md](00_workspace.md) 規範：`<WS>` 為本案 workspace，`<ENV>` 為共用環境。

下列腳本以 `--workspace` 取得本案查詢字串、來源、輸入、輸出與模型目錄；明確指定的位置參數或 `--model-dir` 一律優先。

執行順序：去重 → WD Tagger 分流（Grok VM 本機）→ SFW 交由 Codex 清理 → NSFW 與 Codex 拒絕／失敗者交由 Grok 處理。

## 1–2. 去重與分流（不呼叫 Codex）

```
python -B scripts/dedup_split.py --workspace <WS>
```

- 收集完成後，先遞迴掃描兩個來源（含子資料夾），將全部可讀圖片統一命名為 `000001.<副檔名>`、`000002.<副檔名>`…；原始檔保留，新檔名與原始絕對路徑寫入 `<WS>/02_clean/input_mapping.json`，後續沿用此唯一主檔名。
- 再以 sha256 移除完全相同的圖片，以 pHash（距離 ≤ 6）去除近似圖片，並保留面積較大者。
- 依 WD Tagger（`wd-eva02-large-tagger-v3`，CPU；本案路徑 `<ENV>/models/wd-eva02-large-tagger-v3`，以 `--model-dir` 指定）的 rating 進行分流：`general`、`sensitive` → `<WS>/02_clean/sfw/`；`questionable`、`explicit` → `<WS>/02_clean/nsfw/`。
- 輸出結果至 `<WS>/02_clean/` 目錄下的 `input_mapping.json`、`dedup/`、`sfw/`、`nsfw/`、`dedup.json` 與 `rating.json`。

## 3. Codex 清理 SFW

```
python -B scripts/codex_clean.py --workspace <WS>
```

執行單次隔離的 `codex exec`（預設 `gpt-6.1-sol`、effort `high`，並可使用圖像生成去除文字）。Codex 會依據角色名與整批圖片判斷角色外觀：先以 8 張一組拼圖進行初篩（確認角色是否存在、是否為線稿／黑白圖、畫面是否過於模糊；若無法確定則開啟原圖檢視），接著逐張處理：角色檢測、品質檢查、剔除線稿與黑白圖、裁切至僅保留目標角色、去除文字／對白框／浮水印並與原圖進行比對。

處理結果會自動輸出至 `<WS>/02_clean/codex_clean/`，包含清理後的圖片、`summary.json`（檔名對照表）與 `rejected.json`（問題圖片與原因：角色不存在、品質過低、線稿或黑白圖、裁切失敗、去字走樣、拒絕處理）。

## 4. Grok 處理

```
python -B scripts/grok_clean.py --workspace <WS>
```

預設讀取 `<WS>/02_clean/nsfw/` 全部圖片，以及 `<WS>/02_clean/codex_clean/rejected.json` 列出的 `<WS>/02_clean/sfw/` 圖片，逐張複製至暫存工作目錄，透過 Grok Build CLI 依第 3 步標準清理。需要時可用 `python -B scripts/wdtag.py --model-dir <ENV>/models/wd-eva02-large-tagger-v3 <WS>/02_clean/nsfw/<檔名>` 查看 tag。可疑內容（例如外觀未成年的性化圖片）直接排除，寫入 `grok_clean/suspicious.json` 並列給使用者。

腳本也會將 `codex_clean/*.png` 複製至 `collected_sfw/`。原先來自 `nsfw/` 的圖片通過後一律存入 `collected_nsfw/`，不因 Grok 的 rating 改送 Codex；Codex 拒絕圖則依 Grok 的 rating 存至 `collected_sfw/` 或 `collected_nsfw/`。步驟 05 以 `collected:nsfw=` 傳入後者，編號後存於 `images_nsfw/`，不進入 Codex 打標資料夾。

預設 `--model grok-4.7 --timeout 3600 --retries 2`；可覆寫 `--target`、`--nsfw`、`--sfw`、`--codex-clean`、`--out`、`--collected-sfw`、`--collected-nsfw`。`--only <檔名...>` 重跑指定圖片，`--dry-run` 只列計畫。輸出與呼叫紀錄位於 `<WS>/02_clean/grok_clean/`：`summary.json`、`rejected.json`、`suspicious.json`、`failed.json`、`logs/`。後續 Codex 腳本不再進行 SFW 檢查。
