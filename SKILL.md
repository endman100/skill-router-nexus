---
name: skill-router-nexus
description: "⚠️ MANDATORY ENTRY POINT — ALWAYS read this file FIRST before: (1) planning any task (plan / blueprint / roadmap / how to implement), (2) reviewing a plan (review / audit / stress-test), (3) executing a task (implement / build / run), (4) verifying completion (done / verify / submit / PR / confirm finished), (5) accessing, querying, or adding any sub-skill. Do NOT load or look up any sub-skill directly. Every agent, every task, and every skill query must route through this file first. | ⚠️ 強制入口 — 以下情境必須先完整讀取本檔再行動：(1) 制定計畫（計畫、規劃、plan、blueprint、怎麼做）；(2) 計畫審查（review、審查、壓力測試）；(3) 執行任務（執行、implement、build）；(4) 驗證完成（驗證、done、verify、確認完成、submit、PR）；(5) 存取、查詢或新增任何 skill。嚴禁直接載入或查詢子 skill、嚴禁繞過本檔。"
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
| 1 | `Agent-Plan/` | Agent Plan | PLAN 階段啟用時優先檢查此分類。涵蓋腦力激盪、問題拆解、方向探索、unblocking、以及從模糊需求到可行計畫初稿的生成。適用於 Agent 需要探索方向、釐清需求、或制定行動計畫的場景。 |
| 2 | `Agent-Plan-Review/` | Agent Plan Review | 計畫需要壓力測試或執行前審查時檢查此分類。涵蓋多視角計畫審查（CEO/設計/工程）、自動審查管道、程式碼審查請求與接收流程。適用於計畫草稿需要交叉驗證、或進行 code review 的場景。 |
| 3 | `Agent-Execute/` | Agent Execute | 涵蓋計畫實際執行、子代理平行派遣、子代理驅動開發、執行中的檢查點儲存與恢復、以及開發分支完成整合（merge/PR/清理）。適用於 Agent 需要將計畫付諸行動、平行派發子任務、中途暫停與繼續、或完成功能分支收尾的場景。 |
| 4 | `Agent-Verification/` | Agent Verification | ⚠️ 完成任務、提交 PR 或宣告完成前必查此分類。涵蓋完成前驗證、完成度確認、以及防止虛報完成的查核機制。適用於任何提交/PR/完成宣告之前的強制驗證。 |
| 5 | `CI-CD-and-Monitoring/` | CI/CD & Monitoring | 此分類涵蓋持續整合與持續部署（CI/CD）管道、應用程式效能監控、錯誤追蹤、日誌管理、功能旗標控制、以及服務狀態監控。適用於需要自動化建置部署流程、即時追蹤系統健康狀態、或管理運維告警的場景。 |
| 6 | `Cloud-and-Hosting/` | Cloud & Hosting | 此分類涵蓋雲端基礎設施管理、伺服器部署、CDN 配置、容器管理、無伺服器資料庫、DNS 管理、以及雲端服務的自動化操作。適用於需要管理雲端資源、自動化部署流程、或監控基礎設施的場景。 |
| 7 | `Coding/` | Coding | 此分類專注於純粹的程式撰寫實務，包括測試驅動開發、系統化除錯、Web 應用測試、程式碼執行與分析、QA 測試修復、以及 Codex 二次意見諮詢。不包含程式碼審查流程（見 Agent-Plan-Review）、Git 工作流（見 Dev-Platforms-and-VCS）、或 CI/CD 工具（見 CI-CD-and-Monitoring）。適用於需要直接動手寫程式、除錯、測試的場景。 |
| 8 | `Communication/` | Communication | 此分類涵蓋即時通訊、SMS/MMS 簡訊、語音通話、推播通知、以及團隊協作工具的自動化整合。適用於需要透過各種通訊管道發送訊息、管理對話、或整合多平台通訊的場景。 |
| 9 | `CRM-Platforms/` | CRM Platforms | 此分類涵蓋客戶關係管理（CRM）平台的自動化操作，包括聯絡人管理、交易追蹤、銷售漏斗管理、客戶互動記錄、以及 CRM 資料的同步與更新。適用於需要自動化銷售流程或統一管理客戶資料的場景。 |
| 10 | `Crypto-and-Market-Data/` | Crypto & Market Data | 此分類涵蓋加密貨幣交易、區塊鏈操作、股票市場數據查詢、金融指標分析、NFT 管理、以及即時行情追蹤。適用於需要存取金融市場資料、執行加密貨幣操作、或進行投資數據分析的場景。 |
| 11 | `Customer-Support/` | Customer Support | 此分類涵蓋客服工單管理、即時聊天支援、客戶對話自動化、幫助台系統、以及跨渠道客戶服務整合。適用於需要自動化客服流程、管理支援請求、或建置聊天機器人客服的場景。 |
| 12 | `Data-APIs-and-Enrichment/` | Data APIs & Enrichment | 此分類涵蓋各類數據查詢 API，包括地理編碼、天氣資訊、體育數據、新聞、電話驗證、身份查核、以及各種公開資料集的存取。適用於需要從外部數據源獲取結構化資訊來充實應用程式資料的場景。 |
| 13 | `Dev-Platforms-and-VCS/` | Dev Platforms & VCS | 此分類涵蓋版本控制系統、開發協作平台、低程式碼/無程式碼建置工具、套件管理、翻譯本地化、以及品質測試自動化。適用於需要管理程式碼倉庫、自動化開發流程、或使用視覺化開發工具的場景。 |
| 14 | `Document-Generation/` | Document Generation | 此分類涵蓋 PDF 生成與轉換、文件自動化產出、範本渲染、OCR 文字辨識、CMS 內容管理、以及各種文件格式（Excel、Word、PDF）的處理。適用於需要批量生成文件、轉換文件格式、或自動化文件工作流的場景。 |
| 15 | `E-commerce-and-Logistics/` | E-commerce & Logistics | 此分類涵蓋電商平台管理、產品目錄維護、訂單處理、庫存管理、物流配送追蹤、以及零售數據分析。適用於需要自動化電商營運、管理多平台店鋪、或優化配送流程的場景。 |
| 16 | `Email-Marketing/` | Email Marketing | 此分類涵蓋電子郵件行銷活動管理、自動化郵件序列、訂閱者名單管理、郵件範本建立、A/B 測試、以及行銷自動化流程。適用於需要設計與執行郵件行銷活動、管理行銷漏斗、或自動化客戶溝通的場景。 |
| 17 | `Email-Verification/` | Email Verification | 此分類涵蓋電子郵件地址驗證、信箱存在性檢查、郵件清單清洗、退信率降低、以及寄件者信譽維護。適用於需要在發送前驗證郵件地址有效性、清理過時名單、或提升郵件投遞率的場景。 |
| 18 | `Events-and-Scheduling/` | Events & Scheduling | 此分類涵蓋行事曆排程、活動管理、線上會議/網路研討會、預約系統、票務管理、以及場地規劃。適用於需要自動化預約流程、管理活動報名、或整合行事曆服務的場景。 |
| 19 | `Feedback-and-Survey/` | Feedback & Survey | 此分類涵蓋產品回饋收集、NPS 調查、客戶滿意度評分、功能請求管理、評論彙整、以及使用者意見分析。適用於需要系統化收集與分析用戶回饋、追蹤產品改善建議的場景。 |
| 20 | `Forms-and-E-Signatures/` | Forms & E-Signatures | 此分類涵蓋線上表單建立、資料收集、電子簽名、文件簽署工作流、問卷調查表單、以及憑證與通行證管理。適用於需要自動化表單處理流程、數位簽署文件、或收集結構化資料的場景。 |
| 21 | `GitHub/` | GitHub | 此分類專門涵蓋 GitHub 平台操作，包括 Issue 管理、Pull Request 工作流、CI 狀態查詢、程式碼審查、以及透過 GitHub CLI 進行的各種自動化操作。適用於需要直接與 GitHub 倉庫互動的場景。 |
| 22 | `Google-Services/` | Google Services | 此分類涵蓋 Google 生態系服務的自動化操作，包括 Google Drive、Google Calendar、BigQuery、Google Docs、Google Meet、Google Photos、以及 Google 搜尋控制台等。適用於需要整合或自動化 Google 套件服務的場景。 |
| 23 | `Health-and-Lifestyle/` | Health & Lifestyle | 此分類涵蓋健身追蹤、智慧家居控制、天氣查詢、遊戲平台整合、抽獎工具、捐款管理、以及環保公益相關服務。適用於需要整合生活類應用、管理健康數據、或進行休閒娛樂互動的場景。 |
| 24 | `HR-and-Education/` | HR & Education | 此分類涵蓋人力資源管理、招募流程自動化、薪資發放、員工入職、績效管理、線上學習平台、認證管理、以及會員制課程系統。適用於需要自動化 HR 流程、管理招聘漏斗、或建置教育內容的場景。 |
| 25 | `Knowledge-and-Productivity/` | Knowledge & Productivity | 此分類涵蓋筆記工具管理、任務清單與待辦事項追蹤、無程式碼資料庫建置、白板協作、儀表板視覺化、書籤管理、試算表資料庫、會議記錄分析、學習回顧、以及個人與團隊生產力工具整合。適用於需要組織個人或團隊知識資產、管理日常工作任務、或建置無程式碼資料管理系統的場景。 |
| 26 | `Image-and-Design/` | Image & Design | 此分類涵蓋圖片處理、壓縮最佳化、截圖擷取、圖庫搜尋、去背、浮水印處理、GIF 搜尋、圖片託管、以及設計素材管理。適用於需要批量處理圖片、管理視覺素材、或自動化圖片工作流的場景。 |
| 27 | `Image-Generation/` | Image Generation | 此分類涵蓋 AI 圖片生成、文字轉圖片、範本化圖片批量產出、橫幅廣告自動生成、以及創意視覺內容生成。適用於需要利用 AI 或範本快速產出圖片素材的場景。 |
| 28 | `Image-Recognition/` | Image Recognition | 此分類涵蓋電腦視覺、圖像分類、物件偵測、車牌辨識、圖片替代文字生成、AI 圖像增強、以及文件影像資料擷取。適用於需要從圖片中自動辨識與提取資訊的場景。 |
| 29 | `LLM-and-Chatbot/` | LLM & Chatbot | 此分類涵蓋大型語言模型 API 整合、聊天機器人建置、AI 推論服務、文字生成、RAG 檢索增強生成、AI 抄襲偵測、以及 LLM 應用開發框架。適用於需要呼叫 LLM API、建置對話式 AI 應用、或管理 AI 模型的場景。 |
| 30 | `Marketing-and-Growth/` | Marketing & Growth | 此分類涵蓋社群行銷工具、短網址服務、行銷分析、品牌資產管理、彈出式視窗、社交證明、直郵行銷、內容發布、以及成長駭客工具。適用於需要擴大品牌觸及、優化行銷漏斗、或管理多渠道行銷活動的場景。 |
| 31 | `MCP-Util/` | MCP Util | 涵蓋 MCP（Model Context Protocol）伺服器建置指南、工具枚舉、組態管理、身份驗證、schema 管理、以及 Claude Plugin 整合。適用於需要建置 MCP 伺服器、設定 MCP 工具、管理 Claude 擴充套件、或進行工具連接自動化的場景。 |
| 32 | `Microsoft-Services/` | Microsoft Services | 此分類涵蓋 Microsoft 生態系服務的自動化操作，包括 Dynamics 365 CRM、SharePoint 文件管理、以及 Microsoft Clarity 網站分析。適用於需要整合或自動化 Microsoft 企業服務的場景。 |
| 33 | `Payments-and-Billing/` | Payments & Billing | 此分類涵蓋線上支付處理、訂閱管理、發票開立、記帳與會計、費用追蹤、稅務計算、以及收款自動化。適用於需要整合支付閘道、管理定期訂閱、或自動化財務帳務的場景。 |
| 34 | `PPT-Design/` | PPT Design | 此分類涵蓋簡報設計與製作，包括 HTML 動畫簡報、PowerPoint 生成與轉換、Google Slides 操作、簡報主題樣式設計、以及資料視覺化簡報。適用於需要自動化簡報製作或設計精美投影片的場景。 |
| 35 | `Project-Management/` | Project Management | 此分類涵蓋任務與專案管理、看板工作流、敏捷開發（Scrum）、工作排程規劃、服務工單管理、團隊協作工具、以及自由工作者專案追蹤。適用於需要管理團隊工作進度、協調多個專案任務、或追蹤服務交付流程的場景。 |
| 36 | `Sales-Intelligence/` | Sales Intelligence | 此分類涵蓋潛在客戶開發、B2B 數據挖掘、聯絡人資訊充實、銷售情報分析、提案工具、以及自動化外展序列。適用於需要發掘商機、充實潛客資料、或加速銷售流程的場景。 |
| 37 | `Search-and-Network-APIs/` | Search & Network APIs | 此分類涵蓋搜尋引擎 API、IP 地理定位、網路安全查詢、DNS 工具、OCR 光學文字辨識、驗證碼處理、密碼管理、以及各類公用網路服務 API。適用於需要整合搜尋功能、進行網路分析、或存取各類工具型 API 的場景。 |
| 38 | `Security-and-Compliance/` | Security & Compliance | 此分類涵蓋資訊安全工具、合規管理、隱私保護、安全稽核、舉報系統、身份驗證、以及郵件隱私代理。適用於需要確保系統安全性、符合法規要求、或管理安全事件的場景。 |
| 39 | `SEO-and-Web-Analytics/` | SEO & Web Analytics | 此分類涵蓋搜尋引擎優化分析、網站流量追蹤、競品分析、關鍵字研究、反向連結監控、社群媒體趨勢分析、以及內容行銷成效追蹤。適用於需要提升網站搜尋排名、分析用戶行為、或監測競爭對手動態的場景。 |
| 40 | `Skill-Util/` | Skill Util | 涵蓋 Skill 生態系工具，包括 skill 建立、編輯、驗證、打包、發布、分享、範本管理、以及知識庫路由規則維護。適用於需要建立新 skill、維護現有 skill、管理知識庫、或最佳化 skill 路由的場景。 |
| 41 | `Social-Media/` | Social Media | 此分類涵蓋主流社群媒體平台（Facebook、Instagram、LinkedIn、Twitter、TikTok、YouTube 等）的自動化操作，包括貼文管理、廣告投放、影音上傳、以及社群互動追蹤。適用於需要自動化社群經營或管理多平台內容的場景。 |
| 42 | `Speech-Recognition/` | Speech Recognition | 此分類涵蓋語音轉文字（STT）、音訊轉錄、會議記錄自動化、字幕生成、以及多語言語音辨識。適用於需要將音訊或會議內容自動轉換為文字記錄的場景。 |
| 43 | `System-and-CLI/` | System & CLI | 此分類涵蓋系統監控、密碼管理、命令列工具、智慧家居控制、終端機管理、以及各類本地端系統操作工具。適用於需要透過 CLI 管理系統資源或自動化本機作業的場景。 |
| 44 | `Time-Tracking/` | Time Tracking | 此分類涵蓋工時追蹤與記錄、專案時間成本分析、生產力統計報告、帳單計費自動化、以及開發者程式碼時間統計（Wakatime）。適用於需要精確追蹤工作時間、分析時間分配效率、或根據工時自動產生帳單的場景。 |
| 45 | `TTS-and-Voice-AI/` | TTS & Voice AI | 此分類涵蓋文字轉語音（TTS）、語音合成、語音克隆、AI 語音代理、語音對話機器人、以及自然語言處理。適用於需要生成語音內容、建置語音互動介面、或進行文本分析的場景。 |
| 46 | `Video-and-Print/` | Video & Print | 此分類涵蓋照片托管與分享、3D 模型管理、數位翻頁書、名片與印刷品自動化、目錄網站建置、以及互動式展示板。適用於需要管理視覺媒體資產或自動化印刷品生產的場景。 |
| 47 | `Video-Editing/` | Video Editing | 此分類涵蓋影片下載、影格擷取、影片託管管理、以及影片串流處理。適用於需要下載、裁切、擷取影片片段、或管理影片內容的場景。 |
| 48 | `Video-Generation/` | Video Generation | 此分類涵蓋 AI 影片生成、虛擬人物影片、範本化影片製作、以及自動化影片剪輯與合成。適用於需要利用 AI 快速產出影片內容或建立虛擬主播影片的場景。 |
| 49 | `Web-Design/` | Web Design | 此分類涵蓋前端網頁介面設計、HTML 互動元件建置、低程式碼網站建構、視覺化設計到程式碼轉換、以及網頁原型製作。此大型分類已在 `category-taxonomy.json` 啟用第二層 subcategory；先依研究與方向、UI 與產品設計、前端與動效實作、原型與建站、媒體文件內容、協作營運等子分類定位，再選 skill。 |
| 50 | `Web-Scraping-and-Browser/` | Web Scraping & Browser | 此分類涵蓋網頁爬蟲、資料擷取、瀏覽器自動化、代理 IP 管理、搜尋結果抓取、以及結構化資料提取。適用於需要從網站批量擷取資料、自動化瀏覽器操作、或建置資料採集管道的場景。 |
| 51 | `Writing-and-Content/` | Writing & Content | 此分類涵蓋腦力激盪、內容研究與撰寫、摘要生成、翻譯潤稿、命名發想、以及寫作計畫制定。適用於需要輔助內容創作、改善文案品質、或規劃寫作流程的場景。 |
| 52 | `ComfyUI/` | ComfyUI | 此分類涵蓋 ComfyUI 自訂節點開發的完整知識庫，包括 V3 節點結構、資料型別（IMAGE/LATENT/MASK 等）、輸入輸出設定、前端 JavaScript 擴充、執行生命週期（快取/驗證/lazy）、打包發布、以及 V1 → V3 遷移指南。適用於需要開發、除錯、遷移或打包 ComfyUI 自訂節點的場景。 |
| 53 | `Entrepreneurship/` | Entrepreneurship | 此分類涵蓋 Minimalist Entrepreneur（極簡創業家）方法論的完整工作流，基於 Sahil Lavingia（Gumroad 創辦人）所著《The Minimalist Entrepreneur》。包括社群識別（find-community）、構想驗證（validate-idea）、MVP 建構（mvp）、手動流程化（processize）、早期客戶獲取（first-customers）、定價策略（pricing）、內容行銷計畫（marketing-plan）、可持續成長決策（grow-sustainably）、公司文化與價值觀（company-values）、以及業務決策審查（minimalist-review）。適用於 bootstrapped 創業者、獨立開發者、或任何希望以小規模可獲利方式建立事業的人。 |
| 54 | `AI-Research/` | AI Research | 此分類涵蓋 AI 研究方法與研究生命週期，包括自主研究編排、研究構想、學術檢索、可執行 rubric 誘導、證據導向驗證與修訂、機制可解釋性、因果干預、論文撰寫、學術圖表與會議報告。適用於提出研究假設、設計與執行實驗、把開放式科學任務轉成可驗證規格、解釋模型行為、查找文獻或產出研究成果；訓練、推論、RAG 與具體模態工具應按核心功能路由至專屬分類。 |
| 55 | `Science/` | Science | 涵蓋科學與研究 skill，包括生物資訊與多體學、化學與藥物發現、臨床醫療、實驗室平台、物理量子與模擬、科學資料與機器學習、研究與溝通。此大型分類已在 `category-taxonomy.json` 啟用第二層 subcategory；先選最直接的子分類，再選具體工具或 workflow。 |
| 56 | `Metaphysics-and-Spirituality/` | Metaphysics & Spirituality | 此分類涵蓋中華傳統命理術數與宗教靈性相關的 AI Skill，包括四柱八字排盤與命理分析、奇門遁甲判斷與擇時、紫微斗數本命盤解讀、姻緣測算（八字合婚、生肖配對、紫微夫妻宮、桃花運勢）、以及基於佛教經典文獻的漢傳祖師教學角色生成與對話。適用於需要進行傳統命理排盤計算、術數分析、姻緣配對、佛學經典查詢、或建置傳統文化 AI 應用的場景。 |
| 57 | `2D-Rigging-and-Animation/` | 2D Rigging & Animation | 此分類涵蓋 2D 角色綁定與動畫專案，包括網格、變形器、參數與關鍵形、紋理與圖集、專案封裝格式及可編輯模型資產處理。適用於需要分析、解包、修改、重封裝或驗證 Live2D 等 2D 骨架動畫工程檔的場景。 |
| 58 | `Reverse-Engineering/` | Reverse Engineering | 此分類涵蓋二進位、行動應用、前端 JavaScript、自訂虛擬機、跨版本差分、反編譯器與動態分析等逆向工程 skill。適用於理解編譯、混淆、封裝或虛擬化目標的內部行為，以及在合法授權範圍內將分析結果延伸至漏洞驗證。 |
| 59 | `Diagramming-and-Visualization/` | Diagramming & Visualization | 此分類涵蓋流程圖、架構圖、序列圖、狀態圖、ER 圖、資料流圖及其他技術視覺化的生成、驗證與渲染。適用於需要將系統、流程或關係轉換為 Mermaid、Graphviz、PlantUML 或 SVG 的場景。 |
| 60 | `Writing-Craft/` | Writing Craft | 此分類涵蓋文章素材探索、段落結構塑形、敘事節拍編排與其他寫作工藝方法。適用於需要從零散素材發展文章、建立閱讀旅程、或改善長文結構與節奏的場景。 |
| 61 | `Creative-Video-Generation/` | Creative Video Generation | 此分類涵蓋以特定美術風格、敘事結構與生成模型為核心的創意影片工作流，包括產品廣告、3D 動畫短片、紙藝定格、品牌宣傳、音樂字幕、遊戲開場與手繪實拍融合。適用於需要從創意規劃、素材確認、分鏡到生成與驗收的一體化影片製作場景。 |
| 62 | `Reverse-Analysis/` | Reverse Analysis | 此分類統一收納逆向分析與 CTF 競賽分析 skill，涵蓋二進位、行動應用、前端 JavaScript、惡意程式、數位鑑識、雲端、身分、協定、硬體、漏洞利用與多類型 CTF 題目。所有 skill 均以單層目錄攤平，適用於需要直接搜尋、載入或組合逆向與競賽分析工作流的場景。 |
| 63 | `Video-Understanding/` | Video Understanding | 此分類涵蓋長短影片的視覺內容理解、時間分段、影片問答、事件與鏡頭定位、電影語言分析、場景檢索及即時串流理解。適用於需要從影片畫面取得可驗證描述、時間戳摘要、運鏡與構圖證據、語意索引或事件警報的場景；純語音轉錄、剪輯、轉碼與影片生成應分別路由至其專屬分類。 |
| 64 | `AI-Training/` | AI Training | 此分類涵蓋模型預訓練、微調、後訓練、RLHF、偏好最佳化、知識蒸餾、資料整理、分散式訓練與模型合併。適用於建立或調整模型權重、準備訓練資料、執行大規模訓練及管理訓練工作流。 |
| 65 | `AI-Inference-and-Optimization/` | AI Inference & Optimization | 此分類涵蓋模型推論服務、量化、解碼加速、注意力最佳化、模型壓縮與硬體執行階段最佳化。適用於降低延遲或記憶體使用、提升吞吐量、部署本地模型或建立高效推論服務。 |
| 66 | `AI-Models-and-Architecture/` | AI Models & Architecture | 此分類涵蓋模型架構、序列建模、長上下文技術、分詞器與基礎模型實作。適用於理解、比較或實作模型結構，以及建立模型輸入表示與架構元件。 |
| 67 | `AI-Evaluation-and-Benchmarking/` | AI Evaluation & Benchmarking | 此分類涵蓋模型評測框架、標準基準、可重現比較與品質量測。適用於比較模型能力、追蹤訓練成效、產生研究或產品評測結果，以及執行跨後端基準測試。 |
| 68 | `AI-MLOps/` | AI MLOps | 此分類涵蓋 AI 實驗追蹤、可觀測性、執行比較、模型登錄、資料與產物版本管理及生產監控。適用於管理模型生命週期、追蹤實驗指標、除錯 LLM 應用或監控模型系統。 |
| 69 | `AI-Robotics/` | AI Robotics | 此分類涵蓋機器人策略、Vision-Language-Action 模型、模擬環境、操作任務微調與機器人評測。適用於訓練、部署或評估具身 AI 與機器人控制模型。 |
| 70 | `Audio-and-Music-Generation/` | Audio & Music Generation | 此分類涵蓋 AI 音樂、音效及其他非語音音訊生成。適用於從文字或旋律條件建立音樂與聲音素材；語音合成應路由至 TTS-and-Voice-AI，語音辨識應路由至 Speech-Recognition。 |
| 71 | `Agent-Delivery/` | Agent Delivery | DELIVER 階段優先檢查此分類。涵蓋使用者可讀的結果整理、成品連結、驗證證據、限制與阻塞狀態交付。適用於任何任務完成、部分完成或受阻時的最終回覆。 |

