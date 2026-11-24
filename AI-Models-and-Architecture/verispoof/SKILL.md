---
name: verispoof
description: "VeriSpoof 語音偽造鑑識。用於評估合成或轉換語音的偵測、定位局部合成片段、比較兩段錄音是否由同一生成器產生，或查核生成器歸因、錄音條件及判定理由。"
---

# VeriSpoof 語音偽造鑑識

Yang Xiao 與 Ting Dang 的技術報告以同一組音訊語言模型權重處理五項任務：語音偽造偵測、生成器／聲學模型／聲碼器歸因、錄音條件分析、合成片段定位，以及雙錄音來源驗證。來源驗證比較的是生成系統，也可指定比較聲學模型或聲碼器。 [arXiv:2611.04634](https://arxiv.org/abs/2611.04634) · [論文 §3](https://arxiv.org/html/2611.04634v1#S3)

## 方法與管線

1. **編碼單段或雙段錄音**。Qwen3-ASR 編碼器處理每段 8 秒視窗。對 25 層隱狀態做可學習的加權融合，音訊 tokenizer 產生 16 個整段 token 和 52 個以 0.16 秒為單位的幀 token，每 0.8 秒插入文字時間標記。比較兩段錄音時，將 A、B 的 token 依序放在問題前。 [論文 §3.2](https://arxiv.org/html/2611.04634v1#S3.SS2)
2. **以候選答案打分**。MiniCPM5-2B 以 LoRA 微調。偵測與來源驗證的二元分數是正、負候選句的對數似然差，多選題取似然最高的候選句。兩項二元任務共用語言模型輸出。另有逐 token 分類頭，輸出合成語音的時間分布。 [論文 §3.1–3.2](https://arxiv.org/html/2611.04634v1#S3.SS1)
3. **逐欄產生可核對的理由**。以波形量測核對頻寬、訊噪比等觀察，以錄音條件紀錄、片段標註及生成器中繼資料各自核對其餘欄位。偵測先列合成片段，再下判定。雙錄音理由先給出基於來源指紋的判斷，再比對屬性，因為不同生成器可能共用聲學模型與聲碼器。 [論文 §3.3](https://arxiv.org/html/2611.04634v1#S3.SS3)
4. **分三階段訓練**。先對齊感知表徵（tokenizer 與編碼器 DoRA），再加上 LLM LoRA 微調多項鑑識問答，最後訓練理由並重播前一階段的問答。最後一階段在 20% 的理由樣本中反轉給定的定位，只監督隨之改變的判定。Base 用八個偵測語料的官方訓練切分及三個局部偽造語料，Plus 再加入十二個語料。 [論文 §3.4–4](https://arxiv.org/html/2611.04634v1#S3.SS4)

## 評測與關鍵結果

| 測試條件 | 作者報告的結果 |
| --- | --- |
| Speech-DF-Arena，14 個測試集 | Plus 2.14%、Base 4.43% pooled EER。Plus 插入 2026-10-31 公開快照後為 28 個系統中的第 3 名、開放權重第 1 名。 |
| SpoofRadar v1.0，16 個測試集 | Plus 4.04%、Base 4.23% pooled EER。 |
| MLAAD 偽造錄音配對，Plus | 同生成器驗證在已見架構的新模型上為 6.17% EER，未見架構為 15.00%。 |
| VeriSpoof-Bench，Plus | MLAAD 已見生成器的封閉集識別準確率為 96.8%，錄音條件分類準確率為 81.3%。 |
| PartialEdit，Base，同一批 500 段 | 先產生理由再判定的準確率為 99.6%，一步作答為 78.4%。 |
| Base，反事實測試 | 99.5% 的判定跟隨訓練未見措辭的反向定位，未做反事實訓練時為 73.8%。 |

Pooled EER 為合併測試集後以同一門檻計算的等錯誤率。兩個公開榜單的數字由作者依官方協議重算並自行比較。 [論文 §5–6](https://arxiv.org/html/2611.04634v1#S5)

消融顯示，音訊表徵的改動主要影響偵測，換用不同 LLM 對雙錄音比較的影響較大。等訓練步數下，來源監督在多數測試集的效果相當或未有定論，CodecFake+ 重合成子集的 EER 則從只做真偽問答的 12.62% 降至 2.24%。2.85B 參數中更新 29.7M。Base 的正式訓練使用一張 48 GB L40S，約 14 GPU 小時。各階段開啟梯度檢查點的顯存量測顯示可容納於單張 24 GB GPU。 [論文 §6.3、§6.5、§6.9](https://arxiv.org/html/2611.04634v1#S6.SS3)

## 限制與採用判斷

- **門檻與錄音條件**。Plus 在 SpoofRadar 的共用門檻下，將 XMAD-Bench 的 92.9% 俄語真實有聲書錄音判為偽造。換語言或領域時依目標域真實錄音設定門檻。帶雜訊、混響或編碼影響的雙錄音，Plus 的來源驗證 EER 約 23–30%。 [論文 §6.1–6.2](https://arxiv.org/html/2611.04634v1#S6.SS1)
- **短片段與證據核對**。Base 在 PartialSpoof、LlamaPartialSpoof 的文字定位 IoU 為 0.25、0.31，逐 token 分類 F1 為 0.74、0.82。反事實測試衡量判定是否跟隨指定定位，定位正確性需另和標註核對。真實案件中缺少片段標註或生成器中繼資料時，記錄哪些欄位仍待獨立查核，並由人工綜合其他證據。 [論文 §6.6、§6.8](https://arxiv.org/html/2611.04634v1#S6.SS6) · [專案頁](https://swagshaw.github.io/verispoof/)
- **工程推論與未驗證應用**。可先用一步分數篩查，再以文字定位和逐 token 分數找出待複核片段。若要涵蓋長錄音，可試行保留原始時間偏移的重疊分窗。此長錄音彙整策略的量化效能為未知／未公開（2026-11-24）。

## 相關既有 skill

- 若同時需要提取逐字稿或詞級時間戳，使用 [ASR Router](../../Speech-Recognition/asr-router/SKILL.md)。
- 若錄音屬於資安事件證據，可依 [Digital Forensics](../../Security-and-Compliance/digital-forensics/SKILL.md) 的原件保全、雜湊與副本流程處理。

## 來源與釋出狀態

- 方法、圖表與實例。 [Hugging Face 論文頁](https://huggingface.co/papers/2611.04634) · [arXiv 摘要](https://arxiv.org/abs/2611.04634) · [arXiv 全文](https://arxiv.org/html/2611.04634v1) · [官方專案頁](https://swagshaw.github.io/verispoof/)
- 推論套件（含 vLLM 後端）及權重已公開，採 CC BY-NC 4.0。訓練程式為未知／未公開（2026-11-24）。 [官方 GitHub](https://github.com/swagshaw/verispoof) · [Base](https://huggingface.co/AustinXiao/VeriSpoof-Base) · [Plus](https://huggingface.co/AustinXiao/VeriSpoof-Plus) · [官方 Demo](https://huggingface.co/spaces/AustinXiao/VeriSpoof-demo)
- VeriSpoof-Bench 有 54 個子集、177,852 筆項目，公開清單、標註、重建與評分腳本及兩版模型輸出，音訊需自原語料取得。 [VeriSpoof-Bench](https://huggingface.co/datasets/AustinXiao/VeriSpoof-Bench)
