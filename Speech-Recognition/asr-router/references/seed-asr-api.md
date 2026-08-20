# Volcengine Seed ASR

**Type:** **API**. **Required secret:** `VOLCENGINE_API_KEY` from the environment
or a workspace `.env`. Upload only when `privacy=allow_api`.

The canonical adapter supports the repository's existing paths:

- `seed`: asynchronous submit/query, default resource `volc.seedasr.auc`.
- `standard`: asynchronous submit/query, default resource `volc.bigasr.auc`.
- `flash`: one-request recognition, default resource `volc.bigasr.auc_turbo`.

```bash
python <asr-router>/scripts/seed_asr.py <audio-or-video> \
  --mode seed \
  --output <output>/seed-asr-raw.json \
  --normalized-output <output>/asr-result.json
```

Use `--mode standard` or `--mode flash` only when that resource is enabled.
Options include `--resource-id`, `--language`, `--num-speakers`,
`--poll-interval`, `--timeout`, `--env-file`, and `--doctor`.

Filter empty tokens and negative or reversed timestamps. For production
subtitles, use approved script text for display and these word timestamps for
timing. Fail on missing key, upload-size limit, provider status, silence,
timeout, or missing usable words. Never print the key.

Repository benchmark note: a 180-second sample evaluated on 2026-06-25 found
Seed ASR word-boundary offset versus corrected subtitle windows at roughly
80 ms median, 240 ms P90, and 620 ms maximum. Treat this as one local sample,
not a universal accuracy guarantee; long utterances still require word-based
caption regrouping and QC.

Sources consolidated from `ra-audio-to-subtitles`, `video-use`, `AI剪口播`,
and `剪口播` Volcengine implementations.
