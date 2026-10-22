# 08. 發布到 Civitai

路徑依 [00_workspace.md](00_workspace.md)；`<WS>` 為本案 workspace，發布資料皆存於 `<WS>/08_release/`。

每個角色固定一個 model page，每次重新訓練都在該 model 下新增 version。上傳一律存為草稿，由使用者審閱後自行按 Publish；代理不得公開發布或排程發布，展示貼文亦同。

## 選定 checkpoint 與打包

checkpoint 由訓練者（使用者）看完 07 的對照圖後自行選定，代理不代為決定。選定的 `<WS>/06_train/models/` checkpoint 檔名記錄於 `<WS>/project.json` 的 `release_ckpt`（例如 `takane_yasuko-000015.safetensors`），保留 project.json 的其他欄位。

透過 Grok Bot 對 endmanHome 的機器連線，在 endmanHome 從本技能資料夾執行（僅使用 Python 標準函式庫），先 `--dry-run` 再正式執行：

```bash
python -B scripts/civitai_release.py --workspace "<WS>" --dry-run
python -B scripts/civitai_release.py --workspace "<WS>"
```

- 所有路徑由 `--workspace` 推導；腳本純本機執行，不連網、不上傳。`--dry-run` 讀取 checkpoint 與 metadata、計算 sha256 並列出打包結果，不建立目錄、不複製、不寫檔。
- 正式執行將選定 checkpoint 以原檔名複製至 `08_release/`，核對副本 sha256，寫入 `release.json`：角色資料、`release_ckpt`、`checkpoint`（來源、檔名、sha256、大小）、`generation` 與 `civitai`。
- `generation.reconstruction`／`generation.scenario` 分別取自 `07_validate/reconstruction/` 與 `07_validate/scenario/` 的 `test_meta.json`：以 `images[].lora_file` 篩出所選 checkpoint 的紀錄（不混入 base 或其他 checkpoint），保留各圖 prompt、seed 等資訊與頂層共用參數（07 的實測參數；腳本不讀取 workflow 內容）。只以 metadata 參照圖片，不複製。
- 任一 test_meta.json 缺少、缺必要欄位或沒有所選 checkpoint 的紀錄時，列出錯誤並停止。沿用同一 sha256 重跑會保留已填的 `civitai` 紀錄；改選不同 sha256 時清空本次版本紀錄，描述檔不受影響。
- 腳本也會將所選 checkpoint 的展示圖與 `showcase_manifest.json` 複製至 `08_release/showcase/`；`showcase_change/` 不存在時沿用舊版 `showcase/`，任一展示圖變體缺少來源目錄或 `test_meta.json` 時僅警告並繼續。

## 描述文字

由 Antigravity（`gemini-3.8-flash-high`）依 project.json、release.json 與 07 的驗證結果撰寫，存至 `08_release/model_description.md` 與 `08_release/version_description.md`：

- 模型名稱：Civitai 的 model Name（標題）只用英文，格式 `[<Base Model>] <Anime English name>: <Character English name>`，例：`[Anima] FX Senshi Kurumi-chan: Takane Yasuko`。
- 模型描述：依 [templates/civitai_description.tmpl.md](templates/civitai_description.tmpl.md) 的結構輸出，填入各 placeholder；Langfuse 的 `{{...}}` 變數保持原樣。
  - 只用英文；不含 negative prompt、中文、Showcase 段落、`detailed background, detailed scenery` 或 `8K`。
  - 段落順序：H1 標題（同時列出作品與角色的英文名稱與日文原名）→ `Usage` → `Prompt structure` → `Trigger words` → `Keep the default outfit` → `Change the outfit`。
  - `Usage`：trigger word；建議 LoRA strength；底模；測試時使用的 sampler、scheduler、cfg、steps 與解析度（取自 release.json 的 `generation`）。
  - `Prompt structure`：以程式碼區塊列出 Langfuse prompt 範本 `masterpiece, best quality, highres, ultra detailed, <trigger>, {{character_features}}, {{cloth_feature}}, {{other}}`，並簡述變數：`character_features` = 角色外觀 tag 組；`cloth_feature` = 預設服裝 tag 組或使用者自訂服裝；`other` = 姿勢／構圖／場景。
  - `Trigger words`：編號 1–3，各自一個程式碼區塊：`<trigger>`、完整角色外觀 tag 組、完整預設服裝 tag 組，供使用者直接複製；與版本 Trigger Words 的三項一致。
  - `Keep the default outfit` 與 `Change the outfit`：各一句說明加一個範例程式碼區塊；範例 prompt 由 `showcase_manifest.json` 的實際 prompt 精簡，順序：品質 tags → `<trigger>` → 角色外觀 → 服裝 → 其他。tag 組不以 trigger 開頭。
