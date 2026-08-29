---
name: flow-matching-data-scaling
description: Apply the Abra scaling-law result when sizing datasets and models for text-to-image Flow Matching training. Use when estimating compute-optimal image-token budgets, choosing model parameter count, or deciding between a smaller data-rich model and a larger data-starved model.
---

# Flow Matching Data Scaling

## Core rule

For modern text-to-image Flow Matching Transformers, use this empirical planning prior:

`image tokens ≈ 200 × trainable parameters`

If the available data budget is `D` image tokens, start model-size planning near `N ≈ D / 200` parameters.

When the estimate is uncertain, prefer a smaller model trained on more data over a larger model trained with insufficient data. The study found diffusion training relatively robust to overtraining, while data starvation is the riskier side.

## Guardrails

- Count image tokens, not raw image count; token count depends on resolution and the image representation/tokenization scheme.
- Treat `200` as an empirical prior for the studied Flow Matching text-to-image setting, not a universal constant for every vision architecture or training recipe.
- Validate the final allocation with small scaling sweeps when the compute budget permits.

## Source

Abra was evaluated as a controlled family of Flow Matching Transformers across roughly `10^19` to `10^22` training FLOPs.

- [Abra: Scaling Diffusion Image Training — arXiv](https://arxiv.org/abs/2608.17286)
- [Hugging Face paper page](https://huggingface.co/papers/2608.17286)
