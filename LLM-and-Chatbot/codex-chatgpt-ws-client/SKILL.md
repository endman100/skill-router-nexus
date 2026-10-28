---
name: codex-chatgpt-ws-client
description: >-
  Call ChatGPT Codex quota via the official Codex CLI WebSocket
  (wss://chatgpt.com/backend-api/codex/responses) without launching `codex exec`.
  Use when you need a single-turn Codex/ChatGPT Responses call from a bot, with
  local ~/.codex auth. Not for chatgpt.com web UI / Sentinel bypass.
---

# Codex ChatGPT WS client

One script: `{baseDir}/codex_chatgpt_ws_client.py`  
Target (Codex 0.163.0 wire): `wss://chatgpt.com/backend-api/codex/responses`

## When to use

- Need the **Codex / ChatGPT account** path (same quota family as `codex exec`)
- Prefer a **thin WS client** over spawning the full CLI
- Do **not** use this for chatgpt.com web `/f/conversation` (different API + Sentinel)

## Models (verified 2026-10-28 on this box)

Reads `model` from `~/.codex/config.toml`; slug must exist in `models_cache.json`.

| Model slug | Status with this script |
|---|---|
| `gpt-6.1-sol` | works (default) |
| `gpt-6-astra` | works |
| `gpt-6.1-terra` | works |
| `gpt-6-sol` | works |
| `gpt-6-luna` | works |
| `gpt-reserve` | works (borrows collab/role strings) |
| `gpt-5.6-sol` | works (borrows collab/role strings) |
| `gpt-5.6-terra` | works (borrows collab/role strings) |
| `gpt-5.6-luna` | works (borrows collab/role strings) |
| `codex-auto-review` | works (borrows collab/role strings; cache `visibility: hide`) |

**Null-cache models:** some entries have `model_messages.collaboration_modes` / `multi_agent` = `null`. The script still uses that slug for the request `model` field, but borrows `collaboration_modes.default` + `multi_agent.role.root` text from a donor (prefer `gpt-6.1-sol`). Own `instructions_template` is always used.

## Place these files on the machine (do not paste secrets into chat)

| Path | Required | What |
|---|---|---|
| `~/.codex/auth.json` | yes | `tokens.access_token`, `tokens.account_id` (from `codex login`) |
| `~/.codex/installation_id` | yes | install UUID |
| `~/.codex/config.toml` | yes | at least `model`, `model_reasoning_effort` |
| `~/.codex/models_cache.json` | yes | `instructions_template` / collab / multi_agent for that model |
| `~/.codex/skills/.system/**/SKILL.md` | optional | feeds `<skills_instructions>` |

Override home with env `CODEX_HOME` if needed.

## Run

```bash
# venv needs: websockets, uuid6
python3 {baseDir}/codex_chatgpt_ws_client.py "your prompt here"
# or
CODEX_CLONE_PROMPT="your prompt" python3 {baseDir}/codex_chatgpt_ws_client.py
```

Outputs under `/workspace/codex-clone/` (or cwd if you change script): `last_request.json`, `last_result.json`.

Optional env:

| Env | Meaning |
|---|---|
| `CODEX_HOME` | Codex state dir (default `~/.codex`) |
| `CODEX_CLONE_PROMPT` | prompt if no argv |
| `CODEX_CLONE_TOOLS_JSON` | path to override embedded `additional_tools` JSON (after CLI upgrade) |

## Parameters — what they are, how to derive

### Handshake headers

| Param | Purpose | How to derive |
|---|---|---|
| `Authorization: Bearer …` | account auth | `auth.json` → `tokens.access_token` |
| `ChatGPT-Account-Id` | which account/workspace | `auth.json` → `tokens.account_id` |
| `OpenAI-Beta` | WS Responses protocol pin | constant `responses_websockets=2026-02-06` (from CLI 0.163.0 wire) |
| `Originator` | client class | `codex_exec` when mimicking `codex exec` |
| `Version` | CLI version | `0.163.0` (match installed Codex) |
| `User-Agent` | UA string | `{originator}/{ver} ({os} {rel}; {arch}) dumb ({originator}; {ver})` |
| `Session-Id` | thread / cache identity | new `uuid7()` per session |
| `x-client-request-id` | request correlation | same as `Session-Id` on connect |
| `x-codex-window-id` | window slot | `f"{session_id}:0"` |
| `x-codex-routing-hint` | edge routing | `model={config.toml model}` |
| `x-codex-beta-features` | beta flags | wire default `remote_compaction_v2` |
| `x-codex-turn-metadata` | JSON ops context | build object below → `json.dumps` |

### `x-codex-turn-metadata` / `client_metadata` fields

| Field | Purpose | How to derive |
|---|---|---|
| `installation_id` | install fingerprint | file `installation_id` |
| `session_id` / `thread_id` | conversation id | = `Session-Id` |
| `turn_id` | one user turn | `""` on prewarm; else new `uuid7()` |
| `context_window_id` | context window | separate `uuid7()` |
| `request_kind` | `prewarm` \| `turn` | frame 1 / frame 2 |
| `model` | model slug | `config.toml` `model` |
| `reasoning_effort` | thinking effort | `config.toml` `model_reasoning_effort` |
| `sandbox` / `sandbox_mode` | sandbox policy | e.g. `seccomp` / `read-only` |
| `history_initialization` | new vs continue | `new` for fresh session |
| `ws_request_header_x_openai_internal_codex_responses_lite` | Responses Lite | `"true"` |

### Body frames

1. **Prewarm** `response.create` with `generate: false`  
   - `input`: `additional_tools` (full nested schemas w/ `description`) + developer base instructions from `models_cache.json`  
   - `prompt_cache_key` = `session_id`  
   - `store: false`, `stream: true`, `tool_choice: auto`, `include: ["reasoning.encrypted_content"]`
2. **Turn** `response.create` with `previous_response_id` from prewarm  
   - `input`: host skills/permissions/collab/plugins, multi_agent role/mode, environment_context, user text  
   - item ids `msg_*` / `at_*`: `uuid5(OID(session_id), content_bytes)`  
   - `access_programs: {"cyber":"standard"}`

### What you replace when upgrading Codex CLI

| Thing | Replace when |
|---|---|
| `Version` / `User-Agent` / `OpenAI-Beta` | CLI major/protocol bump |
| Embedded `_EMBEDDED_TOOLS_JSON` in the `.py` | tool schemas change (mitm-capture prewarm `additional_tools`) |
| `x-codex-beta-features` | wire shows new flags |
| Model slug / effort | your `config.toml` / `models_cache.json` |

Re-capture tools: run `codex exec` once through mitm, take the first client `response.create` → `input[]` entry `type=additional_tools` → `tools`, dump JSON, set `CODEX_CLONE_TOOLS_JSON` or paste into `_EMBEDDED_TOOLS_JSON`.

## Agent checklist

1. Confirm `~/.codex/auth.json` exists (never print tokens).
2. `pip install websockets uuid6` in a venv if needed.
3. Run the script with the user prompt.
4. Return `assistant_text` + response ids from stdout / `last_result.json`.
5. On 400 about `tools[0].description`, refresh embedded tools (see above).

## Out of scope

- chatgpt.com web UI, Sentinel/Turnstile, `/f/conversation`
- Multi-turn tool loops beyond one generate (extend script if needed)
