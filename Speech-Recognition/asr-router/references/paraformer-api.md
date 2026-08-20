# Alibaba Paraformer v2

**Type:** **API** through DashScope. **Required secret:** `DASHSCOPE_API_KEY` or
`PARAFORMER_API_KEY`. The input must be a media URL reachable by DashScope.

```bash
python <asr-router>/scripts/paraformer_asr.py <media-url> \
  --model paraformer-v2 \
  --output <output>/paraformer-result.json
```

Options include `--poll-interval`, `--timeout`, `--env-file`, and `--doctor`.
The adapter submits an asynchronous task, polls the task endpoint with `GET`,
downloads the result, and
writes a router-schema envelope containing the task ID and raw result.

Treat `begin_time`, `start_time`, and `end_time` as milliseconds. Map sentences
to `segments`; map actual word units to `words` when returned. Do not infer word
timing from sentence boundaries.

Source ASR implementation migrated from
`Speech-Recognition/ra-逐字稿提取skill/scripts/transcript.py`.
