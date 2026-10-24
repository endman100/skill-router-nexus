# 02. 清理

路徑依 [00_workspace.md](00_workspace.md) 規範：`<WS>` 為本案 workspace，`<ENV>` 為共用環境。

下列腳本以 `--workspace` 取得本案查詢字串、來源、輸入、輸出與模型目錄；明確指定的位置參數或 `--model-dir` 一律優先。

執行順序：去重 → WD Tagger 分流（Grok VM 本機）→ 生成角色設定圖、確認後執行 `approve-sheet` → SFW 逐張交由 Codex 清理 → NSFW 與 Codex 交接圖交由 Grok 處理。

## 1–2. 去重與分流（不呼叫 Codex）

```
python -B scripts/dedup_split.py --workspace <WS>
```

- 收集完成後，先遞迴掃描 `<WS>/01_collect/` 的 `codex`、`grok`、`reference` 三個來源（含子資料夾），使用者參考圖同樣去重與分流。全部可讀圖片統一命名為 `000001.<副檔名>`、`000002.<副檔名>`…；原始檔保留，新檔名與原始絕對路徑寫入 `<WS>/02_clean/input_mapping.json`，後續沿用此唯一主檔名。
- 再以 sha256 移除完全相同的圖片，以 pHash（距離 ≤ 6）去除近似圖片，並保留面積較大者。
- 依 WD Tagger（`wd-eva02-large-tagger-v3`，CPU；本案路徑 `<ENV>/models/wd-eva02-large-tagger-v3`，以 `--model-dir` 指定）的 rating 進行分流：`general`、`sensitive` → `<WS>/02_clean/sfw/`；`questionable`、`explicit` → `<WS>/02_clean/nsfw/`。NSFW 使用者參考圖不交給 Codex。
- `rating.json` 每筆結果包含 `source`（`codex`／`grok`／`reference`）、分數與分流。
- 輸出結果至 `<WS>/02_clean/` 目錄下的 `input_mapping.json`、`dedup/`、`sfw/`、`nsfw/`、`dedup.json` 與 `rating.json`。

## 3. 清理前產出三視圖

閱讀 [03_character_sheet.md](03_character_sheet.md)。直接使用去重、分流後的 `<WS>/02_clean/sfw/` 生成 `<WS>/03_sheet/character-sheet.png`，已有使用者提供的設定圖則跳過生成。

```
python -B scripts/codex_sheet.py --workspace <WS>
```

腳本印出設定圖路徑後結束。主助理只有在使用者確認角色設定圖之後，或使用者在對話中明確表示全自動（full auto）時，才執行下列指令；預設由使用者手動確認：

```
python -B scripts/ws.py approve-sheet --workspace <WS>
```

此指令寫入 `<WS>/03_sheet/sheet_approved.json`。Codex／Grok 清理前會核對目前設定圖的 sha256；缺少核准紀錄或雜湊不符即停止，替換設定圖後須重新確認並執行核准。

## 4. Codex 逐張清理 SFW

```
python -B scripts/codex_clean.py --workspace <WS>
```

每張 SFW 圖片各執行一次獨立隔離的 `codex exec`，只傳入該圖與角色設定圖。預設 `--model gpt-6.1-sol --effort high --timeout 480 --jobs 3`（timeout 為每張秒數）。每次比對設定圖確認角色存在、檢查品質、剔除線稿與黑白圖、裁切至僅保留目標角色，並以 image_generation 去除文字／對白框／浮水印、與原圖比對。

輸入預設 `<WS>/02_clean/sfw/`，輸出至 `<WS>/02_clean/codex_clean/`；`--sheet` 預設 `<WS>/03_sheet/character-sheet.png`，缺少設定圖即停止。可用位置參數 `"<作品名> <角色名>" <輸入目錄> <WS>/02_clean` 覆寫目標與目錄；另有 `--codex`、`--keep-workdir`、`--only <檔名...>`。

每張完成後印出進度，立即以原子替換寫入 `<stem>.png`、`rejected.json`（陣列）與 `summary.json`；`logs/<stem>/` 保留 argv、prompt、events、stderr、last message 與 status。續跑時跳過已有輸出 PNG 或拒收紀錄的圖片。`summary.json` 的 `moderation_blocked` 陣列依 `rejected.json` 列出遭阻擋的檔名，包含續跑前紀錄；全部完成後另印出 `moderation_blocked: <檔名...>`。

拒收原因：`not_present`（角色不存在）、`crop_failed`（裁切失敗）、`text_removal_distorted`（去字失真）、`low_quality`（品質過低）、`lineart_or_monochrome`（線稿或黑白圖）、`refused`（拒絕處理）。腳本另將 `timeout`（逾時）、`codex_failed`（Codex 執行失敗：非零退出或未產生輸出／拒收紀錄）、`moderation_blocked`（圖像生成遭 moderation 阻擋）寫入同一份拒收清單，附上 `"handoff": "grok"`。每筆皆含 `filename`（`sfw/` 原始檔名）、`reason`、`reason_zh`、`detail`。

## 5. Grok 處理

```
python -B scripts/grok_clean.py --workspace <WS>
```

預設讀取 `<WS>/02_clean/nsfw/` 全部圖片，以及 `<WS>/02_clean/codex_clean/rejected.json` 中僅 `"handoff": "grok"` 紀錄列出的 `<WS>/02_clean/sfw/` 圖片。一般拒收（`not_present`、`low_quality`、`lineart_or_monochrome`、`crop_failed`、`text_removal_distorted`、`refused`）不再複查。逐張連同角色設定圖複製至 `grok_clean/.grok_clean_*/` 隔離目錄，以圖片檢視工具開啟兩圖並比對確認角色，透過 Grok Build CLI（`image` profile：只有 read_file、image_edit，無 shell／寫檔）依第 4 步標準清理；Grok 以 structuredOutput 回傳判定、`output_file`（image_edit 的 session 圖，或空字串代表沿用原圖）與 0–1 比例的 `crop`，裁切由腳本以 PIL 完成。需要時可用 `python -B scripts/wdtag.py --model-dir <ENV>/models/wd-eva02-large-tagger-v3 <WS>/02_clean/nsfw/<檔名>` 查看 tag。可疑內容（例如外觀未成年的性化圖片）直接排除，寫入 `grok_clean/suspicious.json` 並列給使用者。

腳本也會將 `codex_clean/*.png` 複製至 `collected_sfw/`。原先來自 `nsfw/` 的圖片通過後一律存入 `collected_nsfw/`，不因 Grok 的 rating 改送 Codex；Codex 交接圖則依 Grok 的 rating 存至 `collected_sfw/` 或 `collected_nsfw/`。步驟 05 以 `collected:nsfw=` 傳入後者，編號後存於 `images_nsfw/`，不進入 Codex 打標資料夾。

預設 `--model grok-4.7 --timeout 3600 --retries 2`；`--sheet` 預設 `<WS>/03_sheet/character-sheet.png`；可覆寫 `--target`、`--nsfw`、`--sfw`、`--codex-clean`、`--out`、`--collected-sfw`、`--collected-nsfw`。`--only <檔名...>` 重跑指定圖片，`--dry-run` 只列計畫。輸出與呼叫紀錄位於 `<WS>/02_clean/grok_clean/`：`summary.json`、`rejected.json`、`suspicious.json`、`failed.json`、`logs/`。後續 Codex 腳本不再進行 SFW 檢查。
