# 02. 清理

順序：去重 → WD Tagger 分流（Grok VM 本機）→ SFW 給 Codex 清理 → NSFW 與 Codex 拒絕／失敗者由 Grok 處理。

## 1–2. 去重與分流（不呼叫 Codex）

```
python3 scripts/dedup_split.py <清理資料夾> codex=<收集資料夾>/codex grok=<收集資料夾>/grok
```

- sha256 去掉完全相同的圖，再用 pHash（距離 ≤ 6）去近似圖，保留面積大的。
- WD Tagger（`wd-eva02-large-tagger-v3`，CPU；路徑 `--model-dir` 或 `WD_TAGGER_DIR`）的 rating：`general`、`sensitive` → `sfw/`；`questionable`、`explicit` → `nsfw/`。
- 輸出 `dedup/`、`sfw/`、`nsfw/`、`dedup.json`、`rating.json`。

## 3. Codex 清理 SFW

```
python3 scripts/codex_clean.py "<作品名> <角色名>" <清理資料夾>/sfw <清理資料夾>/codex_clean
```

一次隔離 `codex exec`（預設 `gpt-6.1-sol`、effort `high`、可用圖像生成去字）。Codex 依角色名與整包圖判斷角色長相：先 8 張一組拼圖初篩（角色在不在、線稿／黑白、太糊；拿不準開原圖），再逐張處理：角色檢測、品質檢查、剔除線稿與黑白圖、裁到只剩目標角色、去文字／對白框／浮水印並與原圖比對。

輸出清理後的圖、`summary.json`（檔名對照）與 `rejected.json`（問題圖與原因：角色不在、品質過低、線稿或黑白、裁切失敗、去字走樣、拒絕處理）。

## 4. Grok 處理

`nsfw/` 的圖，以及 `rejected.json` 中 Codex 拒絕處理或失敗的圖，由 Grok Bot 照第 3 步的標準處理（需要時用 `python3 scripts/wdtag.py <圖>` 看 tag）。可疑內容（例如外觀未成年的性化圖）直接排除並列給 使用者。

清理後的收集圖 = Codex 清理輸出 + Grok 處理通過的圖（NSFW 另放一個資料夾，05 的 `build_train_set.py` 以 `collected:nsfw=` 傳入，放到 `<訓練資料夾>_nsfw/`，不進 Codex 打標資料夾）。之後的 Codex 腳本不再做 SFW 檢查。
