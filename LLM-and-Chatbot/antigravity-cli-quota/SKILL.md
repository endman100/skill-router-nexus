---
name: antigravity-cli-quota
description: >-
  Read Antigravity (`agy`) remaining quota via Cloud Code PA
  `v1internal:retrieveUserQuota*` / `fetchAvailableModels` using local
  `~/.gemini/antigravity-cli/antigravity-oauth-token`. Read-only; no generation.
  Use when a bot needs Antigravity usage / reset times. Not a chat thin client.
  Grok Bot host only (hostname grok-bot-vm*).
---

# Antigravity CLI quota probe

One script: `{baseDir}/agy_quota_probe.py`  
Target: `POST https://daily-cloudcode-pa.googleapis.com/v1internal:<method>`

## Host lock（標註）

**只能在 Grok Bot 機器上運行**（本機 hostname 如 `grok-bot-vm*`）。不要在其他電腦、CI 或一般筆電上使用此 skill。

## When to use

- Need **Antigravity / `agy` remaining quota** (per model or group) without opening the TUI
- Do **not** use this skill to generate chat; it only calls quota / model-list endpoints

## Place these files on the machine (do not paste secrets into chat)

| Path | Required | What |
|---|---|---|
| `~/.gemini/antigravity-cli/antigravity-oauth-token` | yes | OAuth JSON with `token.access_token`, `token.refresh_token`, `token.expiry` (from `agy` login) |

If the access token is expired, run `agy models` once (no generation) so the CLI refreshes and rewrites the file.

## Run

```bash
python3 {baseDir}/agy_quota_probe.py          # human summary
python3 {baseDir}/agy_quota_probe.py --raw    # full JSON for all endpoints
```

## Endpoints

All are HTTPS JSON `POST` with:

- `Authorization: Bearer <access_token>`
- `Content-Type: application/json`
- Body after `loadCodeAssist`: `{"project":"<cloudaicompanionProject>"}` (typically `aicode-consumers`)

| Method | Purpose |
|---|---|
| `loadCodeAssist` | project id + tier |
| `retrieveUserQuotaSummary` | groups / weekly buckets (`remainingFraction`, `resetTime`) |
| `retrieveUserQuota` | per-model buckets |
| `fetchAvailableModels` | models + `quotaInfo` (same fractions) |

**Note:** proto3 JSON omits zero values, so a missing `remainingFraction` means `0`.

## Out of scope

- Full Antigravity chat thin client / `streamGenerateContent` agent loops
- Printing or pasting OAuth tokens into chat
