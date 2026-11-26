---
name: r2t2
description: "用於查閱或評估網易有道 Confucius4-R2T2 串流語音辨識模型、以最長穩定前綴（LSP）改造全上下文 ASR，或比較即時字幕、同傳前端與語音代理所需的提交穩定性、辨識錯誤率及延遲。"
---

# Confucius4-R2T2 串流語音辨識

Confucius4-R2T2（Real Real-Time Transcription）是網易有道的穩定前綴 ASR 模型。同一份權重支援串流與離線轉錄。串流發布端只追加已提交文字，適合讓字幕、同傳系統與語音代理逐步消費文字。 [專案頁](https://r2t2.ai/) · [論文](https://arxiv.org/abs/2611.06043)

## 模型架構

- 沿用 Qwen3-ASR-1.7B 的 AuT 音訊編碼器、投影器和 Qwen3-1.7B 語言解碼器。AuT 約 300M 參數、隱藏維度 1,024。128 維 log-Mel 特徵每 10 ms 一幀，經 8 倍下採樣後每 80 ms 產生一個音訊 token（12.5 Hz）。
- 音訊注意力在 1–8 秒視窗內維持雙向。兩個後訓練階段皆凍結編碼器與投影器，只更新語言解碼器。架構沿用原有層與輸出頭，`Wait` 由同一詞彙表預測。 [論文 §4.2、§6、附錄 B](https://arxiv.org/html/2611.06043v1#S4.SS2)
- 標準 checkpoint 為 BF16 Safetensors，Hugging Face 標示整體約 2B 參數。官方另提供 FP16、Q8_0 與 Q4_K_M GGUF。 [模型卡](https://huggingface.co/netease-youdao/Confucius4-R2T2) · [GGUF 模型卡](https://huggingface.co/netease-youdao/Confucius4-R2T2-GGUF)

## 方法與訓練管線

1. **建立 LSP 標籤**。用同一基底模型轉錄完整錄音及每隔 80 ms 截出的累積音訊。在每個時點，從當前與更早的候選中，找出整段 token 序列皆為完整錄音轉錄前綴的最長候選。候選尾端若分歧，該候選整段不採用。論文證明標籤單調增長，最後與基底的全音訊輸出一致。 [論文 §4.3、§5.2](https://arxiv.org/html/2611.06043v1#S4.SS3)
2. **標註等待區間**。合併連續且候選與 LSP 相同、前綴維持不變的時點。穩定區間內用 LSP 當目標，區間外加上 `Wait`。完整音訊樣本沿用原本的完整參考逐字稿，保留離線辨識訓練目標。 [論文 §5.2](https://arxiv.org/html/2611.06043v1#S5.SS2)
3. **先 SFT，再 GRPO**。後訓練用約 1,500 小時專有音訊，中文與英文各 30 萬句，增強包含純噪音、混噪、混響與語言標籤翻轉。SFT 以交叉熵做一輪訓練，完整句占 10%，其餘截點在穩定區間與間隙各半。GRPO 每個提示採樣 8 條軌跡，涵蓋 1、2 或 4 次串流更新，以 CER 為主要訊號，另處理重複、語言不一致、過早續寫及 `Wait` 位置。 [論文 §5–6、附錄 B](https://arxiv.org/html/2611.06043v1#S5)

## 推論管線

1. **設定更新頻率**。依後端文件輸入 16 kHz 單聲道音訊。串流步長為 80 ms 的倍數，官方文件列出 80 ms 至 2 s，主評測用 160 ms。`U=1` 保留一個可修訂的尾端 token 以提高辨識品質，`U=0` 優先降低延遲。兩種設定皆只對外發布已提交文字。 [論文 §7–8](https://arxiv.org/html/2611.06043v1#S7) · [官方快速入門](https://github.com/netease-youdao/Confucius4-R2T2#quick-start)
2. **在音訊更新時解碼與提交**。論文的推論流程重編碼當前 8 秒視窗，重用已完成視窗的編碼和其前方的解碼器 KV cache，重新預填變動音訊與保留文字。主評測保留一個已完成視窗，連同當前視窗最多 16 秒。若預填後立即預測 `Wait`，此次更新直接結束，否則貪婪解碼至 `Wait` 或 EOS。預填可驗證尚未提交的尾端 token。 [論文 §7](https://arxiv.org/html/2611.06043v1#S7)
3. **接收已提交輸出**。vLLM 範例的第二個回傳值是已提交的累積前綴，WebSocket 的 `text` 則是本次新增文字。`Wait` 結束當前解碼步，音訊結束時另做 flush。官方亦提供 Transformers 離線推論與 llama.cpp 後端。 [官方 Python API 與 WebSocket 文件](https://github.com/netease-youdao/Confucius4-R2T2#python-api)

## 基準與關鍵結果

作者主評測對 8 個英文測試集的詞錯誤率（WER）與 5 個中文測試集的字元錯誤率（CER）按資料集等權重取宏平均。 [論文 §8、表 3](https://arxiv.org/html/2611.06043v1#S8.T3)

| 設定 | 主評測宏平均 |
| --- | ---: |
| Qwen3-ASR-1.7B，全上下文離線參考 | 5.15% |
| Qwen3-ASR-1.7B，160 ms、U=1 | 21.01% |
| R2T2，160 ms、U=1 | **5.76%** |
| R2T2，160 ms、U=0 | 6.40% |

- 長音訊 EN-RealSI 與 CN-RealSI 的 R2T2 160 ms、U=1 結果分別為 7.33% WER 和 3.27% CER。另有後訓練未涵蓋的 10 種語言、18 個測試集，同設定宏平均為 8.40%，基底同設定為 30.75%。 [論文表 3、附錄 C](https://arxiv.org/html/2611.06043v1#A3) · [RealSI 資料說明](https://github.com/byteresearchcla/RealSI)
- 80 ms、U=0 時，中英文平均回溯式輸出延遲皆低於 0.5 秒，辨識錯誤率較高。這項延遲沿音訊時間軸計算，只計對齊匹配的詞或字，排除高錯誤率樣本、執行、排隊、傳輸和渲染時間。 [論文 §8.1、§8.3](https://arxiv.org/html/2611.06043v1#S8.SS3)

## 限制與採用判斷

- 提交穩定性只約束輸出會持續追加。已提交的誤辨識也會保留。LSP 以基底生成的完整轉錄為錨點，任一 token 分歧便可能延後提交。BPE 下文字前綴相同時，仍需核對 token 序列。 [論文 §4.3、§8.3](https://arxiv.org/html/2611.06043v1#S4.SS3)
- 官方 vLLM 範例重新傳入累積音訊，實際效能應依選用的後端和推論路徑評估。端到端延遲與高併發吞吐的論文實測為未知／未公開（2026-11-26）。 [公開推論實作](https://github.com/netease-youdao/Confucius4-R2T2/blob/master/r2t2/r2t2_asr.py) · [論文 §8.1](https://arxiv.org/html/2611.06043v1#S8.SS1)
- **工程推論，論文未驗證**。移植 LSP 到其他基底時，可先抽樣檢查 LSP 增長曲線及全音訊轉錄品質，再以目標語料檢查錯誤率、逐次提交的前綴關係，以及應用端實測延遲。

## 釋出、授權與來源

- 公開推論程式採 Apache-2.0。公開權重（含 GGUF）採網易有道模型使用許可協議，含再分發義務。中文版第 2.2 條規定，使用者或關聯方上月月活躍使用者超過 1 億，或去年年營收超過人民幣 1 億元，須另行申請商業許可。英文版年營收門檻寫為人民幣 10 億元，第 9 條指明以中文版為準。 [官方 GitHub](https://github.com/netease-youdao/Confucius4-R2T2) · [程式授權](https://github.com/netease-youdao/Confucius4-R2T2/blob/master/LICENSE) · [模型授權中版](https://github.com/netease-youdao/Confucius4-R2T2/blob/master/MODEL_LICENSE_zh) · [模型授權英版](https://github.com/netease-youdao/Confucius4-R2T2/blob/master/MODEL_LICENSE)
- 完整後訓練音訊、LSP 訓練標註和訓練程式為未知／未公開（2026-11-26）。論文附錄公布訓練設定與評測語料，作者的 Hugging Face 帳號未列出公開資料集。 [論文附錄 B–C](https://arxiv.org/html/2611.06043v1#A2) · [作者的資料集頁](https://huggingface.co/netease-youdao/datasets)
- [論文全文](https://arxiv.org/html/2611.06043v1) · [Hugging Face 模型卡](https://huggingface.co/netease-youdao/Confucius4-R2T2) · [ModelScope 模型卡](https://modelscope.cn/models/netease-youdao/Confucius4-R2T2) · [作者發布說明](https://huggingface.co/papers/2611.06043) · [官方 Demo](https://r2t2.youdao.com/demo) · [官方串流回放](https://r2t2.youdao.com/examples/)