> **新增 skill 時，必須按照下方「分類與 Skill 命名規範」及「新增 Skill 與分類分裂決策流程」操作。**

---

## 分類判定規則（追加 Skill 時使用）

當需要將新 skill 歸類時，依照以下優先順序判斷：

1. **讀取 SKILL.md 內容**：從 description、body 關鍵字判斷功能
2. **平台歸屬優先**：若明確屬於某平台（GitHub → `GitHub/`、Google → `Google-Services/`、Microsoft → `Microsoft-Services/`）直接歸類
3. **功能歸屬次之**：根據核心功能匹配最接近的分類（例如「語音轉文字」→ `Speech-Recognition/`）
4. **若橫跨多類**：在所有相關分類中各放置一份，允許重複放置
5. **大型分類使用選擇性第二層**：分類接近或超過 100 個 skill，或語義明顯混雜時，先評估在 `category-taxonomy.json` 宣告 subcategory；未登錄於 taxonomy 的分類維持單層，不為了形式一致強制拆分

### 選擇性雙層分類

- 第一層 category 是穩定的領域或生命週期入口；第二層 subcategory 是隸屬於該 category 的子分類，兩者是嚴格的父子關係。
- `category-taxonomy.json` 是雙層結構的真源，並由 `schemas/category-taxonomy.schema.json` 描述格式。目前只對 `Web-Design` 與 `Science` 啟用第二層。
- 單層分類的實體路徑是 `<category>/<skill-name>/SKILL.md`；啟用第二層後，實體路徑是 `<category>/<subcategory>/<skill-name>/SKILL.md`。
- 未登錄於索引的分類維持單層；此索引即 `category-taxonomy.json`，只有規模或歧義真的需要時才增加 subcategory。
- subcategory 必須按清楚的工作範圍、方法或能力命名，不按任意數量切片；每個 subcategory 只屬於一個 category，同一 category 內的每個 skill 也只能放在一個 subcategory。

