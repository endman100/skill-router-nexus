# 模型與推論契約

核對日期：2026-10-01。模型選擇見同層 `model-policy.json`；選擇只排序候選，不代表執行／安裝，也不代表對使用者語料的品質定論。

## Index-Translate

使用 `IndexTeam/Index-Translate-9B` 或 `IndexTeam/Index-Translate-2B`。重用具有 Qwen3.5 支援的 vLLM、SGLang 或其他相容服務；Windows 沒有可用服務時不可假設原生 vLLM 已能運作，先確認既有 WSL／Linux runtime。不要搬入上游訓練原始碼或模型權重。

採 `/v1/chat/completions`，單一 user message，greedy `temperature=0`；未指定 top_p／top_k 時沿用後端預設。官方基本格式：

```text
请将以下{源语言}文本翻译为{目标语言}，直接输出翻译结果，不要进行任何解释。

{source_text}
```

自動辨識時省略源語言部分。明確用「繁体中文（台湾用语）」區別繁簡；語言代碼不能直接當作未驗證的模型能力。術語、僅翻可見字串、保留標記等附加要求放在原文前，同一 user message 內。這是依任務追加的指令，不假裝是未修改的官方基本測試提示。

官方主文字模型列 150 種語言；本 Skill 不維護假造的完整名單。英／中／日／韓等常見語言可以依官方範例使用；其他語對須核對當前上游支援資料並做短樣本檢查。payload helper 對不在內建常用集合的語對要求 `--verified-language-pair`，該旗標僅記錄呼叫者已核對，不會替你驗證。

官方服務指南提供 bf16 約 2B 8 GB、9B 24 GB 的部署估計，長上下文還需 KV cache；實際必須測量可用 VRAM、配置與併發。不要將權重位元數乘參數量當作完整服務記憶體需求。單張 32 GB 卡預設一次運行一個品質後端。

一般長文採本 Skill 的分塊與共享術語；不自動安裝 NativeLong／Homura／Echo，也不把主文字模型的 150 語言承諾移植到那些不同模型。

## MiLMMT-46 v1.0

使用 `xiaomi-research/MiLMMT-46-12B-v1.0`，容量受限才使用 4B／1B v1.0；不能使用 `-Pretrain` checkpoint。優先既有 vLLM 或 Transformers。使用 raw completion，不套 chat template：

```text
Translate this from <source language name> to <target language name>:
<source language name>: <source text>
<target language name>:
```

解碼 `temperature=0`、`top_k=1`，配置足夠輸出長度。相容 HTTP 服務走 `/v1/completions`；Transformers 則以 raw prompt tokenize，不加入其他模型的角色 token。

精確語言名：Arabic, Azerbaijani, Bulgarian, Bengali, Catalan, Czech, Danish, German, Greek, English, Spanish, Persian, Finnish, French, Hebrew, Hindi, Croatian, Hungarian, Indonesian, Italian, Japanese, Kazakh, Khmer, Korean, Lao, Malay, Burmese, Norwegian, Dutch, Polish, Portuguese, Romanian, Russian, Slovak, Slovenian, Swedish, Tamil, Thai, Tagalog, Turkish, Urdu, Uzbek, Vietnamese, Cantonese, Chinese (Simplified), Chinese (Traditional)。必須知道來源語言，不使用 `auto` 當作語言名稱。

基本模板不提供 Index 等同程度的任意格式／風格控制契約。不要把額外指令當作 MiLMMT 原文前綴來翻譯；以外部欄位擷取、保護標記、驗收處理結構，或改採 `instructions` 設定檔。helper 遇到 MiLMMT 加 `--constraints` 會直接報錯。

## Hy-MT2-1.8B-GGUF

模型 `tencent/Hy-MT2-1.8B-GGUF`。使用支援其 STQ 的近期 llama.cpp，或已驗證包含相容 runtime 的 Ollama。量化順序 Q8_0（約 1.91 GB）→ Q6_K（約 1.47 GB）→ Q4_K_M（約 1.13 GB）；檔案大小不等於執行記憶體。禁止對同一不相容二進位檔無限重試。

不加 system prompt。單一 user message：

```text
Translate the following text into <target language>. Note that you should only output the translated result without any additional explanation:
<source text>
```

術語可放在正文前：`Reference the following translations:`，逐行 `<source term> translates to <target term>`。解碼 `temperature=0.7`、`top_p=0.6`、`top_k=20`、`repetition_penalty=1.05`、`max_tokens=4096`；不是 MiLMMT 的 greedy 設定。

依官方表核對：Chinese, Traditional Chinese, English, French, Portuguese, Spanish, Japanese, Turkish, Russian, Arabic, Korean, Thai, Italian, German, Vietnamese, Malay, Indonesian, Filipino, Hindi, Polish, Czech, Dutch, Khmer, Burmese, Persian, Gujarati, Urdu, Telugu, Marathi, Hebrew, Bengali, Tamil, Ukrainian, Tibetan, Kazakh, Mongolian, Uyghur, Cantonese。

使用 chat template 時保留原模型模板。helper 產出 OpenAI-compatible chat payload；實際送出前，將 `model` 改成服務 `/v1/models` 回報的已驗證 alias（記錄其底層 checkpoint 與量化）。llama.cpp 原生可能把 repetition penalty 欄位叫 `repeat_penalty`；不得默默丟棄設定。若 API 不支援這些採樣欄位，在服務層設定並檢查生效。

## 執行與 provenance

記錄實際 model ID／revision（若可得）、量化、runtime、source／target、prompt 變體、解碼設定、分塊順序、finish reason，以及發生 fallback 的原因。避免在公開 log 留下原文、證件或密鑰。**payload 建立成功不是推論成功；推論成功也不是語意驗收通過。**

模型權重與 runtime 授權分開核對，不把各家模型一概說成相同授權。沿用既有私人端點時不列印其憑證，不因相容 API 名稱就要求外部商業 API 金鑰。

## 官方來源

- https://github.com/bilibili/Index-Translate/blob/main/README.md
- https://github.com/bilibili/Index-Translate/blob/main/inference/llm/README.md
- https://huggingface.co/IndexTeam/Index-Translate-9B
- https://huggingface.co/IndexTeam/Index-Translate-2B
- https://huggingface.co/xiaomi-research/MiLMMT-46-12B-v1.0
- https://github.com/xiaomi-research/gemmax
- https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF
