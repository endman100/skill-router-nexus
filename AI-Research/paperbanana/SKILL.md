---
name: paperbanana
description: 使用 PaperBanana 開源多智慧體流程，把論文方法文字與圖說轉成學術架構圖、方法圖、流程圖與 pipeline figures。當使用者說「用 PaperBanana 畫圖」「論文配圖」「把方法章節轉成圖」「PaperBanana skill」或要求設定、執行 PaperBanana 時使用。提供官方 CLI 執行、Windows 環境設定、圖表驗收及明確標示的替代流程；數值統計圖須走程式碼繪圖。
---

# PaperBanana 學術配圖

以原作者開源專案為預設後端。先走 Skill Router 的生命週期路由；本技能提供領域執行與圖表檢查，不取代 Router 的 VERIFY 與 DELIVER。

## 1. 確定輸入與交付

- 從對話或檔案取得方法文字、圖說／表達目的、必要元件與連線、文字語言及輸出位置。
- 只追問缺少而無法推導的研究內容；不要杜撰方法、數值或模組。PDF 先抽取方法章節並核對，CLI 本身不讀 PDF。
- 將方法存為 UTF-8 method.md，避免把長文字直接拼進 shell。未指定時使用橫向 16:9、原文語言、一張候選圖、最多三輪 critic。
- 用明確的元件與有向邊清單記錄語意要求，例如 retriever → reranker → generator，作為驗收依據。
- 每次使用獨立輸出資料夾，保留來源、參數與最終 PNG；不覆寫既有成果。

## 2. 選擇執行路徑

**官方 CLI（預設）**：需要 Python 環境、原始專案與可用模型 API。首次使用或環境缺失時，讀取 [runtime.md](references/runtime.md)。先檢查環境，再執行；已配置的授權可沿用。

**宿主工具替代**：官方 API 未配置但宿主具有繪圖工具時，可先完成視覺規格並依使用者目標使用宿主工具。明確標示「PaperBanana 方法改編，非官方管線執行」。遵循宿主工具的生成規則，不宣稱已跑過官方五 Agent。一般單張生圖不是等價實作。

**指定網站**：只有使用者明確要求 paper-banana.org 才操作該服務，偏好 Chrome，依當前頁面確認功能與點數。它是獨立營運平台，不把網站訂閱視為開源專案必需條件，不猜測私有 API。

**統計圖**：使用原始資料及可檢查的 Python/Matplotlib 程式碼，經 Router 選用數值繪圖能力。不要把數值圖交給本 wrapper：已查閱版本的上游入口雖接受 plot，結果擷取仍硬編碼為 diagram。不要把圖片模型生成的柱高、刻度當成可靠資料。

## 3. 執行官方 CLI

把 <skill-dir> 替換為本檔所在資料夾，<repo> 為依 runtime.md 配置的專案目錄。wrapper 只使用 Python 標準庫；正式生成由專案虛擬環境執行。

```powershell
python '<skill-dir>/scripts/run_diagram.py' --repo '<repo>' --check
python '<skill-dir>/scripts/run_diagram.py' --repo '<repo>' --content-file '<absolute-path>/method.md' --caption 'Overview of the proposed method' --output '<absolute-path>/figure.png' --dry-run
python '<skill-dir>/scripts/run_diagram.py' --repo '<repo>' --content-file '<absolute-path>/method.md' --caption 'Overview of the proposed method' --output '<absolute-path>/figure.png'
```

- --check 只檢查環境，不發送 API 請求，不下載資料，不顯示金鑰。
- --dry-run 驗證輸入並列出參數陣列，不生成圖片；不能当成端到端成功。
- 預設一張候選、三輪 critic、auto retrieval、16:9。只有使用者需要多方案時才增加候選數。
- 可用 --main-model-name 與 --image-gen-model-name 覆蓋專案設定。模型可用性以實際帳號及目前文件為準。
- 首次生成的上游入口會下載 PaperBananaBench，即使 retrieval 選 none 也會呼叫下載檢查；不要承諾零下載。
- 多輪模型請求可能耗時數分鐘，沿用進程 session 等待並報告有意義的進度，不因等待而重啟重複計費。
- 非零退出時查看錯誤、修正原因；不要用重複生成掩蓋缺圖或依賴問題。

## 4. 檢查與有界修訂

讀取 [quality.md](references/quality.md)，打開實際生成图對照來源。檔案存在只代表輸出成功。

檢查失敗時最多再修訂兩次，只修改有證據的缺口；每輪重新驗圖，保留前一版。不能把上游 Critic 的肯定視為獨立驗證，也不能保證期刊接受或零幻覺。

## 5. 交付

展示最終圖片並提供可點擊檔案。簡述內容、實際執行路徑（官方／改編／網站）、模型與候選數、驗收結果及仍存在的錯誤。有產出但驗收失敗標為 PARTIAL；未生成時只交付視覺規格與具體缺少條件，不稱圖已完成。

來源與實作版本見 [runtime.md](references/runtime.md)。本技能為本地整合封裝，不聲稱由研究作者發布。
