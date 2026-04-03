---
name: skill-router-nexus
description: "⚠️ MANDATORY ENTRY POINT — You MUST read this file completely before accessing, querying, or loading any sub-skill. Do NOT load or look up any sub-skill directly. Every agent, every task, and every skill query must route through this file first. | ⚠️ 強制入口 — 所有 agent 在執行任務、查詢 skill 或新增 skill 之前，必須先完整讀取本檔並依照路由流程操作。嚴禁直接載入或查詢子 skill、嚴禁繞過本檔、嚴禁假設知識庫內容。"
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
| 1 | `Agent-and-Workflow/` | Agent & Workflow | AI Agent 調度、多步驟任務執行、工作流自動化、子代理協作 |
| 2 | `Agent-Plan/` | Agent Plan | Agent 規劃任務時使用此分類。計畫審查與評估，含 CEO/設計/工程等多元視角的計畫審查 |
| 3 | `CI-CD-and-Monitoring/` | CI/CD & Monitoring | 持續整合/部署、效能監控、錯誤追蹤、日誌管理 |
| 4 | `Cloud-and-Hosting/` | Cloud & Hosting | 雲端基礎設施、伺服器部署、CDN、容器、DNS |
| 5 | `Coding/` | Coding | 測試驅動開發、系統化除錯、程式碼審查、Git 分支管理 |
| 6 | `Communication/` | Communication | 即時通訊、SMS、語音通話、推播通知、團隊協作 |
| 7 | `CRM-Platforms/` | CRM Platforms | 客戶關係管理平台、聯絡人管理、銷售漏斗 |
| 8 | `Crypto-and-Market-Data/` | Crypto & Market Data | 加密貨幣交易、區塊鏈、股市數據、金融指標 |
| 9 | `Customer-Support/` | Customer Support | 客服工單、即時聊天、幫助台、跨渠道客服 |
| 10 | `Data-APIs-and-Enrichment/` | Data APIs & Enrichment | 地理、天氣、體育、新聞等外部數據 API |
| 11 | `Dev-Platforms-and-VCS/` | Dev Platforms & VCS | 版控平台、低程式碼工具、套件管理、QA 測試 |
| 12 | `Document-Generation/` | Document Generation | PDF/Word/Excel 生成與轉換、OCR、CMS |
| 13 | `E-commerce-and-Logistics/` | E-commerce & Logistics | 電商平台、訂單處理、庫存管理、物流配送 |
| 14 | `Email-Marketing/` | Email Marketing | 郵件行銷活動、自動化郵件序列、訂閱者管理 |
| 15 | `Email-Verification/` | Email Verification | 郵件地址驗證、信箱清洗、退信率降低 |
| 16 | `Events-and-Scheduling/` | Events & Scheduling | 行事曆排程、活動管理、預約、票務 |
| 17 | `Feedback-and-Survey/` | Feedback & Survey | 產品回饋、NPS、客戶滿意度、功能請求 |
| 18 | `Forms-and-E-Signatures/` | Forms & E-Signatures | 線上表單、電子簽名、文件簽署工作流 |
| 19 | `GitHub/` | GitHub | GitHub Issue/PR/CI、程式碼審查、gh CLI 操作 |
| 20 | `Google-Services/` | Google Services | Google Drive/Calendar/BigQuery/Docs/Meet 等 |
| 21 | `Health-and-Lifestyle/` | Health & Lifestyle | 健身追蹤、智慧家居、遊戲、抽獎、公益 |
| 22 | `HR-and-Education/` | HR & Education | 人資管理、招募 ATS、薪資、線上學習 |
| 23 | `Image-and-Design/` | Image & Design | 圖片處理、壓縮、截圖、圖庫、去背、素材管理 |
| 24 | `Image-Generation/` | Image Generation | AI 圖片生成、文字轉圖、範本化批量產圖 |
| 25 | `Image-Recognition/` | Image Recognition | 電腦視覺、物件偵測、車牌辨識、圖像分析 |
| 26 | `LLM-and-Chatbot/` | LLM & Chatbot | LLM API、聊天機器人、AI 推論、RAG |
| 27 | `Marketing-and-Growth/` | Marketing & Growth | 短網址、行銷分析、社交證明、成長駭客 |
| 28 | `Microsoft-Services/` | Microsoft Services | Dynamics 365、SharePoint、Clarity |
| 29 | `Payments-and-Billing/` | Payments & Billing | 線上支付、訂閱管理、發票、記帳、稅務 |
| 30 | `PPT-Design/` | PPT Design | 簡報設計、PowerPoint 生成、Slides 操作 |
| 31 | `Project-Management/` | Project Management | 任務管理、時間追蹤、看板、知識庫、筆記 |
| 32 | `Sales-Intelligence/` | Sales Intelligence | 潛客開發、B2B 數據、聯絡人充實、提案 |
| 33 | `Search-and-Network-APIs/` | Search & Network APIs | 搜尋 API、IP 定位、DNS、OCR、密碼管理 |
| 34 | `Security-and-Compliance/` | Security & Compliance | 資安、合規、隱私、安全稽核、舉報 |
| 35 | `SEO-and-Web-Analytics/` | SEO & Web Analytics | SEO 分析、流量追蹤、競品分析、關鍵字 |
| 36 | `Social-Media/` | Social Media | Facebook/IG/LinkedIn/Twitter/YouTube 等社群平台 |
| 37 | `Speech-Recognition/` | Speech Recognition | 語音轉文字、音訊轉錄、會議記錄、字幕 |
| 38 | `System-and-CLI/` | System & CLI | 系統監控、密碼管理、CLI 工具、終端機 |
| 39 | `TTS-and-Voice-AI/` | TTS & Voice AI | 文字轉語音、語音合成、語音克隆、語音代理 |
| 40 | `Video-and-Print/` | Video & Print | 照片托管、3D 模型、翻頁書、印刷品自動化 |
| 41 | `Video-Editing/` | Video Editing | 影片下載、影格擷取、影片託管、串流處理 |
| 42 | `Video-Generation/` | Video Generation | AI 影片生成、虛擬人物影片、範本化影片製作 |
| 43 | `Web-Design/` | Web Design | 前端介面設計、HTML 元件、低程式碼網站建構 |
| 44 | `Web-Scraping-and-Browser/` | Web Scraping & Browser | 網頁爬蟲、資料擷取、瀏覽器自動化、代理 IP |
| 45 | `Writing-and-Content/` | Writing & Content | 腦力激盪、內容撰寫、摘要、翻譯潤稿、命名 |

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
