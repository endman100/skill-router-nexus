# 透過 LinkingAI Chrome 完成 X 共用連線

本文件歸入「Bot 管理」分類，供重新部署 X 個人監控或設定其他 Bot 時參考。

以已授權的使用者任務為範圍，先使用 LinkingAI 接上指定電腦的 Chrome，再完成 OpenMausBot 與 X 的 OAuth。完成條件包含連線已登入、實際帳號核對與私人書籤成功讀取。使用者要求全體 Bot 共用時，保留全體 Bot 的使用權。

## 準備參數

從目前任務取得目標電腦、X 帳號與分享範圍。從 OpenMausBot 現有連線取得連線名稱與授權設定。現有 X 應用程式可沿用時直接使用。僅在需要時建立應用程式。

部署時記下指定電腦、預期的 X 帳號與數字 ID、應用程式名稱及獲准的 Bot 共用範圍。連線名稱可沿用 `x-bookmarks-read`，網址為 `https://api.x.com/mcp`。回呼網址以目前安裝的 OAuth 設定所顯示的完整網址為準。

## 1. 先以 LinkingAI 接上指定 Chrome

使用 https://mcp.lyfiai.com/mcp 已連線的 LinkingAI。

1. 目標電腦或 boot_id 未知或已過期時，呼叫 list_machines，取得指定電腦當前的 machine_id 與 boot_id。
2. chrome_use 名稱或參數 schema 未知時，以 list_methods 查詢 chrome_use。已知時直接 call_methods。
3. 以 call_methods 執行 chrome_use，先確認 status，再列出 tabs。沿用使用者指定 Chrome 的既有登入狀態。
4. 選定 tabId，attach 後 snapshot。以最新 pageId、元素 ref 操作，每次導覽或畫面變化後檢查結果。
5. 在 Chrome 的 X 頁面確認登入帳號。授權頁也要再核對帳號。

本流程使用使用者指定且已授權的 LinkingAI Chrome。若環境要求切換電腦，按當回合提供的正式選擇方式完成切換。操作前用一句話說明正在指定電腦的 Chrome 工作。

## 2. 設定 X OAuth 應用程式

在指定 Chrome 開啟 https://console.x.com/，確認開發者帳號正確。進入 Apps，沿用適用應用程式，或按任務需要建立一個名稱清楚的應用程式，再開啟 OAuth 2.0 設定。

本次書籤唯讀用途使用：
- App permissions 選 Read。
- Type of App 選 Native App / Public client。
- Callback URI / Redirect URL 填 OpenMausBot 此連線實際使用的完整回呼網址。
- Website URL 填應用程式的真實專案網址。本次使用 https://github.com/milind-soni/OpenMausBot。
- 儲存後取得公開的 Client ID。

從 X Developer Console 的 Client ID 欄位取得公開值，確認非空後填入連線設定。秘密值由平台的安全儲存機制處理。

## 3. 設定 OpenMausBot 共用連線

透過 mcp_server 的 list 檢查是否已有連線，再以 add 或 update 設定：
- name 為任務選定的連線名稱。
- type 為 http。
- url 為 https://api.x.com/mcp。
- oauth.clientId 為剛取得的實際 Client ID。
- oauth.scopes 為 tweet.read、users.read、bookmark.read、offline.access。

啟用連線，讀回確認 enabled。分享範圍依使用者要求設定。使用者已允許全體 Bot 時，沿用全體共用。

## 4. 在指定 Chrome 完成授權

1. 在同一部電腦的 Chrome，開啟使用者已登入的 OpenMausBot 網頁。
2. 進入側欄「應用程式」中的 MCP 伺服器清單，找到正確連線，按「登入」。此步會由 OpenMausBot 產生帶有 state 與 PKCE 的 OAuth 請求。
3. 若登入按鈕位於對話框下方，先捲動清單讓按鈕完整可見，再點擊。
4. 列出 Chrome 分頁，找到新開的 x.com/i/oauth2/authorize，attach 後 snapshot。
5. 核對應用程式名稱、X 帳號與要求的書籤讀取權限，依使用者原有授權按「授權應用程式」。
6. 若 OpenMausBot 自動收到回呼，直接檢查登入結果。
7. 若 Chrome 與 OpenMausBot 主機位於不同電腦，而 OpenMausBot 畫面提供「重新導向網址」與「完成登入」，使用平台提供的手動回填方式。從授權後 Chrome 的網址列取得完整回呼網址，核對其回呼目的地，將它直接填入同一筆登入流程的「重新導向網址」，按「完成登入」。

回呼網址中的 code 與 state 只用於該筆登入流程。處理時保留在操作資料內，對話、日誌、文件與截圖中省略這些值。使用 OpenMausBot 產生的原始 OAuth 流程與官方回填欄位完成交換。

## 5. 驗證實際帳號與書籤