---

## 分類與 Skill 命名規範

名稱分成機器使用的 folder ID 與人類閱讀的 display name。folder ID 必須穩定、可預測且可由驗證器檢查；display name 可以保留正常空格、大小寫與符號，但不得改變分類語義。

### 第一層 category

- folder ID 使用英文 `Title-Kebab-Case`，格式為 `^[A-Z0-9][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*$`，最多 64 個字元。
- 一般單字首字母大寫；既有標準縮寫維持大寫，例如 `AI`、`API`、`CRM`、`LLM`、`MCP`、`SEO`、`TTS`、`VCS`。
- 使用名詞或穩定領域名稱，例如 `Project-Management`、`AI-Training`；避免使用一次性任務、版本號或含糊名稱。
- 多領域組合統一使用 `-and-`；不得使用空格、底線、斜線、尾端連字號或連續連字號。
- 不得按提供者建立第一層分類，除非該提供者本身就是使用者會直接尋找、且能長期容納多個 skill 的平台入口，例如 `GitHub`。
- 知識庫分類地圖中的英文名是 display name，例如 folder ID `AI-Inference-and-Optimization` 對應 `AI Inference & Optimization`。

### 第二層 subcategory

- `id` 使用英文 `lowercase-kebab-case`，格式為 `^[a-z0-9]+(?:-[a-z0-9]+)*$`，最多 64 個字元。
- 使用名詞片語描述父分類內穩定、可重用的工作範圍，例如 `bioinformatics-and-omics`；不得以流水號、任意數量切片或暫時專案命名。
- 不得按提供者或作者分組；只有提供者本身構成穩定的方法範圍時，才可成為名稱的一部分。
- 不必重複父分類名稱，除非省略後會造成歧義；同一父分類內不得出現同義、包含關係不清或高度重疊的 id。
- `category-taxonomy.json` 中的 `name` 是 display name，使用正常英文標題格式並保留標準縮寫，例如 `Bioinformatics & Omics`。

