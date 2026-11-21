---
name: flomss-music-source-separation
description: "FLOMSS（Flow Matching for Music Source Separation，arXiv:2610.17821）生成式音樂音源分離研究與 MV 人聲去除選型評估。涵蓋 conditional flow matching、音樂分離、MV 人聲去除、伴奏提取、vocal removal、music source separation，以及與 HTDemucs、SCNet 在聽感、Mel 距離與 SDR 上的取捨分析。"
---

# FLOMSS：基於 Flow Matching 的生成式音樂音源分離與 MV 人聲去除選型評估

本條目整理論文 **《Flow Matching for Music Source Separation》（FLOMSS，arXiv:2610.17821）** 的方法設計、MUSDB18-HQ 實驗證據、官方儲存庫現況查核，以及針對「MV 初步濾除人聲／提取伴奏」任務的實務採用評估。本檔為外部研究簡易包裝，未在本環境執行實機推論或盲聽測試。

- **查核日期**：`2026-11-21`
- **中英檢索關鍵詞**：`FLOMSS`、`flow matching`、`音樂分離`、`音樂分軌`、`MV`、`人聲去除`、`伴奏`、`vocal removal`、`music source separation`、`OT-CFM`、`HTDemucs`、`SCNet`

---

## 核心方法與模型架構

- **生成式音源分離框架**：FLOMSS 使用 **conditional flow matching**，在壓縮後的 **complex STFT** 表示空間上進行生成式分離，選用 **OT-CFM（Optimal Transport Conditional Flow Matching）+ x-prediction** 參數化。
- **音訊規格與分離目標**：處理 **44.1 kHz 立體聲（stereo）** 音樂，分離四大常見音軌（stems）：`Vocals`、`Bass`、`Drums`、`Other`。
- **FLOMSS-M 模型規模與推論設定**：
  - 採用 **4 個獨立的單一來源模型**（每個來源約 `67M` 參數，4 個模型合計約 `268M` 參數）。
  - 推論使用 **10-step Midpoint ODE solver**。
  - **實驗結論**：研究顯示 4 個單來源獨立模型表現最佳；聯合 4 來源（joint 4-stem）建模與強制硬性混合一致性（hard mixture consistency）在該研究中並未帶來更好的整體表現。

---

## MUSDB18-HQ 實驗結果與核心取捨

以下數據引自論文在 **MUSDB18-HQ** 上的報告結果（不同比較模型所使用的訓練資料範圍存在差異，比較時須一併考量）：

| 模型 | 主觀聽測分數（越高越好） | SDR (dB，越高越好) | Mel 距離（越低越好） |
| --- | --- | --- | --- |
| **FLOMSS-M** | `59.12` | `4.34` | **`1.55`** |
| **SCNet** | **`62.59`** | **`9.69`** | `1.66` |
| **HTDemucs** | `58.71` | `8.14` | `1.61` |

### 聽測設計與統計解讀限制

- **主觀聽測規模**：共 **23 位受試者**、**10 段 8 秒音訊片段**。
- **名次觀察**：FLOMSS-M 在整體主觀分數排名第二（`59.12`，介於 SCNet `62.59` 與 HTDemucs `58.71` 之間），並在 **Bass** 單項主觀評分排名第一。
- **嚴格解讀邊界**：由於樣本數與片段數有限，**不可將微小分差或單項名次直接視為統計顯著，亦不能泛稱 FLOMSS 為「最佳模型」**。
- **核心技術取捨**：生成式 Flow Matching（FLOMSS）展現的是 **「主觀聽感與頻譜／分布相似度（如 Mel 距離較優 `1.55`）」對比「原始波形精確逐點還原（傳統 SDR 顯著較低，僅 `4.34 dB`）」** 的核心取捨。

---

## 官方儲存庫（`ik4sumii/FLOMSS`）現況查核

- **查核時間**：`2026-11-21`（二次核對 GitHub API 檔案列表）
- **目前倉庫內容**：僅包含展示頁與音訊處理輔助檔案（`.gitignore`、`audio/`、`generate_results_data.py`、`generate_waveforms.py`、`index.html`、`prepare_demo_audio.py`、`results_data.js`、`waveforms.js`）。
- **缺件與部署狀態**：**目前尚未釋出完整的模型訓練程式碼、推論程式碼與預訓練權重**（論文註明將於論文接受後公開）。
- **重要提醒**：**不得將目前的 `ik4sumii/FLOMSS` 展示倉庫當成可直接部署或執行的音源分離實作**。

---

## MV 初步人聲去除／伴奏提取：實務選型與流程建議

針對使用者「**常見 MV 只要初步濾掉人聲（保留伴奏並配回畫面）**」的具體應用需求，評估結論如下：

### 1. 任務定性與模型選型建議

- **任務適用性**：此需求適合採用 **音樂音源分離（music source separation / 音樂分軌）** 路線。
- **現階段優先選型**：由於 FLOMSS 尚未公開權重與推論程式，且 MV 去人聲通常重視穩定分離與相位／波形一致性，**目前實務上應優先採用已有成熟開源權重與推論工具的 `HTDemucs` 或 `SCNet`**，而非等待或誤用 FLOMSS 展示倉庫。

### 2. 標準處理流程（建議管線）

1. **抽取音訊**：從原始 MV 影片（如 MP4）無損抽取 44.1 kHz 立體聲音軌。
2. **四軌分離**：使用 `HTDemucs` 或 `SCNet` 分離出 `vocals`、`drums`、`bass`、`other`。
3. **合成伴奏**：將非人聲軌（`drums + bass + other`）混合（或視模型支援直接輸出 `no_vocals`／伴奏軌）。
4. **封裝配回畫面**：將混合後的伴奏音軌與原始 MV 視訊軌重新封裝（mux），保持影音時間軸同步。

### 3. 評估性質與實務限制（風險揭露）

- **未經實機驗證聲明**：上述管線為基於模型特性與開源可用性的**工程採用建議**，本條目建立時**未針對特定 MV 進行實機推論或盲聽驗證**。
- **常見分離瑕疵**：
  - **人聲殘留**：濃厚和聲（backing vocals）、大合唱（choir）、長殘響（reverb/delay 尾音）容易被分配至 `other` 軌而殘留。
  - **樂器損傷**：與人聲頻段高度重疊的主奏吉他、合成器或銅管樂器可能出現頻段凹陷、相位失真或水聲（musical noise）。
  - **MV 非音樂聲源**：劇情類或現場版 MV 常包含額外對白、環境音效（SFX）、掌聲或現場歡呼聲；純音樂四軌分離模型（MUSDB18 定義）未針對電影／現場對白與 SFX 專門訓練，若 MV 含大量非音樂對白或音效，需另行檢查或評估結合 `speech / music / sfx` 三分軌模型（如 DnR 路線）。

---

## 原始論文與專案連結

- **Hugging Face Paper 頁面**：https://huggingface.co/papers/2610.17821
- **arXiv HTML 全文**：https://arxiv.org/html/2610.17821
- **arXiv 摘要頁**：https://arxiv.org/abs/2610.17821
- **官方展示頁面（Demo Page）**：https://ik4sumii.github.io/FLOMSS/
- **官方 GitHub 倉庫（目前僅含展示頁與音訊樣本）**：https://github.com/ik4sumii/FLOMSS
