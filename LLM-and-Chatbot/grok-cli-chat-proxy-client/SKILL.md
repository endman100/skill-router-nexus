---
name: grok-cli-chat-proxy-client
description: >-
  Call Grok Build quota via the official cli-chat-proxy
  (https://cli-chat-proxy.grok.com/v1/chat/completions) using `grok login`
  session auth in ~/.grok/auth.json — same family as `grok -p`, without the TUI.
  Use for single-turn Grok Build prompts from a bot. Not for forging login or
  bypassing CLI version / token-auth headers.
  OIDC auto-refresh via refresh_token. Grok Bot host only (hostname grok-bot-vm*).
---

# Grok Build cli-chat-proxy client

One script: `{baseDir}/grok_cli_chat_proxy_client.py`  
Target: `POST https://cli-chat-proxy.grok.com/v1/chat/completions` (SSE stream)

Derived from Grok CLI **1.0.67** + official README section *Using auth.json for API Access*, verified live on 2026-10-28.

## Host lock（標註）

**只能在 Grok Bot 機器上運行**（本機 hostname 如 `grok-bot-vm*`）。不要在其他電腦、CI 或一般筆電上使用此 skill。


## When to use

- Need **Grok Build / grok.com session** path (same login as `grok -p`)
- Prefer a **thin HTTP client** over spawning the full TUI/`grok` binary
- Do **not** omit required CLI proxy headers (426 / auth failures)

## Place these files on the machine (do not paste secrets into chat)

| Path | Required | What |
|---|---|---|
| `~/.grok/auth.json` | yes\* | session entry with `.key` (from `grok login`) |
| `~/.grok/config.toml` | optional | marketplace/cli prefs; not required for this script |

\*Or set env `GROK_AUTH` / `XAI_API_KEY` (API key path differs; session token is preferred for Build models).

Override home with env `GROK_HOME` if needed.

## OIDC auto-refresh (matches Grok CLI)

Access tokens in `~/.grok/auth.json` expire in ~6h (`expires_in=21600`). The official CLI silent-refreshes via IdP; this script does the same:

1. Read entry (`key`, `refresh_token`, `oidc_client_id`, `oidc_issuer`, `expires_at`)
2. If `expires_at` is within `GROK_AUTH_EARLY_INVALIDATION_SECS` (default **300**), or proxy returns **401**, POST to `{issuer}/.well-known/openid-configuration` → `token_endpoint` (for SpaceXAI: `https://auth.x.ai/oauth2/token`) with `grant_type=refresh_token` + `client_id` + `refresh_token` (public client, no secret)
3. Rewrite `key` / `refresh_token` / `expires_at` in `auth.json` (mode `0600`)
4. Retry the chat-completions call once after a 401-driven refresh

Env: `GROK_AUTH_EARLY_INVALIDATION_SECS` (CLI default 300). CLI flag: `--force-refresh`.

## Run


```bash
python3 {baseDir}/grok_cli_chat_proxy_client.py "your prompt here"
# or
GROK_CLONE_PROMPT="your prompt" python3 {baseDir}/grok_cli_chat_proxy_client.py
# model + effort
python3 {baseDir}/grok_cli_chat_proxy_client.py -m grok-4.5 --effort low "Say hi"
```

Outputs under `/workspace/grok-build-clone/` (or `GROK_CLONE_OUT`): `last_request.json`, `last_result.json`.

Optional env:

| Env | Meaning |
|---|---|
| `GROK_HOME` | Grok state dir (default `~/.grok`) |
| `GROK_CLONE_PROMPT` | prompt if no argv |
| `GROK_MODEL` | default model id |
| `GROK_MODEL_OVERRIDE` | value for `x-grok-model-override` (defaults to model) |
| `GROK_REASONING_EFFORT` | default `--effort` |
| `GROK_CLI_VERSION` | `x-grok-client-version` / UA (default `1.0.67`) |
| `GROK_CLI_CHAT_PROXY_BASE_URL` | proxy base (default `https://cli-chat-proxy.grok.com/v1`) |
| `GROK_AUTH` / `XAI_API_KEY` | Bearer override instead of auth.json |
| `GROK_CLONE_OUT` | where to write last_request/result JSON |
| `GROK_HTTP_TIMEOUT` | seconds (default `180`) |

## Models (`grok models`, grok.com login) — verified 2026-10-28

All four return successfully via this script (HTTP 200 SSE):

| Model id | Notes |
|---|---|
| `grok-4.7` | default; proxy may report backend `grok-4.7-build` |
| `grok-4.7-build-fast` | fast variant |
| `grok-4.6` | |
| `grok-4.5` | |

Reasoning efforts seen in CLI: `xhigh`, `high` (default), `medium`, `low` (`grok-4.5` has no `xhigh` in catalog).

## Parameters — what they are, how to derive

### HTTP

| Param | Purpose | How to derive |
|---|---|---|
| URL | chat completions | `{base}/chat/completions` — base default `https://cli-chat-proxy.grok.com/v1` (`GROK_CLI_CHAT_PROXY_BASE_URL` / CLI flag) |
| Method | | `POST` |
| Body `stream` | SSE chunks | prefer `true` (README: most proxy models streaming-only) |

### Headers

| Header | Purpose | How to derive |
|---|---|---|
| `Authorization: Bearer …` | session / API auth | `auth.json` → pick entry with `.key` (prefer latest `expires_at`); or `GROK_AUTH` / `XAI_API_KEY` |
| `Content-Type` | JSON body | `application/json` |
| `X-XAI-Token-Auth` | mark CLI session token | constant `xai-grok-cli` (README) |
| `x-grok-model-override` | **routing** to backend | usually same as body `model`; README notes body alone is not enough |
| `x-grok-client-version` | CLI version gate | installed `grok --version` (e.g. `1.0.67`); missing → **HTTP 426** |
| `User-Agent` | client UA | `grok/{version}` matches CLI family |

Optional (CLI SamplerConfig also sends; not required for basic `-p` equivalent): `x-grok-client-mode`, `x-authenticateresponse`.

### JSON body

| Field | Purpose | How to derive |
|---|---|---|
| `model` | model id | `-m` / `GROK_MODEL`; list via `grok models` |
| `messages` | OpenAI-style chat | single user turn: `[{"role":"user","content": prompt}]` |
| `stream` | SSE vs JSON | default `true` |
| `reasoning_effort` | thinking level | `--effort` / `GROK_REASONING_EFFORT` when supported |

### Auth.json shape (OIDC session)

Top-level keys look like `https://auth.x.ai::<uuid>` (docs curl still shows an older `https://accounts.x.ai/sign-in` example — **read whatever key exists** and take `.key`). Useful fields: `key`, `refresh_token`, `expires_at`, `auth_mode` (`oidc`). Tokens expire (~7 days per README); refresh with `grok login`.

## Relation to `grok -p`

| | `grok -p` | this script |
|---|---|---|
| Auth | `~/.grok/auth.json` SessionToken | same |
| Endpoint family | cli-chat-proxy `/v1` + Responses internally | public `/v1/chat/completions` documented for auth.json |
| Tools / agent loop | full Build agent | **single-turn chat only** |
| Version gate | binary embeds version | must send `x-grok-client-version` |

For full agent/tools, keep using `grok -p` / `grok agent`. This skill is the thin prompt path.