### Skill

- 新增或重新命名的 skill folder 與 frontmatter `name` 使用英文 `lowercase-kebab-case`，最多 64 個字元，兩者必須一致。
- 動作型 skill 優先使用簡短的動詞導向名稱；平台專屬 skill 可在必要時加入工具 namespace，例如 `gh-address-comments`。
- 名稱應描述可重用能力，不加入版本號、作者名、來源倉庫名或 `new`、`final` 等暫時字樣。
- 既有 legacy skill 名稱可保留以避免破壞相容性；所有新增與主動重新命名的 skill 必須遵循本規範。

---

## 新增 Skill 與分類分裂決策流程

當需要新增 skill 到知識庫時，必須依序完成以下步驟。正常順序是先加入目前最合理且合法的位置，再依加入後的整體狀態決定是否分裂；只有不存在合法落點時，才先調整分類結構。

### Step A — 理解新 Skill

完整讀取新 skill 的 `SKILL.md`，辨識主要問題、使用者觸發意圖、操作平台或領域、輸入輸出、核心工作流程，以及與現有 skill 是否重複。不得只根據名稱、作者或來源判斷分類。

### Step B — 決定第一層分類

使用 roadmap 比較所有第一層分類的實際描述。既有分類能準確涵蓋主要用途時，選擇最直接的一個；平台專屬 skill 優先使用對應平台分類，其他 skill 依核心功能與使用者目標分類。只有所有既有分類都不適用，且新領域是穩定、獨立、可由使用者直接尋找並能容納多個 skill 的入口時，才建立新的第一層分類。

