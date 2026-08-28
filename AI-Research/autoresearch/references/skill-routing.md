# Skill Routing: When to Use Which Domain Skill

The autoresearch skill orchestrates — domain skills execute. This reference maps research activities to the skills library.

## Routing Principle

When you encounter a domain-specific task during research, read the repository's root `SKILL.md`, scan the relevant categories with `skill_reader.py`, and then load the selected skill. The paths below are Router-relative locations in this repository.

## Complete Routing Map

### Data and Preprocessing

| Task | Skill | Location |
|---|---|---|
| Large-scale data processing | Ray Data | `AI-Training/ray-data/` |
| Data curation and filtering | NeMo Curator | `AI-Training/nemo-curator/` |
| Custom tokenizer training | HuggingFace Tokenizers | `AI-Models-and-Architecture/huggingface-tokenizers/` |
| Subword tokenization | SentencePiece | `AI-Models-and-Architecture/sentencepiece/` |

### Model Architecture and Training

| Task | Skill | Location |
|---|---|---|
| Large-scale pretraining | Megatron-Core | `AI-Training/megatron-core/` |
| Lightweight LLM training | LitGPT | `AI-Training/litgpt/` |
| State-space models | Mamba | `AI-Models-and-Architecture/mamba/` |
| Linear attention models | RWKV | `AI-Models-and-Architecture/rwkv/` |
| Small-scale pretraining | NanoGPT | `AI-Models-and-Architecture/nanogpt/` |

### Fine-tuning

| Task | Skill | Location |
|---|---|---|
| Multi-method fine-tuning | Axolotl | `AI-Training/axolotl/` |
| Template-based fine-tuning | LLaMA-Factory | `AI-Training/llama-factory/` |
| Fast LoRA fine-tuning | Unsloth | `AI-Training/unsloth/` |

### Post-training (RL / Alignment)

| Task | Skill | Location |
|---|---|---|
| PPO, DPO, SFT pipelines | TRL | `AI-Training/trl-fine-tuning/` |
| Group Relative Policy Optimization | GRPO | `AI-Training/grpo-rl-training/` |
| Scalable RLHF | OpenRLHF | `AI-Training/openrlhf/` |
| Reference-free alignment | SimPO | `AI-Training/simpo/` |

### Interpretability

| Task | Skill | Location |
|---|---|---|
| Transformer circuit analysis | TransformerLens | `AI-Research/transformer-lens/` |
| Sparse autoencoder training | SAELens | `AI-Research/saelens/` |
| Intervention experiments | NNsight | `AI-Research/nnsight/` |
| Causal tracing | Pyvene | `AI-Research/pyvene/` |

### Distributed Training

| Task | Skill | Location |
|---|---|---|
| ZeRO optimization | DeepSpeed | `AI-Training/deepspeed/` |
| Fully sharded data parallel | FSDP2 | `AI-Training/pytorch-fsdp2/` |
| Multi-GPU abstraction | Accelerate | `AI-Training/accelerate/` |
| Training framework | PyTorch Lightning | `AI-Training/pytorch-lightning/` |
| Distributed data + training | Ray Train | `AI-Training/ray-train/` |

### Evaluation

| Task | Skill | Location |
|---|---|---|
| Standard LLM benchmarks | lm-evaluation-harness | `AI-Evaluation-and-Benchmarking/lm-evaluation-harness/` |
| NeMo-integrated evaluation | NeMo Evaluator | `AI-Evaluation-and-Benchmarking/nemo-evaluator/` |

### Inference and Serving

| Task | Skill | Location |
|---|---|---|
| High-throughput serving | vLLM | `AI-Inference-and-Optimization/vllm/` |
| NVIDIA-optimized inference | TensorRT-LLM | `AI-Inference-and-Optimization/tensorrt-llm/` |
| CPU / edge inference | llama.cpp | `AI-Inference-and-Optimization/llama-cpp/` |
| Structured generation serving | SGLang | `AI-Inference-and-Optimization/sglang/` |

### Experiment Tracking

| Task | Skill | Location |
|---|---|---|
| Full experiment tracking | Weights & Biases | `AI-MLOps/weights-and-biases/` |
| Open-source tracking | MLflow | `AI-MLOps/mlflow/` |
| Training visualization | TensorBoard | `AI-MLOps/tensorboard/` |

### Optimization Techniques

| Task | Skill | Location |
|---|---|---|
| Efficient attention | Flash Attention | `AI-Inference-and-Optimization/flash-attention/` |
| 4/8-bit quantization | bitsandbytes | `AI-Inference-and-Optimization/bitsandbytes/` |
| GPTQ quantization | GPTQ | `AI-Inference-and-Optimization/gptq/` |
| AWQ quantization | AWQ | `AI-Inference-and-Optimization/awq/` |
| GGUF format (llama.cpp) | GGUF | `AI-Inference-and-Optimization/gguf/` |

