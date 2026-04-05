---
name: skill-router-nexus
description: "⚠️ MANDATORY ENTRY POINT — You MUST read this file completely before accessing, querying, or loading any sub-skill. Do NOT load or look up any sub-skill directly. Every agent, every task, and every skill query must route through this file first. When agent is planning, reviewing, checking, or auditing tasks, always query this skill router to find the right sub-skill (especially Agent-Plan category). | ⚠️ 強制入口 — 所有 agent 在執行任務、查詢 skill 或新增 skill 之前，必須先完整讀取本檔並依照路由流程操作。嚴禁直接載入或查詢子 skill、嚴禁繞過本檔、嚴禁假設知識庫內容。當 agent 進行計畫規劃、計畫審查、檢查點、驗證完成等操作時，務必查詢此 skill router 以找到正確的子 skill（特別是 Agent-Plan 分類）。"
metadata:
  {
    "openclaw":
      {
        "emoji": "🧠",
      },
  }
---

# Skill Router Nexus — 強制路由器

> **⚠️ 注意：你正在讀的這個 skill 不是用來執行任務的。**
> 它的唯一職責是告訴你「如何正確找到並載入能執行任務的子 skill」。
> **在執行任何任務之前，你必須完整讀完此頁並嚴格依照以下流程操作。**

> **安裝與優先使用提醒：** 對於所有 agent 和 system prompt，必須優先讀取並路由通過此 skill-router-nexus。建議在 system prompt 中追加規則：'追加規則:對於任何 skill 存取、查詢或新增，永遠先讀取 skill-router-nexus。' 這確保技能操作的正確分類與載入，避免繞過入口點。

---

## 知識庫分類地圖