### Step C — 決定合法落點

- 單層分類使用 `<分類資料夾>/<skill-name>/SKILL.md`。
- 已啟用第二層的分類，使用 `<分類資料夾>/<subcategory>/<skill-name>/SKILL.md`，並選擇一個已宣告且最直接的 subcategory。
- 同一個 skill 在同一 category 中只能有一個主要 subcategory。
- 若所有既有 subcategory 都不適用，skill 不得直接放在第一層分類根目錄，也不得直接建立未宣告的 subcategory。先重新檢查第一層分類，再判斷應擴充既有描述、建立新 subcategory，或建立新 category。

> **路徑推導規則：** 本 `SKILL.md` 所在目錄就是知識庫根目錄。禁止猜測、硬編碼其他根目錄，或把 skill 放到其父層及其他位置。

### Step D — 加入並第一次驗證

將 skill 複製到合法落點後，確認 `SKILL.md`、`name`、`description`、folder ID、父子目錄與 taxonomy 宣告均有效，並檢查同名或同內容重複。執行：

```bash
python -B "<SKILL_DIR>/skill_reader.py" --validate --category <category>
python -B "<SKILL_DIR>/skill_reader.py" --category <category> --subcategory <subcategory> --query <skill-name>
```

單層分類省略 `--subcategory`。第一次驗證只確認 skill 是否放對；若數量門檻觸發驗證失敗或警示，仍須繼續執行 Step E，不得直接結束新增流程。

