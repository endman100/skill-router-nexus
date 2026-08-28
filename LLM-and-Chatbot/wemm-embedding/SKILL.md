---
name: wemm-embedding
description: Use Tencent WeMM-Embedding to create unified embeddings for text, images, videos, visual documents, and interleaved multimodal inputs. Use when implementing multimodal retrieval, semantic search, RAG, similarity scoring, Matryoshka dimension truncation, or serving WeMM-Embedding with Sentence Transformers, Transformers, vLLM, or SGLang. Do not use for audio embedding because WeMM-Embedding does not currently support audio.
---

# WeMM Embedding

Use Tencent WeMM-Embedding for multimodal representation and retrieval. Prefer the official Sentence Transformers integration for a concise local workflow.

Official source: <https://github.com/Tencent/WeMM-Embedding>

## Choose a model

| Model | Supported Matryoshka dimensions |
|---|---|
| `tencent/WeMM-Embedding-2B` | 64, 128, 256, 512, 1024, 2048 |
| `tencent/WeMM-Embedding-4B` | 64, 128, 256, 512, 1024, 2560 |
| `tencent/WeMM-Embedding-9B` | 64, 128, 256, 512, 1024, 2048, 4096 |

Choose according to available memory, latency, and measured retrieval quality. Start with 2B when no model size is specified.

## Install

Use the versions pinned by the upstream repository for reproducible preprocessing:

```bash
pip install torch "transformers==5.2.0" "qwen-vl-utils[decord]==0.0.14" "sentence-transformers==5.7.0" "accelerate>=1.1.0"
```

## Encode queries and documents

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "tencent/WeMM-Embedding-2B",
    trust_remote_code=True,
    device="cuda",
)

queries = ["Which document explains this chart?"]
documents = [
    "A text-only document.",
    {"image": "/path/to/chart.png", "text": "Represent this image."},
    {"video": "/path/to/demo.mp4", "text": "Represent this video."},
]

query_embeddings = model.encode_query(
    queries,
    truncate_dim=256,
    normalize_embeddings=True,
    convert_to_tensor=True,
)
document_embeddings = model.encode_document(
    documents,
    truncate_dim=256,
    normalize_embeddings=True,
    convert_to_tensor=True,
)

scores = model.similarity(query_embeddings, document_embeddings)
print(scores)
```

Use `model.encode()` when independent embeddings are sufficient. Inputs may be strings, paths or URLs, `PIL.Image` objects, multimodal dictionaries, or chat-style message structures. In multimodal dictionaries, place `image` or `video` before `text` to match the upstream prompt ordering.

## Apply Matryoshka dimensions

Use only a dimension supported by the selected model. With Sentence Transformers, pass both `truncate_dim` and `normalize_embeddings=True`. When truncating tensors manually, L2-normalize again:

```python
import torch.nn.functional as F

embedding_256 = F.normalize(full_embedding[..., :256], dim=-1)
```

Do not compare vectors produced with different dimensions or normalization rules.

## Serve the model

- For vLLM, follow the upstream pooling runner configuration and use the model's `embedding_chat_template.jinja`. The repository documents vLLM `0.27.0`.
- For SGLang, apply the upstream video patch before launching with embedding mode. The repository documents SGLang `0.5.9`.
- Recheck the official repository before changing serving versions because preprocessing behavior may differ.

## Constraints

- Do not send audio inputs; audio is not supported.
- Treat `trust_remote_code=True` as code execution. In security-sensitive or production environments, review the model repository and pin a trusted revision.
- Keep preprocessing, embedding dimension, normalization, and similarity metric identical for queries and indexed documents.
- Batch conservatively for image and video inputs because their memory cost is substantially higher than text-only inputs.