| # | 資料夾 | 英文名 | 說明 |
|---|--------|--------|------|
| 1 | `Agent-and-Workflow/` | Agent & Workflow | 此分類涵蓋 AI Agent 調度、多步驟任務執行、工作流自動化、子代理協作、以及與外部應用程式的連接整合。適用於需要規劃與執行複雜自動化流程、管理 Agent 生命週期、或串接多個服務完成端對端任務的場景。 |
| 2 | `Agent-Plan/` | Agent Plan | ⚠️ Agent 進行規劃、計畫、檢查、審核時必查此分類。此分類涵蓋計畫生成與執行、多視角審查（CEO/設計/工程）、自動審查管道、檢查點儲存與恢復、完成前驗證等 skill。適用於 Agent 需要規劃任務、審查計畫、設立檢查點、或驗證完成度的場景。 |
| 3 | `CI-CD-and-Monitoring/` | CI/CD & Monitoring | 此分類涵蓋持續整合與持續部署（CI/CD）管道、應用程式效能監控、錯誤追蹤、日誌管理、功能旗標控制、以及服務狀態監控。適用於需要自動化建置部署流程、即時追蹤系統健康狀態、或管理運維告警的場景。 |
| 4 | `Cloud-and-Hosting/` | Cloud & Hosting | 此分類涵蓋雲端基礎設施管理、伺服器部署、CDN 配置、容器管理、無伺服器資料庫、DNS 管理、以及雲端服務的自動化操作。適用於需要管理雲端資源、自動化部署流程、或監控基礎設施的場景。 |
| 5 | `Coding/` | Coding | 此分類涵蓋程式開發工作流程中的核心實務，包括測試驅動開發、系統化除錯、程式碼審查、Git 分支管理、Web 應用測試、MCP 伺服器建置、以及程式碼執行與分析。適用於需要遵循工程最佳實務進行軟體開發的場景。 |
| 6 | `Communication/` | Communication | 此分類涵蓋即時通訊、SMS/MMS 簡訊、語音通話、推播通知、以及團隊協作工具的自動化整合。適用於需要透過各種通訊管道發送訊息、管理對話、或整合多平台通訊的場景。 |
| 7 | `CRM-Platforms/` | CRM Platforms | 此分類涵蓋客戶關係管理（CRM）平台的自動化操作，包括聯絡人管理、交易追蹤、銷售漏斗管理、客戶互動記錄、以及 CRM 資料的同步與更新。適用於需要自動化銷售流程或統一管理客戶資料的場景。 |
| 8 | `Crypto-and-Market-Data/` | Crypto & Market Data | 此分類涵蓋加密貨幣交易、區塊鏈操作、股票市場數據查詢、金融指標分析、NFT 管理、以及即時行情追蹤。適用於需要存取金融市場資料、執行加密貨幣操作、或進行投資數據分析的場景。 |
| 9 | `Customer-Support/` | Customer Support | 此分類涵蓋客服工單管理、即時聊天支援、客戶對話自動化、幫助台系統、以及跨渠道客戶服務整合。適用於需要自動化客服流程、管理支援請求、或建置聊天機器人客服的場景。 |
| 10 | `Data-APIs-and-Enrichment/` | Data APIs & Enrichment | 此分類涵蓋各類數據查詢 API，包括地理編碼、天氣資訊、體育數據、新聞、電話驗證、身份查核、以及各種公開資料集的存取。適用於需要從外部數據源獲取結構化資訊來充實應用程式資料的場景。 |
| 11 | `Dev-Platforms-and-VCS/` | Dev Platforms & VCS | 此分類涵蓋版本控制系統、開發協作平台、低程式碼/無程式碼建置工具、套件管理、翻譯本地化、以及品質測試自動化。適用於需要管理程式碼倉庫、自動化開發流程、或使用視覺化開發工具的場景。 |
| 12 | `Document-Generation/` | Document Generation | 此分類涵蓋 PDF 生成與轉換、文件自動化產出、範本渲染、OCR 文字辨識、CMS 內容管理、以及各種文件格式（Excel、Word、PDF）的處理。適用於需要批量生成文件、轉換文件格式、或自動化文件工作流的場景。 |
| 13 | `E-commerce-and-Logistics/` | E-commerce & Logistics | 此分類涵蓋電商平台管理、產品目錄維護、訂單處理、庫存管理、物流配送追蹤、以及零售數據分析。適用於需要自動化電商營運、管理多平台店鋪、或優化配送流程的場景。 |
| 14 | `Email-Marketing/` | Email Marketing | 此分類涵蓋電子郵件行銷活動管理、自動化郵件序列、訂閱者名單管理、郵件範本建立、A/B 測試、以及行銷自動化流程。適用於需要設計與執行郵件行銷活動、管理行銷漏斗、或自動化客戶溝通的場景。 |
| 15 | `Email-Verification/` | Email Verification | 此分類涵蓋電子郵件地址驗證、信箱存在性檢查、郵件清單清洗、退信率降低、以及寄件者信譽維護。適用於需要在發送前驗證郵件地址有效性、清理過時名單、或提升郵件投遞率的場景。 |
| 16 | `Events-and-Scheduling/` | Events & Scheduling | 此分類涵蓋行事曆排程、活動管理、線上會議/網路研討會、預約系統、票務管理、以及場地規劃。適用於需要自動化預約流程、管理活動報名、或整合行事曆服務的場景。 |
| 17 | `Feedback-and-Survey/` | Feedback & Survey | 此分類涵蓋產品回饋收集、NPS 調查、客戶滿意度評分、功能請求管理、評論彙整、以及使用者意見分析。適用於需要系統化收集與分析用戶回饋、追蹤產品改善建議的場景。 |
| 18 | `Forms-and-E-Signatures/` | Forms & E-Signatures | 此分類涵蓋線上表單建立、資料收集、電子簽名、文件簽署工作流、問卷調查表單、以及憑證與通行證管理。適用於需要自動化表單處理流程、數位簽署文件、或收集結構化資料的場景。 |
| 19 | `GitHub/` | GitHub | 此分類專門涵蓋 GitHub 平台操作，包括 Issue 管理、Pull Request 工作流、CI 狀態查詢、程式碼審查、以及透過 GitHub CLI 進行的各種自動化操作。適用於需要直接與 GitHub 倉庫互動的場景。 |
| 20 | `Google-Services/` | Google Services | 此分類涵蓋 Google 生態系服務的自動化操作，包括 Google Drive、Google Calendar、BigQuery、Google Docs、Google Meet、Google Photos、以及 Google 搜尋控制台等。適用於需要整合或自動化 Google 套件服務的場景。 |
| 21 | `Health-and-Lifestyle/` | Health & Lifestyle | 此分類涵蓋健身追蹤、智慧家居控制、天氣查詢、遊戲平台整合、抽獎工具、捐款管理、以及環保公益相關服務。適用於需要整合生活類應用、管理健康數據、或進行休閒娛樂互動的場景。 |
| 22 | `HR-and-Education/` | HR & Education | 此分類涵蓋人力資源管理、招募流程自動化、薪資發放、員工入職、績效管理、線上學習平台、認證管理、以及會員制課程系統。適用於需要自動化 HR 流程、管理招聘漏斗、或建置教育內容的場景。 |
| 23 | `Knowledge-and-Productivity/` | Knowledge & Productivity | 此分類涵蓋筆記工具管理、任務清單與待辦事項追蹤、無程式碼資料庫建置、白板協作、儀表板視覺化、書籤管理、試算表資料庫、會議記錄分析、學習回顧、以及個人與團隊生產力工具整合。適用於需要組織個人或團隊知識資產、管理日常工作任務、或建置無程式碼資料管理系統的場景。 |
| 24 | `Image-and-Design/` | Image & Design | 此分類涵蓋圖片處理、壓縮最佳化、截圖擷取、圖庫搜尋、去背、浮水印處理、GIF 搜尋、圖片託管、以及設計素材管理。適用於需要批量處理圖片、管理視覺素材、或自動化圖片工作流的場景。 |
| 25 | `Image-Generation/` | Image Generation | 此分類涵蓋 AI 圖片生成、文字轉圖片、範本化圖片批量產出、橫幅廣告自動生成、以及創意視覺內容生成。適用於需要利用 AI 或範本快速產出圖片素材的場景。 |
| 26 | `Image-Recognition/` | Image Recognition | 此分類涵蓋電腦視覺、圖像分類、物件偵測、車牌辨識、圖片替代文字生成、AI 圖像增強、以及文件影像資料擷取。適用於需要從圖片中自動辨識與提取資訊的場景。 |
| 27 | `LLM-and-Chatbot/` | LLM & Chatbot | 此分類涵蓋大型語言模型 API 整合、聊天機器人建置、AI 推論服務、文字生成、RAG 檢索增強生成、AI 抄襲偵測、以及 LLM 應用開發框架。適用於需要呼叫 LLM API、建置對話式 AI 應用、或管理 AI 模型的場景。 |
| 28 | `Marketing-and-Growth/` | Marketing & Growth | 此分類涵蓋社群行銷工具、短網址服務、行銷分析、品牌資產管理、彈出式視窗、社交證明、直郵行銷、內容發布、以及成長駭客工具。適用於需要擴大品牌觸及、優化行銷漏斗、或管理多渠道行銷活動的場景。 |
| 29 | `Microsoft-Services/` | Microsoft Services | 此分類涵蓋 Microsoft 生態系服務的自動化操作，包括 Dynamics 365 CRM、SharePoint 文件管理、以及 Microsoft Clarity 網站分析。適用於需要整合或自動化 Microsoft 企業服務的場景。 |
| 30 | `Payments-and-Billing/` | Payments & Billing | 此分類涵蓋線上支付處理、訂閱管理、發票開立、記帳與會計、費用追蹤、稅務計算、以及收款自動化。適用於需要整合支付閘道、管理定期訂閱、或自動化財務帳務的場景。 |
| 31 | `PPT-Design/` | PPT Design | 此分類涵蓋簡報設計與製作，包括 HTML 動畫簡報、PowerPoint 生成與轉換、Google Slides 操作、簡報主題樣式設計、以及資料視覺化簡報。適用於需要自動化簡報製作或設計精美投影片的場景。 |
| 32 | `Project-Management/` | Project Management | 此分類涵蓋任務與專案管理、看板工作流、敏捷開發（Scrum）、工作排程規劃、服務工單管理、團隊協作工具、以及自由工作者專案追蹤。適用於需要管理團隊工作進度、協調多個專案任務、或追蹤服務交付流程的場景。 |
| 33 | `Sales-Intelligence/` | Sales Intelligence | 此分類涵蓋潛在客戶開發、B2B 數據挖掘、聯絡人資訊充實、銷售情報分析、提案工具、以及自動化外展序列。適用於需要發掘商機、充實潛客資料、或加速銷售流程的場景。 |
| 34 | `Search-and-Network-APIs/` | Search & Network APIs | 此分類涵蓋搜尋引擎 API、IP 地理定位、網路安全查詢、DNS 工具、OCR 光學文字辨識、驗證碼處理、密碼管理、以及各類公用網路服務 API。適用於需要整合搜尋功能、進行網路分析、或存取各類工具型 API 的場景。 |
| 35 | `Security-and-Compliance/` | Security & Compliance | 此分類涵蓋資訊安全工具、合規管理、隱私保護、安全稽核、舉報系統、身份驗證、以及郵件隱私代理。適用於需要確保系統安全性、符合法規要求、或管理安全事件的場景。 |
| 36 | `SEO-and-Web-Analytics/` | SEO & Web Analytics | 此分類涵蓋搜尋引擎優化分析、網站流量追蹤、競品分析、關鍵字研究、反向連結監控、社群媒體趨勢分析、以及內容行銷成效追蹤。適用於需要提升網站搜尋排名、分析用戶行為、或監測競爭對手動態的場景。 |
| 37 | `Social-Media/` | Social Media | 此分類涵蓋主流社群媒體平台（Facebook、Instagram、LinkedIn、Twitter、TikTok、YouTube 等）的自動化操作，包括貼文管理、廣告投放、影音上傳、以及社群互動追蹤。適用於需要自動化社群經營或管理多平台內容的場景。 |
| 38 | `Speech-Recognition/` | Speech Recognition | 此分類涵蓋語音轉文字（STT）、音訊轉錄、會議記錄自動化、字幕生成、以及多語言語音辨識。適用於需要將音訊或會議內容自動轉換為文字記錄的場景。 |
| 39 | `System-and-CLI/` | System & CLI | 此分類涵蓋系統監控、密碼管理、命令列工具、智慧家居控制、終端機管理、以及各類本地端系統操作工具。適用於需要透過 CLI 管理系統資源或自動化本機作業的場景。 |
| 40 | `Time-Tracking/` | Time Tracking | 此分類涵蓋工時追蹤與記錄、專案時間成本分析、生產力統計報告、帳單計費自動化、以及開發者程式碼時間統計（Wakatime）。適用於需要精確追蹤工作時間、分析時間分配效率、或根據工時自動產生帳單的場景。 |
| 41 | `TTS-and-Voice-AI/` | TTS & Voice AI | 此分類涵蓋文字轉語音（TTS）、語音合成、語音克隆、AI 語音代理、語音對話機器人、以及自然語言處理。適用於需要生成語音內容、建置語音互動介面、或進行文本分析的場景。 |
| 42 | `Video-and-Print/` | Video & Print | 此分類涵蓋照片托管與分享、3D 模型管理、數位翻頁書、名片與印刷品自動化、目錄網站建置、以及互動式展示板。適用於需要管理視覺媒體資產或自動化印刷品生產的場景。 |
| 43 | `Video-Editing/` | Video Editing | 此分類涵蓋影片下載、影格擷取、影片託管管理、以及影片串流處理。適用於需要下載、裁切、擷取影片片段、或管理影片內容的場景。 |
| 44 | `Video-Generation/` | Video Generation | 此分類涵蓋 AI 影片生成、虛擬人物影片、範本化影片製作、以及自動化影片剪輯與合成。適用於需要利用 AI 快速產出影片內容或建立虛擬主播影片的場景。 |
| 45 | `Web-Design/` | Web Design | 此分類涵蓋前端網頁介面設計、HTML 互動元件建置、低程式碼網站建構、視覺化設計到程式碼轉換、以及網頁原型製作。適用於需要快速設計與建置網頁介面或互動式 Web 應用的場景。 |
| 46 | `Web-Scraping-and-Browser/` | Web Scraping & Browser | 此分類涵蓋網頁爬蟲、資料擷取、瀏覽器自動化、代理 IP 管理、搜尋結果抓取、以及結構化資料提取。適用於需要從網站批量擷取資料、自動化瀏覽器操作、或建置資料採集管道的場景。 |
| 47 | `Writing-and-Content/` | Writing & Content | 此分類涵蓋腦力激盪、內容研究與撰寫、摘要生成、翻譯潤稿、命名發想、以及寫作計畫制定。適用於需要輔助內容創作、改善文案品質、或規劃寫作流程的場景。 |

