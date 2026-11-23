---
name: embeddinggemma-2
description: "使用 Google DeepMind 的 EmbeddingGemma 2 將文字（含程式碼）、圖像、影片與音訊轉為同一向量空間的嵌入。適用於跨模態語意搜尋、RAG 檢索、分類、聚類，以及評估向量維度與部署需求。"
---

# EmbeddingGemma 2

## 模型與適用情境

EmbeddingGemma 2 基於 Gemma 4，支援 100 多種語言，可將單一模態或交錯的多模態輸入編碼為一個向量。可用文字查詢搜尋圖像、影片或音訊，也可為 RAG 建立語意索引，或將向量用於分類與聚類。

| 規格 | 數值 |
| --- | --- |
| 參數量 | 總計 740M，含文字模型 270M、視覺編碼器 170M、音訊編碼器 300M |
| 輸入 | 文字（含程式碼）、圖像、影片、音訊，共用 8,192 token 的上下文 |
| 向量維度 | 原生 768 維，支援 Matryoshka 截短至 512、256、128 維 |

## 最小用法

1. 安裝 `sentence-transformers` 和 `transformers`，從 `sentence_transformers` 匯入 `SentenceTransformer`，以 `model = SentenceTransformer("google/embeddinggemma-2")` 載入模型。
2. 文字搜尋用 `q = model.encode(query, prompt_name="SearchQuery")` 與 `d = model.encode(document, prompt_name="Document")`，再以 `model.similarity(q, d)` 計算相似度。
3. `Document` 會套用 `title: none`。文件有標題時，將內容組成 `title: {title} | text: {content}` 後直接編碼。文字分類和聚類分別使用 `Classification` 與 `Clustering`。
4. 媒體輸入省略文字任務前綴。交錯輸入可用 `model.encode({"text": "跑鞋 <|image|>", "image": ["shoe.jpg"]})`，依序以 `<|image|>`、`<|video|>` 或 `<|audio|>` 對應各媒體項目。

## 推論與索引

- 推論精度使用 `bfloat16` 或 `float32`。`float16` 可能產生 NaN 或降低嵌入品質。
- 純文字部署可設定 `config_kwargs={"vision_config": None, "audio_config": None}`，僅載入 270M 參數的文字模型。
- 查詢與索引使用相同向量維度。截短時在 `encode()` 同時指定 `truncate_dim` 與 `normalize_embeddings=True`。256 維可將向量儲存量降至 768 維的三分之一，128 維較適合純文字。
- 影片預設每秒取樣一幀，音訊使用 16 kHz 單聲道。混合輸入的所有媒體和文字共用同一個上下文預算。

## 基準測試

以下是模型卡的全精度 768 維結果。

| 基準 | 指標 | 分數 |
| --- | --- | --- |
| MTEB multilingual v2 | 任務平均（多指標） | 61.36 |
| MTEB code v1 | 任務平均 NDCG@10 | 78.68 |
| MIEB lite | 任務類型平均（多指標） | 65.67 |
| MMEB v2 VisDoc | 任務平均 NDCG@5 | 67.84 |
| MMEB v2 Video | 任務平均 Hit@1 | 50.67 |
| MSEB Retrieval | 任務平均 MRR@10 | 69.54 |

## 授權與引用

- 模型授權為未知。模型卡要求部署遵守 Gemma Prohibited Use Policy。
- [Hugging Face 模型卡](https://huggingface.co/google/embeddinggemma-2)
- Schechter Vera、Dua 與 EmbeddingGemma Team（2026）。[EmbeddingGemma 2: Unified and Efficient Multimodal Representations（arXiv:2610.37364）](https://arxiv.org/abs/2610.37364)
