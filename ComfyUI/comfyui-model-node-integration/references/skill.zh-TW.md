# 將上游模型整合至 ComfyUI

建立最精簡的原生節點組合，同時保留上游模型的功能與品質。

## 核心原則

- 以第一手資料確認目標 ComfyUI API、上游版本、權重、支援功能及可執行的官方基準。
- 許可證審查與合規由使用者人工處理，不屬於 Agent 工作範圍。不可研究、推斷、驗證或修改許可證；使用者提供的許可證檔案與 Metadata 只能原樣保留。使用其他包裝或研究 Skill 時也適用此排除規則。
- 除了有版本號的 `comfy_api` Namespace，以及重現結果所需的固定上游／模型 Revision 外，其他相依套件預設以最新正式版為目標並實際測試。避免過時 Pin 及不必要的上限；`pyproject.toml` 應盡量只使用最低版本 `>=`。優先修改 Adapter 或上游相容性 Fork，主動消除 `<` 或 `!=`；只有無法安全相容、已重現失敗且記錄原因時才能保留。
- 以目前 ComfyUI Runtime 的相依套件為準。官方上游推理套件或 SDK 若與最新版 ComfyUI 衝突，且無法用小型 Adapter 解決，只能 Fork 發生衝突的上游套件並進行最小相容性更新；不可為了遷就上游而 Fork 或修改 ComfyUI。保留模型行為，並與官方實作進行品質對等驗證。
- 優先使用 ComfyUI 原生型別及既有的載入、Conditioning、Sampler、Schedule、Codec、預覽與儲存節點；只有模型專屬工作才新增節點。
- 先建立 Capability Matrix，再決定 Node Surface；只有使用者能有意義地編輯、分支、替換、檢視或重用的階段才拆成節點，不要把每個上游函式都包成 Node。
- 上游參數語意相同時，沿用 ComfyUI 既有的輸入名稱、含義、預設值、範圍、Widget 與 Socket 型別；不要新增別名，也不要為了外觀一致而錯用原生名稱。
- 已發布的 Node ID、Input ID、Output Type 與 Output 順序必須保持穩定；顯示調整應使用 Display Name 或 Search Alias，不可暗中破壞既有 Workflow。
- Diffusion 或 Flow 模型只要更新方程與 Tensor 契約相容，就使用原生 `MODEL`、`CONDITIONING`、`LATENT`、`GUIDER`、`SAMPLER`、`SIGMAS` Graph；只自訂不相容的部分。
- 上游方法無法由核心 Provider 重現時，可以且應該新增自訂 Sampler 或 Schedule Provider Node；優先輸出原生 `SAMPLER` 或 `SIGMAS`，以便與 ComfyUI 採樣執行器組合。
- 使用 Lazy Load，並遵循 ComfyUI 的模型路徑、DType／裝置、記憶體、快取、卸載、進度及取消機制。
- 對外部模型、設定、DType 及其他不在 Socket 中但會影響結果的狀態建立可重現的 `fingerprint_inputs`。區分 ComfyUI Data List 與 Tensor Batch；Lazy Branch 只能載入實際會使用的資源。
- 保留上游演算法。Socket 型別相容，不代表可以更改採樣數學、Conditioning、Tensor Layout 或解碼行為。
- 上游沒有相應的 Conditioning 路徑時，不宣稱支援編輯、Reference、Inpaint、Control 或格式轉換。
- 相依套件只能在安裝階段處理；禁止 `eval`、`exec`、程式碼混淆及 Runtime 套件安裝。可透過程式存取時，必須在使用者明確執行 Model Loader 且本地缺檔時，依固定 Revision 與檔案清單自動下載所需權重；驗證可用的 Checksum，以暫存目標寫入後再原子發布。取消或失敗不可留下看似有效的半成品。
- 模型必須透過 ComfyUI `folder_paths` 尋找，包含 `extra_model_paths.yaml` 設定的路徑；不可只寫死單一模型目錄，也不可另建一套路徑系統。所有路徑值都需在實際讀寫邊界重新驗證，不可信任 Combo Widget。
- 優先使用 Schema Description、英文 Input Tooltip、Label 及 Node Help；只有原生 Schema 無法表達必要互動時才加入 JavaScript。若使用前端程式碼，需測試最新 Frontend，必要時只宣告最低 `comfyui-frontend-package` 版本。
- UI 必須清楚指出使用者要改哪些欄位。對有不直觀參數的 Custom Node 加入簡短英文說明或 Workflow Note；沒有參數的 Plumbing Provider 保持精簡。必須使用自訂結構物件時，提供安全 Editor 及可讀 Preview，而不是要求使用者修改 Tensor Token 或不公開的 JSON。
- 提供多個可直接執行的 Workflow，涵蓋推薦流程及其他確實支援且已測試的模式或 Graph 組合；不能以只改參數的複製品湊數，也不能加入不支援的功能。
- 短版或限制 Token／Step／Frame 的生成只能當作 Regression Fixture，不是展示品質的證據。除了快測，還要使用上游預設或建議設定執行代表性完整案例，允許自然結束，並保留配對的官方／ComfyUI 產物。
- Repository README 必須以使用者為中心：先說能產生什麼、如何安裝、最短成功 Workflow 及要改哪些欄位，再說實作細節。密集 Schema 與 Metrics 放到獨立 docs；可檢視的媒體要提供標示清楚的官方／ComfyUI 配對展示，使用 GitHub 可播放格式並在瀏覽器確認實際呈現。
- README 中每個 Workflow 都必須可點擊；硬體、DType、Backend 與 Manager 路徑只有實際執行過才能宣稱支援，未測路徑及完整 Revision 細節放在獨立 docs。
- 不可為 Custom Node 自動化測試新增 GitHub Actions 或其他 Hosted CI Workflow。必要測試需在本機或由人工執行，並記錄指令、環境及結果。只有使用者明確要求時才能加入發布自動化。