> **新增 skill 時，必須按照下方「追加 Skill 流程」操作。**

---

## 分類判定規則（追加 Skill 時使用）

當需要將新 skill 歸類時，依照以下優先順序判斷：

1. **讀取 SKILL.md 內容**：從 description、body 關鍵字判斷功能
2. **平台歸屬優先**：若明確屬於某平台（GitHub → `GitHub/`、Google → `Google-Services/`、Microsoft → `Microsoft-Services/`）直接歸類
3. **功能歸屬次之**：根據核心功能匹配最接近的分類（例如「語音轉文字」→ `Speech-Recognition/`）
4. **若橫跨多類**：在所有相關分類中各放置一份，允許重複放置
5. **每個分類上限 50 個 skill**：若某分類已達 50 個，考慮拆分為子分類

---

## 追加 Skill 流程

當需要新增 skill 到知識庫時，**必須依序完成以下步驟**：

### Step A — 判斷分類
讀取新 skill 的 `SKILL.md`，根據「分類判定規則」確定目標分類資料夾。

### Step B — 複製 skill
> **⚠️ 路徑推導規則：禁止猜測或硬編碼路徑。**
> 本 `SKILL.md` 所在目錄即為 skill 知識庫的根目錄。
> 你讀取本檔時已知其完整路徑，以該目錄為基準放置新 skill。
> 例如：若本檔路徑為 `D:\skills\skill-router-nexus\SKILL.md`，
> 則目標路徑為 `D:\skills\skill-router-nexus\<分類資料夾>\<skill-name>\`。
> **嚴禁將 skill 放到本檔所在目錄的父層或其他位置。**

將 skill 資料夾複製到對應分類目錄下：
```
<本 SKILL.md 所在目錄>/<分類資料夾>/<skill-name>/
```

### Step C — 驗證
確認 skill 資料夾內的 `SKILL.md` 存在且可被 `skill_reader.py` 正確解析。

---

## 路由流程（強制執行，禁止跳步）

### Step 1 — 判斷任務分類
先判斷任務主軸，再圈出 2 到 4 個候選分類（主分類 + 相關分類）。
若任務同時涉及規劃、實作、整合、驗證、部署任一組合，預設至少命中 2 個分類，不建議只看單一分類。

### Step 2 — 用 skill_reader.py 多分類掃描

> **⚠️ 路徑推導規則：禁止猜測或硬編碼路徑。**
> `skill_reader.py` 與本 `SKILL.md` 位於同一目錄。
> 你讀取本檔時已知其完整路徑，將檔名替換為 `skill_reader.py` 即為正確路徑。
> 例如：若本檔路徑為 `/foo/bar/skill-router-nexus/SKILL.md`，
> 則腳本路徑為 `/foo/bar/skill-router-nexus/skill_reader.py`。

```bash
# 掃描多個分類（推薦）—— <SKILL_DIR> 替換為本檔所在目錄的實際絕對路徑
python "<SKILL_DIR>/skill_reader.py" --category Agent-Plan --category Coding --category CI-CD-and-Monitoring

