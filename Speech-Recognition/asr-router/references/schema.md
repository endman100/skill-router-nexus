# ASR routing schema

This file is the canonical routing order and data contract. Follow the link in
the selected row; do not load every provider guide.

## Default order

| Rank | Method | Type | Model/resource | Repository evidence | Select when |
|---:|---|---|---|---|---|
| 1 | [Qwen3-ASR](qwen3-asr.md) | Local GPU | `Qwen3-ASR-1.7B-hf` + Qwen3 ForcedAligner | Multilingual text plus forced word alignment | CUDA is available and the profile permits Qwen |
| 2 | [Whisper CLI](whisper-local.md) | Local | installed Whisper model; CLI default `turbo` | Mature offline transcription and SRT export | Local execution is required or Qwen is unavailable |
| 3 | [Seed ASR](seed-asr-api.md) | **API** | Seed/standard/flash resource selected by profile | Word timestamps used by production caption and editing workflows | API upload is allowed; especially useful for Chinese timing |
| 4 | [Deepgram](deepgram-api.md) | **API** | model exposed by the discovered live tool | Provider automation through the installed Rube toolkit | Batch or realtime provider tooling is available |
| 5 | [Paraformer v2](paraformer-api.md) | **API** | `paraformer-v2` | DashScope asynchronous transcript extraction | A reachable media URL and DashScope key are available |
| 6 | [OpenAI Whisper API](openai-whisper-api.md) | **API** | `whisper-1` | Installed audio-transcription adapter | OpenAI-compatible audio transcription is configured |
| 7 | [Gladia](gladia-api.md) | **API** | model exposed by the discovered live tool | Provider automation through the installed Rube toolkit | Gladia connection and matching tools are available |
| 8 | [Rev AI](rev-ai-api.md) | **API** | model exposed by the discovered live tool | Provider automation through the installed Rube toolkit | Rev AI connection and matching tools are available |
| 9 | [Wit.ai](wit-ai-api.md) | **API** | model exposed by the discovered live tool | Provider automation through the installed Rube toolkit | Wit.ai connection and matching tools are available |

This is an operational priority, not a claim that one provider has the lowest
WER for every language and recording. Evaluate each candidate against the
requested profile using: recognition quality on representative audio, required
timestamp granularity, language coverage, latency/throughput, local privacy or
API upload, runtime/credential availability, and failure rate. The caller's
hard constraints override rank; otherwise preserve the table order.

With no CUDA, start at Whisper. With `local_only`, stop after Whisper. For
required word-level timing, skip a method unless its selected invocation returns
real word timings; Qwen3 plus its aligner and Seed ASR satisfy the repository's
current timing workflows. For realtime recognition, prefer an available
Deepgram or Gladia realtime tool rather than walking the batch order.

## Input contract

```json
{
  "source": "/absolute/path/or/reachable-url",
  "profile": "transcript|word_timestamps|realtime|qa",
  "language": null,
  "privacy": "local_only|allow_api",
  "gpu": "cuda|none|unknown",
  "preferred_provider": null,
  "fallback_allowed": true,
  "reference_text": null,
  "output_dir": "/absolute/output/path"
}
```

`reference_text` is approved display wording or alignment text. Do not send it
as a recognition prompt unless the selected method guide permits that behavior
and the caller authorizes it.

`preferred_provider` is the only supported provider lock. The calling skill
still invokes this Router; it must not resolve or execute a child adapter path.
When `fallback_allowed=false`, attempt only that provider and return its exact
unavailable or failure state.

## Output contract

```json
{
  "schema_version": "1.0",
  "provider": "qwen3|whisper|seed-asr|deepgram|paraformer|openai|gladia|rev-ai|wit-ai",
  "model": "exact model or resource identifier",
  "type": "local|api",
  "source": "/absolute/path/or-url",
  "source_sha256": null,
  "language": null,
  "text": "",
  "segments": [{"text": "", "start": 0.0, "end": 0.0}],
  "words": [{"text": "", "start": 0.0, "end": 0.0, "confidence": null}],
  "raw_artifact": "/absolute/path/to/provider-result",
  "command": "exact invocation without secrets",
  "warnings": [],
  "fallback_trace": [{"provider": "qwen3", "status": "unavailable|failed|succeeded", "reason": ""}]
}
```

Use empty arrays when the provider does not return a granularity. Never invent
timestamps, confidence, language, or a source hash. Keep secrets out of the
command and artifacts.

Provider extensions such as `speaker_id`, `requested_language`, or
`type=spacing` may be preserved. Consumers must ignore spacing entries when
they require real recognized words.

## Stop conditions

- Stop before the first API when `privacy=local_only`.
- Stop immediately when the caller sets `fallback_allowed=false`.
- Stop when a provider returns usable output satisfying the requested profile.
- Stop and report the exact error when every eligible method is unavailable or
  failed. Downloading captions or fetching an existing transcript is not an ASR
  fallback.