## Checklist

### 上游與環境

- [ ] 記錄目標 ComfyUI／API 版本並檢查實際安裝環境。
- [ ] 盤點相依套件版本並測試最新正式版；持續調整 Adapter 或上游相容性 Fork，直到 `pyproject.toml` 能只使用最低版本 `>=`；任何無法移除的 Pin、`<` 或 `!=` 都需有可重現失敗及理由。
- [ ] 固定上游程式碼與模型版本並確認硬體需求。
- [ ] 官方上游推理套件或 SDK 若與目前 ComfyUI 衝突，先嘗試小型 Adapter；仍無法解決時只 Fork 該上游套件，不得 Fork ComfyUI，並將修改路徑與官方結果比對。
- [ ] 執行一次官方基準，列出明確支援與不支援的功能。
- [ ] 至少一個官方代表案例使用正常上游設定並自然結束；縮短或降低品質的案例明確標示為快速 Regression Fixture。
- [ ] 需要細節時閱讀 [upstream-audit.md](upstream-audit.md)。

### 節點設計與實作

- [ ] 將每項功能分類為：核心節點、必要 Adapter、必要 Custom Node 或不支援。
- [ ] Graph 邊界使用原生公開型別；模型私有狀態才使用自訂型別。
- [ ] 新增參數前先檢查當前核心節點 Schema；語意相同就共用標準參數契約，否則只新增最少且有說明的模型專屬參數。
- [ ] 保持 Node ID、Input ID、Output Type 與 Output 順序穩定；非破壞性的呈現調整使用 Display Name 及 Search Alias。
- [ ] Diffusion／Flow 必須比較 prediction、guidance、time／sigma、noise、solver 與 RNG 契約，等價時沿用當前 ComfyUI 採樣鏈。
- [ ] Sampler 或 Schedule 不同時，實作最小的自訂 Provider Node，輸出原生 `SAMPLER` 或 `SIGMAS`，並依上游更新規則驗證。
- [ ] 確認原生 Sampler、Schedule、Encoder、Decoder、Preview 及 Save 的數學與資料契約確實相容。
- [ ] 為外部模型、設定、DType 及其他可觀察狀態建立可重現的快取 Fingerprint；驗證相同輸入命中快取，相關狀態改變時正確失效。
- [ ] 區分 ComfyUI Data List 與 Tensor Batch，測試空的 Optional Input、單項、多項，以及支援的混合 Shape 或尺寸。
- [ ] 完成 Lazy Load、DType／裝置選擇、卸載、進度及取消處理；確認未選擇的 Lazy Branch 不會載入模型或持續占用 VRAM。
- [ ] 透過 `folder_paths` 註冊及解析模型分類，分別測試預設目錄與 `extra_model_paths.yaml` 額外路徑。
- [ ] 技術可行且具備存取能力時，依固定 Revision 及檔案清單實作由使用者觸發的首次權重自動下載；測試 Checksum 或 Metadata 驗證、暫存檔、原子發布、取消清理、Cache Hit、Offline、Gated、下載中斷及損壞檔案；不可行時明確說明手動放置位置與存取條件。
- [ ] 在實際讀寫邊界重新驗證模型與輸出路徑，包含 Combo 值及 `extra_model_paths.yaml` 位置。
- [ ] 確認 Import 與執行路徑不包含 `eval`、`exec`、程式碼混淆或 Runtime pip／conda／subprocess Installer。
- [ ] 為不直觀的 Node 與 Input 加入簡短英文說明及 Tooltip；只有原生 Schema 無法提供的互動才使用前端 JavaScript。
- [ ] 指出一般使用者只需修改的少數 Node 與 Widget，以原生說明或 Workflow Note 解釋；沒有參數的 Plumbing Node 不加重複 Note。
- [ ] 可編輯的模型專屬狀態無法使用原生型別時，提供穩定自訂物件、安全 Editor 與可讀 Preview，不要求使用者修改 Tensor Token 或不公開的 JSON。
- [ ] 需要細節時閱讀 [node-surface.md](node-surface.md)；涉及模型或權重載入時再讀 [runtime-integration.md](runtime-integration.md)。