# 也可用逗號分隔一次傳入多分類
python "<SKILL_DIR>/skill_reader.py" --category Agent-Plan,Coding,CI-CD-and-Monitoring

# 掃描全部分類（慎用，避免 token 浪費）
python "<SKILL_DIR>/skill_reader.py"
```
`skill_reader.py` 會自動解析每個子 skill 的 frontmatter 並輸出 `name`、`description`、`path`。
優先掃描 Step 1 選出的候選分類，再決定是否擴大掃描範圍。

### Step 3 — 根據輸出進行 mapping
比對 `skill_reader.py` 輸出的 `description` 與任務，從每個命中分類至少挑 1 個 skill。
總數建議 2 到 6 個 skill；複合型任務可提高到 8 個，但仍維持最小必要載入。

### Step 4 — On-demand 載入選定 skill
分批讀取這些選定 skill 的完整 `SKILL.md`（先主分類，再輔助分類），依其指令執行任務。

### Step 5 — 回報來源路徑
完成後必須告知使用者：
> 「已使用 `skill-router-nexus → Agent-Plan + Coding → gstack-plan-eng-review + systematic-debugging` 完成任務」
> ....

---

## 禁止事項

| 禁止行為 | 原因 |
|---------|------|
| 假設任何子 skill 已載入 | 每次 session 必須重新路由 |
| 直接進入子資料夾而不讀此檔 | 此檔是強制入口，不可繞過 |
| 直接查詢或搜尋子 skill 而不先讀此檔 | 查詢行為同樣必須經由路由流程 |
| 跨域任務只命中單一分類就結束 | 容易遺漏關鍵能力，降低路由品質 |
| 命中分類後只選 1 個 skill 且不做比對 | 缺乏備援與交叉驗證，風險較高 |
| 一次性 pre-load 整個分類 | 浪費 token，違反最小載入原則 |
