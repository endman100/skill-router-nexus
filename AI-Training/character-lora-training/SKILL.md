---
name: character-lora-training
description: >-
  從作品名與角色名開始，收集、清理並生成角色圖片資料集，使用 Codex 逐張打標，再訓練 Anima 角色 LoRA。
  適用於為動畫角色從零建立 LoRA 訓練資料集、打標（caption）或訓練角色 LoRA 時。
---

# 角色 LoRA 訓練

## 輸入

作品名、角色名、trigger（小寫底線，例 `takane_yasuko`，亦為 LoRA 檔名）。選填：參考圖、生成張數 N（預設 30）。

## 必守規則

- Codex 不得接收任何 NSFW 圖片或文字；NSFW 僅由 Grok Build 腳本處理；Codex 永不接收 NSFW（分流於步驟 2 與 5）。
- 主助理只有在使用者確認角色設定圖之後，或使用者在對話中明確表示全自動（full auto）時，才執行 `approve-sheet`；預設由使用者手動確認。

Grok 步驟一律使用各步驟的 `grok_*.py` 腳本，透過已登入的 Grok Build CLI `/home/box/.local/bin/grok` 無人值守執行。共用預設為 `--model grok-4.7 --timeout 3600 --retries 2`；可用 `--grok-bin`、`--model`、`--effort`、`--timeout` 覆寫，`--dry-run` 只列計畫，不呼叫 Grok。權限一律最小化，集中在 `scripts/grok_headless.py` 的 `PROFILES`：每次呼叫在輸出資料夾下建立隔離 cwd `.grok_<步驟>_*/`（只複製該次需要的輸入），寫入沙箱 `lora_min`（strict + 禁讀 `/tmp/*`、`/var/tmp/*` + 限制子程序網路；`~/.grok` 登入資料仍可讀），加 `--tools` 白名單、`--disallowed-tools`、`--no-subagents`、`--max-turns`、deny 規則；Grok 一律不給 shell 與寫檔工具，結果只以 structuredOutput 回傳、圖片由腳本從 session 取出，所有寫檔由腳本完成。三種 profile：`read`（read_file、list_dir；dontAsk，用於 vocab、NSFW 打標、場景規劃）、`image`（read_file、image_edit；dontAsk + allow `*`，因 dontAsk 只放行 `*` 才能無人值守執行 image_edit，用於清理、生成、放大）、`web`（read_file、web_search、web_fetch；只用於收集）。除收集外皆停用網路搜尋，每次呼叫皆記錄 prompt、argv、stdout JSON、stderr 與 exit code，失敗不改寫要求繞過工具限制。

## 流程

複製此清單並逐步勾選。每一步驟先閱讀對應的 md 檔案，並依照其中的指令執行。

```
- [ ] 0. 建立 workspace
- [ ] 1. 資料收集
- [ ] 2. 去重、分流、三視圖與逐張清理
- [ ] 3. 三視圖（已於步驟 2 清理前產出）
- [ ] 4. 資料集生成
- [ ] 5. 整理訓練集與打標
- [ ] 6. LoRA 訓練
- [ ] 7. LoRA 驗證
- [ ] 8. 發布到 Civitai（存草稿）
```

0. **建立 workspace**：閱讀 [00_workspace.md](00_workspace.md)，先建立全新案例目錄；後續 `<WS>` 均指此目錄。
1. **資料收集**：閱讀 [01_data_collection.md](01_data_collection.md)。
2. **清理**：閱讀 [02_cleaning.md](02_cleaning.md)，依序去重 → WD Tagger 分流 → 依 [03_character_sheet.md](03_character_sheet.md) 生成三視圖、確認後執行 `approve-sheet` → 逐張 Codex 清理 SFW → Grok 處理 NSFW 與 Codex 交接圖。
3. **三視圖**：已移至步驟 2 分流後、清理前產出；沿用 [03_character_sheet.md](03_character_sheet.md) 與 `03_sheet/`，此處不重複生成。
4. **資料集生成**：閱讀 [04_dataset_generation.md](04_dataset_generation.md)。
5. **整理訓練集與打標**：閱讀 [05_captioning.md](05_captioning.md)。向使用者確認詞表時，每個英文／SDXL tag 旁附繁體中文翻譯。
6. **LoRA 訓練**：閱讀 [06_lora_training.md](06_lora_training.md)。
7. **LoRA 驗證**：閱讀 [07_lora_validation.md](07_lora_validation.md)。
8. **發布到 Civitai**：閱讀 [08_civitai_release.md](08_civitai_release.md)，打包使用者選定的 checkpoint，由有瀏覽器的代理上傳並存為草稿；由使用者審閱後自行發布。

`scripts/` 內的程式直接執行，不需要讀取內容；指令與參數寫在各步驟的 md 檔案中。`templates/` 則是打標用的 prompt 模板、欄位設定與 schema，以及驗證用的 workflow、prompt 模板與情境清單。