1. 以 mcp_server list 讀回連線，確認 enabled 且 signed-in。
2. 以 test 確認功能清單包含 get_users_me 與 get_users_bookmarks。
3. 若新功能在下一回合載入，接續原工作，沿用已完成的授權。
4. 實際呼叫 get_users_me，取得 id、name、username，核對使用者指定帳號。
5. 呼叫 get_users_bookmarks，id 使用剛核對的數字字串，max_results=100。依當前 schema 取得貼文 id、text、created_at，expansions 包含 author_id，user.fields 包含 id、name、username。
6. 依 meta.next_token 傳入 pagination_token，讀取到末頁。確認回應成功，記錄本次筆數。
7. 報告授權與實測結果。若只完成授權，清楚標示書籤實測尚待完成。

## 6. 任務包含監控時

沿用現有自動化與已見 ID 清單，以共用連線核對帳號並讀取完整書籤。用貼文 ID 去重，成功後合併已見 ID，以同目錄暫存檔原子更新。照使用者要求回報新增，有新增才發摘要。

只有任務包含排程調整時才更新自動化。讀回確認使用新連線、原排程仍啟用、下次執行時間正確。本次實例每天台灣時間 00:00、12:00 執行，cron 為 0 0,12 * * *，時區 Asia/Taipei。

## 7. 重新部署 X 個人監控

部署時依序完成以下項目，每一步讀回實際結果。

1. 先確認新安裝可以使用 LinkingAI，連線網址為 https://mcp.lyfiai.com/mcp。透過 OpenMausBot 的應用程式管理介面新增或沿用連線，完成所需登入，取得目標電腦目前的 machine_id、boot_id。確認 Chrome 擴充功能已連線且能列出分頁。需要安裝或配對時，使用 LinkingAI 當前提供的安裝指引完成，再驗證 status。此文件實測環境已具備 Chrome 連線。
2. 經由有權限的 Bot 管理流程建立或恢復 X 個人監控，記下新 botId。恢復使用者指定的長期指示，包括使用台灣繁體中文、每 12 小時查書籤、有新增才回報。以新安裝目前的應用程式設定讀回模型、執行位置與共用連線的可用範圍。
3. 讀回 x-bookmarks-read 的設定及登入狀態。狀態正常時先實測帳號與書籤；需要授權時依本指南第 2 至第 5 節操作。新安裝的回呼網址依實際登入流程取得，並在 X Developer Console 登記相同值。既有公開 Client ID 可依同一應用程式的設定沿用。
4. OAuth 憑證由 OpenMausBot 管理。跨主機搬遷依該安裝的正式安全匯出／還原功能處理；需要登入時，在指定 Chrome 重新走 OAuth。可分享的部署指南記錄公開參數與步驟。
5. 搬移已見書籤 JSON 到新 Bot 的持久資料夾，確認 account_id、username 與 ids 能解析，且帳號吻合。同步更新自動化指向的絕對路徑。從舊自動化的設定取得原本的絕對路徑，搬移該路徑下最新的 `x_bookmarks_seen.json`。本次成功驗證後，歷次已見 ID 合併為 100 筆，當下 X 書籤為 99 筆。
6. 讀回新 Bot 的既有自動化，沿用適用的同一筆設定；需要建立時，在正確 Bot 上建立一筆。設定 cron 為 0 0,12 * * *，timeZone 為 Asia/Taipei，使用已授權共用連線，指向第 5 步的持久清單。執行位置依新安裝設定選擇。
7. 每次檢查先呼叫 get_users_me 核對指定帳號，再讀完 get_users_bookmarks 全部分頁，以字串 ID 比對。完整成功後合併已見 ID，原子更新清單。有新增時回報作者、一句摘要及貼文連結；沒有新增保持安靜。帳號、讀取或資料解析出現錯誤時，向使用者回報具體原因並保留原清單。來源清單確定不存在時，第一次完整成功讀取僅建立基線。
8. 部署驗收應包含實際帳號回應、書籤筆數與末頁確認、已見清單解析與差集結果，以及自動化 enabled 與 nextRunAt 的讀回。將下一次執行時間換成台灣時間告知使用者。排程實際執行後，從執行紀錄核對結果。

共用範圍依使用者授權設定。本指南實測的是書籤讀取與持續登入。

本指南的 OAuth、帳號核對、完整書籤讀取與自動化設定均來自本次成功操作。跨新主機部署的部分提供復用步驟，實際新部署依上述驗收結果確認。

## 來源

- 來源文件《X共用連線授權指南.md》由 X 個人監控整理，記錄 2026-11-19 至 2026-11-20 的實測。OpenMausBot 讀回 `signed-in`，`get_users_me` 核對指定帳號，`get_users_bookmarks` 成功讀到 99 筆且無下一頁。
- Cursor 官方 X 外掛設定 https://github.com/cursor/plugins/blob/50b3a3234bf2e0293849a48784d72030948e44ee/third_party/x/mcp.json
- X 書籤文件 https://docs.x.com/x-api/posts/bookmarks/introduction
- 本安裝 OpenMausBot 的共用連線設定、登入頁面及回呼網址回填介面。