- 版本說明（version changelog）：第一版固定為 `This is the first version.`；後續版本說明本次 checkpoint、訓練／驗證結果與 release.json 的生成設定。

## 網頁上傳

### 1. 傳輸與瀏覽器
- 主要路線：將 `08_release/` 的 checkpoint 副本從 endmanHome 複製到 box（Grok Bot 自己的電腦），再用 box 的瀏覽器上傳；box 瀏覽器已登入使用者的 Civitai 帳號，若未登入則停止並請使用者登入。
  - 前提：box 的 LinkingAI agent 須在線，以 `/workspace/linkingai-agent/start.sh` 搭配 `watchdog.sh` 啟動；離線時以帳號 token 重新註冊（re-enroll）。box 於 `list_machines` 顯示為 `grokbot-box`。
  - 在來源機器（endmanHome）以 `call_methods` 呼叫 `file_transfer`，例如：`{action:'start', transfer_id:<32 位小寫 hex>, source_path:'<WS>\\08_release\\<ckpt>.safetensors', target_machine_id:<box id>, target_path:'/workspace/uploads/civitai/<trigger>/<ckpt>.safetensors', mode:'copy', overwrite:false}`。可直接讀取 `D:\`；`transfer_id` 可省略，但指定時重送較安全。
  - 以 `{action:'status', transfer_id}` 輪詢（每次使用新的 `request_id`）至 `completed`；來源端計算雜湊時 bytes 可能維持 0 約 1 分鐘，屬正常現象。
  - 完成後執行 `chmod 644`（傳入時為 600），並核對 sha256 須與 `release.json` 的 `checkpoint.sha256` 相符，不符則停止。
  - `08_release/showcase/` 的展示圖與 `showcase_manifest.json` 以同樣方式傳到 box 的 `/workspace/uploads/civitai/<trigger>/showcase/`（可先打包成不壓縮的 zip）。
  - 備援傳輸：`file_transfer` 不可用時，複製到使用者設定檔 Temp、以 PowerShell 切成 ≤ 90 MiB 的 `<name>.partN`、用 CopyToBox 傳到 `/workspace/uploads/civitai/parts/`、`cat <name>.part* > <name>` 合併（10 段以上須明確列出順序），合併後同樣核對 sha256。
- 備援路線：使用使用者的 LinkingAI MCP 找出已登入 Civitai 的主機（預設 endmanHome），操作該主機自己的 Chrome（`chrome_use`；原生檔案選擇器用 `computer_use` 的真實點擊）。上傳前確認 `08_release/` 的 checkpoint 副本 sha256 與 `release.json` 的 `checkpoint.sha256` 相符。
  - 檔案選擇器只會在前景、獨立視窗的作用中分頁以真實點擊開啟（可用 `chrome.exe --new-window <url>` 開獨立視窗）；輸入路徑前確認檔案對話框是前景視窗（桌面焦點可能被使用者搶走）。

### 2. Wizard 步驟（https://civitai.com/models/create）
1. **模型頁判斷**：讀取 `project.json` 的 `civitai_model_id`／`civitai_model_url`。跨 workspace 重新訓練同一角色時，沿用該角色原有的 model ID／URL（不可只看本 workspace 的 `project.json`，否則會重複建立模型頁）。
   - **新角色**（尚無 `civitai_model_id`）：在 Step 1 Create your model 建立 model page：Name 依「描述文字」的模型名稱格式填寫、Type=LoRA、Category=Character、Description、Depicts an actual person=No、勾選 Acknowledgement；按 Next 後模型即以 Draft 建立（網址變為 `/models/<id>/wizard?step=2`），之後可從 model page 編輯名稱與描述。
     - **Tags**：`anime`、`anima`、`<character 小寫>`、`<anime 小寫>`、`woman`。
     - **License**：選最開放的授權，勾選全部權限：Use without credit、Share merges、Different permissions on merges、Sell generated images、兩種 generation services、Sell model、Sell merges。內容標記維持不變。
   - **已有 `civitai_model_id` 的角色**：從既有 model page 新增 version。
2. **Add version（Step 2）**：填寫版本名稱、Base Model = Anima、Epochs 等；版本說明（changelog）依「描述文字」的版本說明填寫。Trigger Words 依序逐一輸入本案 trigger、完整角色外觀 tag 組與完整預設服裝 tag 組，每項輸入後都選擇下拉選單的「+ Create <輸入內容>」，絕不按 Enter（Enter 會直接送出步驟並清空 trigger、開啟「This version doesn't require any trigger words」；逗號也不會分隔）。按 Next 進入 Step 3。
   - 版本建立後，在 version 編輯頁（非 model 編輯頁）關閉「Require users to be logged in to download」。
3. **Upload files（Step 3）**：主要路線選取 box 上 `/workspace/uploads/civitai/<trigger>/` 的副本，備援路線選取 endmanHome 上 `08_release/` 的副本，等待進度完成並核對檔名。
4. **展示貼文（Step 4 Create your post）**：
   - 按 Next 進入「Create your post」，貼文標題留空，貼文說明填 `Showcase for <Character> (<Anime>) <Base Model> LoRA <version>.`，加入 16 張展示圖（主要路線用 box 上 `/workspace/uploads/civitai/<trigger>/showcase/`，備援路線用 endmanHome 的 `08_release/showcase/`）。
   - 上傳順序：先上傳全部 8 張 keep 圖（`keep_c00`…`keep_c07`），處理完成後再上傳全部 8 張 change 圖（`change_c00`…`change_c07`）；此順序與 `showcase_manifest.json` 的清單順序不同，以本步驟為準。上傳後確認貼文中的圖片依此順序顯示，不符先調整再離開。
   - 依 `showcase_manifest.json` 為每張圖填入各自的 prompt、seed、cfg、steps 與 sampler；Civitai 沒有 `er_sde`，sampler 改選 `DPM++ 2M SDE`；negative 留空。Civitai 不會自動讀取 ComfyUI 的 prompt。
   - 絕不按 Publish 或 Schedule；貼文維持隱藏，模型維持草稿，之後直接離開頁面。wizard 沒有 Save as Draft 按鈕。展示貼文一旦發布，會連帶發布模型與版本。
5. **確認草稿**：打開 `https://civitai.com/models/<id>` 確認 Details 顯示 Draft、Base Model Anima、Trigger Words、檔案。

### 3. 常見陷阱
- **角色年齡標記**：「Intended to depict a minor character」欄位須由使用者確認。
- **Model tags**：Civitai 會刪除 tag `girl`，也不接受 `character` 作為 tag。

### 4. 完成後寫回
依下表將 ID、URL 與狀態寫回 `project.json` 與 `release.json` 的 `civitai` 區段，保留其他欄位與格式，寫完重新解析 JSON 驗證。將草稿連結交給使用者，由使用者審閱後自行按 Publish。

| 位置 | 欄位 | 寫入時機 |
|---|---|---|
| `<WS>/project.json` | `civitai_model_id`、`civitai_model_url` | 模型頁建立後寫入；之後固定沿用 |
| `<WS>/08_release/release.json` 的 `civitai` | `version_id`、`version_url` | 本次版本建立後寫入網頁取得的 ID 與 URL |
| 同上 | `version_status`、`showcase_status` | 本機打包時為 null；`version_status` 確認草稿後填 `Draft`；`showcase_status` 未建立貼文填 `none`、已建立未發布填 `Draft` |
