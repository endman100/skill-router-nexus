---
name: game-development-workflow
description: Plan, review, or adapt an end-to-end game development lifecycle with stage gates, milestones, deliverables, PM checks, testing loops, and live-operations feedback. Use when a user asks to 規劃遊戲從立項到上線的流程、建立遊戲開發 roadmap、審查製作里程碑與 Gate、定義原型或 Vertical Slice、安排 GDD/TDD 與 Alpha/Beta/Gold、規劃 DLC／Early Access，或建立長線營運與版本迭代流程。
---

# Game Development Workflow

以「階段閘門＋迭代回饋」組織遊戲研發。先證明值得做與做得出來，再擴大製作；每個 Gate 都以證據決策，而非只看日期。

## 工作流程

1. 收集產品型態、平台、商業模式、團隊規模、預算／時程與連線需求。資訊不足時標記假設並繼續，不因非關鍵缺口停住。
2. 依五階段建立主線：立項、前期製作、正式開發、測試、發布與持續研發。
3. 為每階段列出目標、主要活動、責任角色、產出物、Gate 證據與返工路徑。
4. 設定四個預設里程碑：正式立項、首次可玩版、Alpha、正式發布。依專案需要拆分 Beta、Early Access、Gold、Soft Launch 或公測。
5. 把玩法、技術、內容、品質、商業與營運風險放進相應 Gate；指定負責人、驗證方法及未通過時的回流點。
6. 交付使用者需要的格式，例如階段表、roadmap、Gate checklist、風險清單或結構流程圖。

需要完整的階段定義、產出物、PM 檢查及產品型態調整規則時，讀取 [references/stage-gates.md](references/stage-gates.md)。

需要流程圖時，以 [assets/game-development-workflow.mmd](assets/game-development-workflow.mmd) 為可編輯基線；先依專案型態刪改節點，再透過 Router 選用合適的圖表技能進行驗證或渲染。

## 預設主線

`市場調研 → 遊戲概念 → 可行性分析 → 立項 Gate → 快速原型 → 首次可玩版／Vertical Slice → GDD＋TDD → Alpha → QA／Beta → Release Gate → 發布 → 版本與社群回饋迭代`

## 操作規則

- 把「核心玩法可驗證」放在大量內容與高品質美術投入之前。
- 把 Gate 寫成可觀察的通過條件；避免使用「差不多完成」等模糊描述。
- 保留返工迴圈。玩法不成立回到產品支柱，品質不穩定回到製作／QA，營運回饋回到版本迭代。
- 將 `TDD` 解讀為 Technical Design Document；若使用者指 Test-Driven Development，明確區分。
- 把 Early Access 視為選配策略，不當作所有遊戲的必經階段。
- 依單機、長線網路、F2P 手遊或獨立遊戲調整發布節點，不強行合併公測、Gold 與正式上線。
- 區分「功能完成」「內容完成」「品質穩定」「商業可發布」，避免只用單一完成百分比管理專案。

## 預設交付格式

依序提供：

1. 一句話產品與當前階段判定。
2. 階段／里程碑／Gate 表。
3. 下一個 Gate 的通過條件與必要證據。
4. 目前風險、負責人與返工路徑。
5. 已採用的假設，以及需要使用者決策的事項。

## 完成條件

- 五階段均有明確目標與產出物，或已說明刪除原因。
- 每個主要 Gate 都有通過條件、證據、決策者與未通過路徑。
- 四個預設里程碑已保留或被明確替換。
- 測試與上線後回饋形成閉環。
- 流程符合產品型態、團隊能力、預算與發布策略。
