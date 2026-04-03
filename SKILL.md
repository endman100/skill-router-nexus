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
| 1 | `Agent-and-Workflow/` | Agent & Workflow | Agent 調度、子代理協作、並行分派、多步驟工作流自動化、MCP 伺服器連接、外部應用整合 |
| 2 | `Agent-Plan/` | Agent Plan | ⚠️ Agent 規劃、計畫、檢查、審核時必查此分類。計畫生成與執行、多視角審查（CEO/設計/工程）、自動審查管道、檢查點儲存與恢復、完成前驗證 |
| 3 | `CI-CD-and-Monitoring/` | CI/CD & Monitoring | CI/CD 持續整合與部署、應用效能監控（APM）、錯誤追蹤、日誌聚合、功能旗標、Webhook 管理 |
| 4 | `Cloud-and-Hosting/` | Cloud & Hosting | 雲端基礎設施（AWS/GCP/Azure）、伺服器部署、CDN 加速、容器管理、DNS 設定、無伺服器運算 |
| 5 | `Coding/` | Coding | 測試驅動開發（TDD）、系統化除錯、程式碼審查、Git 分支管理、重構、程式碼品質 |
| 6 | `Communication/` | Communication | 即時通訊（Slack/Discord）、SMS 簡訊、語音通話、推播通知、團隊協作、訊息廣播 |
| 7 | `CRM-Platforms/` | CRM Platforms | 客戶關係管理（HubSpot/Salesforce）、聯絡人管理、銷售漏斗追蹤、交易管線 |
| 8 | `Crypto-and-Market-Data/` | Crypto & Market Data | 加密貨幣交易與報價、區塊鏈查詢、股市數據、金融指標、DeFi 協議 |
| 9 | `Customer-Support/` | Customer Support | 客服工單系統、即時聊天客服、幫助台（Zendesk/Intercom）、跨渠道客戶服務 |
| 10 | `Data-APIs-and-Enrichment/` | Data APIs & Enrichment | 外部數據 API（地理、天氣、體育、新聞）、資料充實、第三方數據整合 |
| 11 | `Dev-Platforms-and-VCS/` | Dev Platforms & VCS | 版本控制平台、低程式碼/無程式碼工具、套件管理（npm/pip）、QA 自動化測試 |
| 12 | `Document-Generation/` | Document Generation | PDF/Word/Excel 文件生成與轉換、OCR 文字辨識、CMS 內容管理系統 |
| 13 | `E-commerce-and-Logistics/` | E-commerce & Logistics | 電商平台（Shopify/WooCommerce）、訂單處理、庫存管理、物流配送追蹤 |
| 14 | `Email-Marketing/` | Email Marketing | 郵件行銷活動（Mailchimp/SendGrid）、自動化郵件序列、訂閱者名單管理 |
| 15 | `Email-Verification/` | Email Verification | 郵件地址驗證與清洗、退信率降低、信箱有效性檢測 |
| 16 | `Events-and-Scheduling/` | Events & Scheduling | 行事曆排程、會議預約、活動管理、票務系統、時段預訂 |
| 17 | `Feedback-and-Survey/` | Feedback & Survey | 產品回饋收集、NPS 調查、客戶滿意度評分、功能請求追蹤 |
| 18 | `Forms-and-E-Signatures/` | Forms & E-Signatures | 線上表單建立、電子簽名（DocuSign）、文件簽署工作流 |
| 19 | `GitHub/` | GitHub | GitHub Issue/PR/CI 管理、程式碼審查自動化、gh CLI 操作、倉庫管理 |
| 20 | `Google-Services/` | Google Services | Google Drive/Calendar/BigQuery/Docs/Meet/Sheets/Gmail 整合 |
| 21 | `Health-and-Lifestyle/` | Health & Lifestyle | 健身追蹤、智慧家居控制（IoT）、遊戲互動、抽獎活動、公益捐贈 |
| 22 | `HR-and-Education/` | HR & Education | 人資管理（HRIS）、招募 ATS 追蹤、薪資計算、線上學習平台（LMS） |
| 23 | `Image-and-Design/` | Image & Design | 圖片處理與壓縮、螢幕截圖、圖庫搜尋、去背摳圖、設計素材管理 |
| 24 | `Image-Generation/` | Image Generation | AI 圖片生成（DALL-E/Midjourney/Flux）、文字轉圖、範本化批量產圖 |
| 25 | `Image-Recognition/` | Image Recognition | 電腦視覺、物件偵測、車牌辨識、圖像分類與標籤、OCR 圖片文字辨識 |
| 26 | `LLM-and-Chatbot/` | LLM & Chatbot | LLM API 呼叫（OpenAI/Anthropic）、聊天機器人、AI 推論、RAG 檢索增強生成 |
| 27 | `Marketing-and-Growth/` | Marketing & Growth | 短網址追蹤、行銷分析儀表板、社交證明、成長駭客工具、A/B 測試 |
| 28 | `Microsoft-Services/` | Microsoft Services | Dynamics 365 CRM、SharePoint 文件管理、Microsoft Clarity 分析 |
| 29 | `Payments-and-Billing/` | Payments & Billing | 線上支付（Stripe/PayPal）、訂閱管理、發票開立、記帳對帳、稅務計算 |
| 30 | `PPT-Design/` | PPT Design | 簡報設計與生成、PowerPoint 自動化、Google Slides 操作 |
| 31 | `Project-Management/` | Project Management | 任務管理（Jira/Trello/Asana）、時間追蹤、看板工作流、知識庫、團隊筆記 |
| 32 | `Sales-Intelligence/` | Sales Intelligence | 潛在客戶開發、B2B 企業數據、聯絡人資料充實、銷售提案自動化 |
| 33 | `Search-and-Network-APIs/` | Search & Network APIs | 搜尋引擎 API、IP 地理定位、DNS 查詢、網路工具、密碼管理 |
| 34 | `Security-and-Compliance/` | Security & Compliance | 資訊安全掃描、合規檢查、隱私政策、安全稽核報告、漏洞舉報 |
| 35 | `SEO-and-Web-Analytics/` | SEO & Web Analytics | SEO 排名分析、網站流量追蹤、競品分析、關鍵字研究、Google Analytics |
| 36 | `Social-Media/` | Social Media | 社群平台管理（Facebook/IG/LinkedIn/X/YouTube）、貼文排程、社群互動 |
| 37 | `Speech-Recognition/` | Speech Recognition | 語音轉文字（STT）、音訊轉錄、會議記錄自動化、影片字幕生成 |
| 38 | `System-and-CLI/` | System & CLI | 系統監控與告警、CLI 命令列工具、終端機自動化、環境管理 |
| 39 | `TTS-and-Voice-AI/` | TTS & Voice AI | 文字轉語音（TTS）、語音合成、語音克隆、AI 語音代理與對話 |
| 40 | `Video-and-Print/` | Video & Print | 照片托管服務、3D 模型渲染、翻頁書製作、印刷品設計自動化 |
| 41 | `Video-Editing/` | Video Editing | 影片下載與擷取、影格處理、影片託管平台、串流媒體處理 |
| 42 | `Video-Generation/` | Video Generation | AI 影片生成、虛擬人物影片、範本化影片批量製作、文字轉影片 |
| 43 | `Web-Design/` | Web Design | 前端 UI 介面設計、HTML/CSS 元件、低程式碼網站建構器、響應式設計 |
| 44 | `Web-Scraping-and-Browser/` | Web Scraping & Browser | 網頁爬蟲與資料擷取、瀏覽器自動化（Playwright/Puppeteer）、代理 IP 池 |
| 45 | `Writing-and-Content/` | Writing & Content | 腦力激盪、AI 內容撰寫、文章摘要、多語翻譯潤稿、品牌命名 |

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
分析任務屬於上方分類中的哪一個（可複合）。

