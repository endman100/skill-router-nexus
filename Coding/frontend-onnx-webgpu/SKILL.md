---
name: frontend-onnx-webgpu
description: Build pure frontend ONNX WebGPU tools for large browser-hosted models. Use when implementing or documenting ONNX Runtime Web, WebGPU, OPFS model caching, HTTP Range downloads, Hugging Face model loading, progress UI, and browser-only inference workflows.
---

# Frontend ONNX WebGPU

## 使用時機

當任務需要在純瀏覽器環境建置、移植、除錯或文件化大型 ONNX 模型工具時，使用本 skill。

適用情境：

- 建置純前端 ONNX 推理工具。
- 使用 ONNX Runtime Web 與 WebGPU 執行模型。
- 從 Hugging Face 或其他遠端來源下載大型模型。
- 需要 OPFS、Cache API 或 HTTP Range Request 處理大型檔案快取。
- 需要設計模型下載、快取、session 建立與推理狀態 UI。
- 需要讓工具不依賴後端推理服務。

## 目標

目標是讓大型 ONNX 模型能在純瀏覽器環境中穩定下載、快取、載入與執行。

## 技術面

| 技術 | 簡單描述 |
|---|---|
| 純前端 Web App | 所有下載、快取、推理、輸出都在瀏覽器內完成，不依賴後端推理服務。 |
| ONNX Runtime Web | 在瀏覽器中執行 ONNX 模型，統一管理模型 session 與 tensor 推理。 |
| WebGPU | 使用 GPU 加速模型推理，作為主要運算後端。 |
| WASM fallback | 當部分運算無法走 WebGPU 時，保留 WASM 作為備援後端。 |
| Hugging Face 模型來源 | 從 Hugging Face repo 取得模型與相關資源，方便版本管理與公開部署。 |
| OPFS | 使用瀏覽器 Origin Private File System 快取大型模型檔，降低重複下載與記憶體壓力。 |
| HTTP Range Request | 分段下載大檔，避免一次載入完整模型造成 Chrome renderer 記憶體暴衝。 |
| Cache API | 作為 OPFS 不可用或失敗時的備援快取方式。 |
| 動態載入 Runtime | 開頁先準備模型資源，需要建立 session 時再載入 ONNX Runtime。 |
| Progress UI | 顯示模型下載、快取、session 建立與執行狀態，讓使用者知道目前進度。 |
| Run Log | 保留執行過程紀錄，方便除錯模型下載、session 建立與推理流程。 |
| 本地設定檔 | tokenizer、scheduler、manifest 等輔助設定由工具本地提供，避免每次都依賴遠端小檔。 |
| 模組化前端結構 | HTML / CSS / JS 分離，工具放在獨立資料夾中，方便複製到其他工具專案。 |
| 進度條顯示 | 顯示模型下載、快取、session 建立與執行狀態的進度條，提升使用者體驗。 |

## 實作要求

### 1. 架構

- 使用純前端 HTML / CSS / JavaScript，除靜態檔案服務外不依賴後端推理服務。
- 工具應放在獨立資料夾，至少包含 `index.html`、`style.css`、`index.js` 或同等檔案。
- tokenizer、scheduler、manifest、model metadata 等小型設定檔優先放在工具本地。
- 遠端模型來源應明確寫在常數或 manifest 中，避免散落在多處。

### 2. ONNX Runtime Web

- 固定 ONNX Runtime Web 版本，避免 CDN 自動升版造成不可預期回歸。
- 優先使用 WebGPU execution provider，並保留 WASM fallback。
- 大型模型應序列化建立 session，避免同時建立多個 session 導致瀏覽器記憶體暴衝。
- Runtime 可動態載入：開頁先檢查環境與準備資源，需要建立 session 時再載入 runtime。

### 3. 模型下載與快取

- 大型模型優先使用 OPFS 快取。
- 伺服器或遠端模型來源需支援 HTTP Range Request，讓大檔能分段下載。
- OPFS 不可用或失敗時，可使用 Cache API 作為備援。
- 不要在背景 prefetch 與 ONNX Runtime session create 同時下載同一批大模型。
- 對於大型檔案，避免一次性 `arrayBuffer()` 讀完整檔進 JavaScript heap，除非檔案大小已確認可接受。
- 提供清除模型快取操作，方便模型更新、HF repo 更換或除錯。

### 4. UI 與狀態

- 顯示模型下載、快取、session 建立與推理狀態。
- 使用 progress bar 顯示大檔下載進度。
- 使用 Run Log 保留每個主要步驟與錯誤訊息。
- Generate / Run 按鈕在模型尚未準備好時應 disabled。
- 發生錯誤時要清楚顯示可理解的錯誤訊息，不只丟 console。

## 驗證清單

完成前至少確認：

- 頁面可在一般 Chrome 開啟。
- `navigator.gpu` 可用時會使用 WebGPU。
- `navigator.storage.getDirectory` 可用時會使用 OPFS。
- 大型模型下載採用分段下載或等效低記憶體策略。
- 模型下載完成後，重新整理頁面不會重新完整下載同一批檔案。
- ONNX Runtime session 能建立成功。
- 推理結果能輸出到對應 UI。
- Progress UI 與 Run Log 狀態不殘留在錯誤或 loading 狀態。
- 清除快取後可以重新下載並恢復執行。

## 常見反模式

- 開頁就同步建立所有大型 ONNX session。
- 同時下載多個大模型檔並同時建立 session。
- 使用 `<link rel="prefetch">` 下載超大型模型，導致背景下載與 session create 互搶資源。
- 對 GB 級模型直接 `response.arrayBuffer()`，造成 renderer 記憶體暴衝。
- 沒有固定 ONNX Runtime Web 版本。
- 只依賴 console log，沒有在 UI 顯示進度或錯誤。
- 沒有清除快取功能，導致替換模型後仍使用舊檔。