### Step E — 加入後重新評估分類健康度

重新計算目標 category、目標 subcategory 與相鄰分支的 skill 數量和語義分布，檢查：

- 單層 category 是否接近或超過 100 個 skill。
- subcategory 是否接近或超過 50 個 skill。
- 是否已形成至少兩到三個穩定、可命名的能力群組。
- 查詢結果是否混入大量無關候選，或分類描述已寬泛到無法有效路由。
- 新 skill 是否揭露了未被識別的獨立領域。
- 現有分支是否出現同義、重疊或邊界不清。

數量只負責觸發重新評估，不得單獨作為分裂理由。若數量偏大但語義仍單純且查詢準確，可以保持現狀；數量未達門檻但語義已明顯混雜，也可以提早分裂。

### Step F — 決定分裂方向

按照以下優先順序選擇分裂方向：

1. **第一層分類向下分裂**：單層 category 仍屬同一上位領域，但內部已有清楚的能力群組時，優先建立多個 subcategory。不得按數量平均切片。
2. **subcategory 水平分裂**：既有 subcategory 過大或含有多種能力時，拆成兩個以上同層兄弟 subcategory。系統維持雙層結構，不建立第三層。
3. **第一層分類水平分裂**：只有原 category 已包含本質不同、可被使用者獨立尋找、且各自能長期容納多個 skill 的領域時，才把其中一部分提升為新的第一層 category。不得只因總數超過 100 就使用此方向。