### Step 2 — 用 skill_reader.py 掃描

> **⚠️ 路徑推導規則：禁止猜測或硬編碼路徑。**
> `skill_reader.py` 與本 `SKILL.md` 位於同一目錄。
> 你讀取本檔時已知其完整路徑，將檔名替換為 `skill_reader.py` 即為正確路徑。
> 例如：若本檔路徑為 `/foo/bar/skill-router-nexus/SKILL.md`，
> 則腳本路徑為 `/foo/bar/skill-router-nexus/skill_reader.py`。

```bash
# 掃描單一分類（推薦）—— <SKILL_DIR> 替換為本檔所在目錄的實際絕對路徑
python "<SKILL_DIR>/skill_reader.py" --category Feedback-and-Survey

# 掃描全部分類（慎用，避免 token 浪費）
python "<SKILL_DIR>/skill_reader.py"
```
`skill_reader.py` 會自動解析每個子 skill 的 frontmatter 並輸出 `name`、`description`、`path`。

### Step 3 — 根據輸出進行 mapping
比對 `skill_reader.py` 輸出的 `description` 與任務，選出最多 N 個最匹配的 skill使用。

### Step 4 — On-demand 載入選定 skill
讀取這些選定的 skill 的完整 `SKILL.md`，依其指令執行任務。

### Step 5 — 回報來源路徑
完成後必須告知使用者：
> 「已使用 `skill-router-nexus → Feedback-and-Survey → systematic-debugging` 完成任務」
> ....

---

## 禁止事項

| 禁止行為 | 原因 |
|---------|------|
| 假設任何子 skill 已載入 | 每次 session 必須重新路由 |
| 直接進入子資料夾而不讀此檔 | 此檔是強制入口，不可繞過 |
| 直接查詢或搜尋子 skill 而不先讀此檔 | 查詢行為同樣必須經由路由流程 |
| 一次性 pre-load 整個分類 | 浪費 token，違反最小載入原則 |
