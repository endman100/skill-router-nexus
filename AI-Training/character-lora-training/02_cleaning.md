# 02. 清理

路徑依 [00_workspace.md](00_workspace.md) 規範：`<WS>` 為本案 workspace，`<ENV>` 為共用環境。

執行順序：去重 → WD Tagger 分流（Grok VM 本機）→ SFW 交由 Codex 清理 → NSFW 與 Codex 拒絕／失敗者交由 Grok 處理。

## 1–2. 去重與分流（不呼叫 Codex）

```
python3 -B scripts/dedup_split.py <WS>/02_clean codex=<WS>/01_collect/codex grok=<WS>/01_collect/grok \
    --model-dir <ENV>/models/wd-eva02-large-tagger-v3
```

- 先以 sha256 移除完全相同的圖片，再以 pHash（距離 ≤ 6）去除近似圖片，並保留面積較大者。
- 依 WD Tagger（`wd-eva02-large-tagger-v3`，CPU；本案路徑 `<ENV>/models/wd-eva02-large-tagger-v3`，以 `--model-dir` 指定）的 rating 進行分流：`general`、`sensitive` → `<WS>/02_clean/sfw/`；`questionable`、`explicit` → `<WS>/02_clean/nsfw/`。
- 輸出結果至 `<WS>/02_clean/` 目錄下的 `dedup/`、`sfw/`、`nsfw/`、`dedup.json` 與 `rating.json`。

## 3. Codex 清理 SFW

```
python3 -B scripts/codex_clean.py "<作品名> <角色名>" <WS>/02_clean/sfw <WS>/02_clean
```

執行單次隔離的 `codex exec`（預設 `gpt-6.1-sol`、effort `high`，並可使用圖像生成去除文字）。Codex 會依據角色名與整批圖片判斷角色外觀：先以 8 張一組拼圖進行初篩（確認角色是否存在、是否為線稿／黑白圖、畫面是否過於模糊；若無法確定則開啟原圖檢視），接著逐張處理：角色檢測、品質檢查、剔除線稿與黑白圖、裁切至僅保留目標角色、去除文字／對白框／浮水印並與原圖進行比對。

處理結果會自動輸出至 `<WS>/02_clean/codex_clean/`，包含清理後的圖片、`summary.json`（檔名對照表）與 `rejected.json`（問題圖片與原因：角色不存在、品質過低、線稿或黑白圖、裁切失敗、去字走樣、拒絕處理）。

## 4. Grok 處理

針對 `<WS>/02_clean/nsfw/` 中的圖片，以及 `<WS>/02_clean/codex_clean/rejected.json` 內 Codex 拒絕處理或失敗的圖片，由 Grok Bot 依照第 3 步的標準進行處理（需要時可使用 `python3 -B scripts/wdtag.py --model-dir <ENV>/models/wd-eva02-large-tagger-v3 <WS>/02_clean/nsfw/<檔名>` 查看 tag）。可疑內容（例如外觀未成年的性化圖片）直接排除並列給使用者。

將 `<WS>/02_clean/codex_clean/` 中的 PNG 檔案複製至 `<WS>/02_clean/collected_sfw/`，經 Grok 處理通過的 SFW 圖片亦存入此處；NSFW 圖片則存入 `<WS>/02_clean/collected_nsfw/`。步驟 05 會以 `collected:nsfw=` 傳入後者，編號後的圖片會存放到 `<WS>/05_caption/images_nsfw/`，不進入 Codex 打標資料夾。後續的 Codex 腳本亦不再進行 SFW 檢查。