若沒有形成清楚、穩定且能提高查詢精確度的分界，維持目前結構。

### Step G — 執行分類分裂

確定分裂後，先定義新 category 或 subcategory 的 folder ID、display name、包含範圍與排除範圍，再更新 `category-taxonomy.json`、建立實體目錄並重新分類所有受影響 skills。不得只移動剛加入的新 skill；必須處理整個能力群組，並同步更新分類地圖與說明。

### Step H — 第二次驗證

分裂或維持原結構後，再次執行結構驗證、roadmap 查詢、分類查詢與新 skill 精確查詢。最終決策必須記錄為以下其中一種：

- `KEEP_FLAT`：維持單層分類。
- `KEEP_SUBCATEGORY`：維持目前 subcategory。
- `CREATE_SUBCATEGORY`：第一層分類向下建立第二層。
- `SPLIT_SUBCATEGORY`：將一個 subcategory 拆成多個同層分支。
- `CREATE_CATEGORY`：建立新的第一層分類。
- `RECLASSIFY_SKILL`：最初落點錯誤，重新歸類 skill。

---

## 追加 分類 流程

當需要新增分類資料夾時，**必須依序完成以下步驟**：

### Step A — 判斷分類名稱
根據「分類判定規則」與「分類與 Skill 命名規範」確定分類名稱，並確認不與現有分類重複。
### Step B — 建立資料夾
> **⚠️ 路徑推導規則：禁止猜測或硬編碼路徑。**
> 本 `SKILL.md` 所在目錄即為 skill 知識庫的根目錄。
> 你讀取本檔時已知其完整路徑，以該目錄為基準放置新分類資料夾。
> 例如：若本檔路徑為 `D:\skills\skill-router-nexus\SKILL.md`，
> 則新分類資料夾路徑為 `D:\skills\skill-router-nexus\<新分類資料夾>\`。
> **嚴禁將分類資料夾放到本檔所在目錄的父層或其他位置。**

### Step C — 新增分類說明
在新分類資料夾內建立 `readme.md`，內容包含分類說明與適用場景。

### Step D — 新增 知識庫分類地圖 
在本 `SKILL.md` 的「知識庫分類地圖」表格中新增一行，包含新分類的資料夾名稱、英文名、以及說明。 說明與readme.md 內容需保持一致。

---

## 路由流程（強制執行，禁止跳步）

### Step 1 — 準備最小任務摘要

主 Agent 只整理路由所需的目標、成品與限制。移除密鑰、私人資料、完整對話及無關內容。

### Step 2 — 啟動一個 Router Sub-agent

需要搜尋時，主 Agent 只啟動 **一個** fresh／isolated internal Sub-agent，標記 `role=skill-router-scout`，並傳入最小任務摘要。這個 Sub-agent 一次找齊任務需要的所有 skills，不得再次委派、修改檔案、執行候選 skill 或產生外部副作用。

只有三種情況不啟動：使用者已指定且主 Agent 已知確切路徑；當前 Agent 已是 `skill-router-scout`；環境沒有可用 Sub-agent。最後一種情況才由主 Agent 本地搜尋。

### Step 3 — 搜尋並回傳路徑

Router Sub-agent 先完整讀取本 Router，再用與本檔同目錄的 `skill_reader.py` 搜尋。先查最直接的分類，只有仍缺能力時才擴大範圍。

> **⚠️ 路徑推導規則：禁止猜測或硬編碼路徑。**
> `skill_reader.py` 與本 `SKILL.md` 位於同一目錄。
> 你讀取本檔時已知其完整路徑，將檔名替換為 `skill_reader.py` 即為正確路徑。
> 例如：若本檔路徑為 `/foo/bar/skill-router-nexus/SKILL.md`，
> 則腳本路徑為 `/foo/bar/skill-router-nexus/skill_reader.py`。

```bash
python -B "<SKILL_DIR>/skill_reader.py" --roadmap
python -B "<SKILL_DIR>/skill_reader.py" --category <category>
python -B "<SKILL_DIR>/skill_reader.py" --category <category> --query "<keywords>"
python -B "<SKILL_DIR>/skill_reader.py" --category <category> --list-subcategories
python -B "<SKILL_DIR>/skill_reader.py" --category <category> --subcategory <subcategory> --query "<keywords>"
```

Sub-agent 只依主 Agent 應讀取的順序回傳去重後的 `SKILL.md` 絕對路徑：

```json
{"skill_paths":["<absolute-path-to-SKILL.md>"]}
```

搜尋細節留在 Sub-agent。不得回傳 roadmap、分類清單、落選候選、manifest、hash、評分或搜尋紀錄；找不到合格 skill 時回傳空陣列。

### Step 4 — 主 Agent 讀取 Skills

主 Agent 確認每個回傳路徑存在、位於本 Router 所在的知識庫內且指向 `SKILL.md`，再親自完整讀取每個選中的 skill。Sub-agent 的搜尋不能代替這一步。

### Step 5 — 主 Agent 執行任務

理解、規劃、執行、驗證與交付都由主 Agent 依選中的 skills 及更高優先級指令完成。Router 到 Step 4 即完成職責，不管理後續任務生命週期，也不要求主 Agent 回報搜尋細節。

---

## 禁止事項

| 禁止行為 | 原因 |
|---------|------|
| 未先讀取本 Router 就查詢或載入子 skill | 本檔是強制入口 |
| 需要搜尋時啟動多個 Router Sub-agent | 一個 Sub-agent 應一次找齊所有路徑 |
| `skill-router-scout` 再啟動 Sub-agent | 避免無限遞迴 |
| 將完整對話、密鑰或私人資料傳給 Router Sub-agent | 路由只需要最小任務摘要 |
| Router Sub-agent 完整讀取或執行最終 skill | 它只負責搜尋路徑 |
| Router Sub-agent 回傳路徑以外的搜尋資料 | 避免污染主 Agent context |
| 主 Agent 未完整讀取所選 skill 就開始使用 | 路徑回報不能取代 skill 指令 |