### Safety and Alignment

| Task | Skill | Location |
|---|---|---|
| Constitutional AI training | Constitutional AI | `AI-Training/constitutional-ai/` |
| Content safety classification | LlamaGuard | `Security-and-Compliance/llamaguard/` |
| Prompt injection detection | Prompt Guard | `Security-and-Compliance/prompt-guard/` |

### Infrastructure

| Task | Skill | Location |
|---|---|---|
| Serverless GPU compute | Modal | `Cloud-and-Hosting/modal/` |
| Multi-cloud orchestration | SkyPilot | `Cloud-and-Hosting/skypilot/` |
| GPU cloud instances | Lambda Labs | `Cloud-and-Hosting/lambda-labs/` |

### Agents and RAG

| Task | Skill | Location |
|---|---|---|
| Agent pipelines | LangChain | `LLM-and-Chatbot/langchain/` |
| Knowledge retrieval agents | LlamaIndex | `LLM-and-Chatbot/llamaindex/` |
| Vector store (local) | Chroma | `LLM-and-Chatbot/chroma/` |
| Vector similarity search | FAISS | `LLM-and-Chatbot/faiss/` |
| Text embeddings | Sentence Transformers | `LLM-and-Chatbot/sentence-transformers/` |
| Managed vector DB | Pinecone | `LLM-and-Chatbot/pinecone/` |

### Prompt Engineering and Structured Output

| Task | Skill | Location |
|---|---|---|
| Prompt optimization | DSPy | `LLM-and-Chatbot/dspy/` |
| Structured LLM output | Instructor | `LLM-and-Chatbot/instructor/` |
| Constrained generation | Guidance | `LLM-and-Chatbot/guidance/` |
| Grammar-based generation | Outlines | `LLM-and-Chatbot/outlines/` |

### Multimodal

| Task | Skill | Location |
|---|---|---|
| Vision-language models | CLIP | `Image-Recognition/clip/` |
| Speech recognition | ASR Router (Whisper fallback) | `Speech-Recognition/asr-router/` |
| Visual instruction tuning | LLaVA | `Image-Recognition/llava/` |

### Observability

| Task | Skill | Location |
|---|---|---|
| LLM tracing and debugging | LangSmith | `AI-MLOps/langsmith/` |
| LLM observability platform | Phoenix | `AI-MLOps/phoenix/` |

### Emerging Techniques

| Task | Skill | Location |
|---|---|---|
| Mixture of Experts training | MoE Training | `AI-Training/moe-training/` |
| Combining trained models | Model Merging | `AI-Training/model-merging/` |
| Extended context windows | Long Context | `AI-Models-and-Architecture/long-context/` |
| Faster inference via drafting | Speculative Decoding | `AI-Inference-and-Optimization/speculative-decoding/` |
| Teacher-student compression | Knowledge Distillation | `AI-Training/knowledge-distillation/` |
| Reducing model size | Model Pruning | `AI-Inference-and-Optimization/model-pruning/` |

### Research Output

| Task | Skill | Location |
|---|---|---|
| Generate research ideas | Research Ideation | `AI-Research/brainstorming-research-ideas/` |
| Write publication-ready paper | ML Paper Writing | `AI-Research/ml-paper-writing/` |

## Common Research Workflows

### "I need to fine-tune a model and evaluate it"

1. Pick fine-tuning skill based on needs (Unsloth for speed, Axolotl for flexibility)
2. Use lm-evaluation-harness for standard benchmarks
3. Track with W&B or MLflow

### "I need to understand what the model learned"

1. Use TransformerLens for circuit-level analysis
2. Train SAEs with SAELens for feature-level understanding
3. Run interventions with NNsight or Pyvene

### "I need to do RL training"

1. Start with TRL for standard PPO/DPO
2. Use GRPO skill for DeepSeek-R1 style training
3. Scale with OpenRLHF if needed

### "I need to run experiments on cloud GPUs"

1. Modal for quick serverless runs
2. SkyPilot for multi-cloud optimization
3. Lambda Labs for dedicated instances

## Finding Skills

If you're not sure which skill to use:

```bash
# Scan the candidate categories after reading the root SKILL.md
python skill_reader.py --category AI-Training --category AI-Evaluation-and-Benchmarking

# Scan RAG and application-framework skills
python skill_reader.py --category LLM-and-Chatbot
```