### 驗證與發布

- [ ] 先測試節點註冊及可重現的中間資料，再測試完整生成流程。
- [ ] 使用相同版本、權重、輸入、Seed、DType、裝置及生成設定，執行相互配對的官方與 ComfyUI 測試案例。
- [ ] 執行前先定義中間資料與最終輸出的比較指標及通過門檻；所有差異都在門檻內才能判定通過。
- [ ] 昂貴生成採兩層證據：快速可重現 Regression Case，以及自然長度／正常品質的代表案例；不可把限制 Token、Step、Frame 或時間的 Fixture 展示成模型的正常結果。
- [ ] 測試宣稱支援的 DType、裝置、記憶體、卸載、取消及錯誤行為。
- [ ] 使用最新正式版相依套件與 Frontend 測試；以 `>=` 宣告實際測試的最低版本，並透過相容性修改盡可能消除 `<` 或 `!=`。
- [ ] 至少提供兩個可直接執行的 Workflow：推薦最小流程，以及真正不同的支援模式或實用組合；可編輯輸入需有標示並連接最終輸出。
- [ ] 註冊範例使其出現在 ComfyUI Template Browser；依目標 Frontend 與 Schema 開啟、檢視並實際 Queue 每個 Workflow，確認最終輸出；不能用只改參數的重複流程滿足數量。
- [ ] 確認套件、權重、程式碼與素材來源，並測試文件中的安裝方法。
- [ ] 在乾淨環境安裝建置產物，測試安裝、更新、移除、Backend 註冊及宣告的 Frontend 相容性，且不可修改 ComfyUI Core。
- [ ] GitHub Actions 及其他 Hosted CI 不包含 Custom Node 自動化測試；改為保留可重現的本機測試指令及結果。
- [ ] 按照 [readme-template.md](readme-template.md) 撰寫 Repository README，每個必要章節都必須使用已驗證的專案資料。
- [ ] 在目標瀏覽器開啟已發布或本地 Render 的 README，確認相對連結、媒體播放、配對標示及折疊區；被 `.comfyignore` 排除的開發證據仍需能從 README 指向的位置取得。
- [ ] 宣稱品質對等或 Manager／Registry 相容前，閱讀 [validation-and-release.md](validation-and-release.md)。

## Definition of Done

每個適用項目都有直接證據後，才能宣告 Node Pack 完成：

- [ ] Capability Matrix 連結官方上游 Repository，並列出支援、可由 ComfyUI 組合、外部及刻意不支援的功能。
- [ ] 最終 Node Map 列出每個 Custom Node、穩定 Schema，以及可與其組合的 ComfyUI 原生 Node 與型別。
- [ ] 建置套件可在乾淨環境以最新已測相依套件安裝，註冊時沒有錯誤，且不修改 ComfyUI Core。
- [ ] 每個隨附 Workflow 都從 `example_workflows` 出現在 Template Browser、成功 Queue，並產生文件描述的最終輸出。
- [ ] Runtime 證據涵蓋模型尋找、`extra_model_paths.yaml`、自動下載或手動替代、Lazy Branch、Fingerprint、List／Batch、支援的 DType／裝置、記憶體釋放、取消及可操作的錯誤訊息。
- [ ] 可重現的官方上游／ComfyUI 比較報告記錄 Revision、權重、輸入、Seed、設定、硬體、指標、門檻、Hash 或產物，且所有必要比較都在預先定義的容許範圍內。
- [ ] Parity 證據包含快測，以及每個實質不同模式的正常輸出代表案例；展示產物不能為了加速測試而刻意縮短。
- [ ] README 遵循 [readme-template.md](readme-template.md)，能引導第一次使用者從安裝到執行 Template，將實作雜訊留在 docs，並涵蓋原始 Repository、專案目標、包裝方法、Node、Workflow 與官方／ComfyUI 結果。
- [ ] 媒體配對標示清楚，且在適用時可直接從 Render 後的 README 播放或檢視；完整 Metrics 放在 Validation Report，不干擾 Quick Start。
- [ ] 必要測試已在本機或由人工執行並保留證據；Repository 不含用於 Custom Node 自動化測試的 GitHub Actions 或其他 Hosted CI Workflow。
- [ ] Release Artifact、安裝說明及任何 Registry／Manager 狀態都經過直接測試，不可只根據 Source Tree 執行或上傳成功推定。

ComfyUI API 近期有變動時使用 `comfyui-research`；檢查既有環境時使用 `comfyui-inventory`；範例 Workflow 使用 `comfyui-workflow-skill`；發布使用 `comfyui-node-packaging`。發布、Push、Fork、大型下載與加入其他模型都需要使用者明確授權。
