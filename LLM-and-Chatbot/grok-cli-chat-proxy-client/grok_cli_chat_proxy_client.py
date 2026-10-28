#!/usr/bin/env python3
"""Grok Build single-turn client via official cli-chat-proxy (skill script).

Uses the same auth path as `grok login` / `grok -p`: session token in
~/.grok/auth.json + required CLI proxy headers. Not a wire forge of anti-abuse;
documented proxy access from Grok README ("Using auth.json for API Access").
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator

GROK_HOME = Path(os.environ.get("GROK_HOME", Path.home() / ".grok"))
DEFAULT_BASE = os.environ.get(
    "GROK_CLI_CHAT_PROXY_BASE_URL", "https://cli-chat-proxy.grok.com/v1"
).rstrip("/")
DEFAULT_CLI_VERSION = os.environ.get("GROK_CLI_VERSION", "1.0.67")
DEFAULT_MODEL = os.environ.get("GROK_MODEL", "grok-4.7")

# Models listed by `grok models` on grok.com session (2026-10-28).
KNOWN_MODELS = (
    "grok-4.7",
    "grok-4.7-build-fast",
    "grok-4.6",
    "grok-4.5",
)


def load_auth_token(auth_path: Path | None = None) -> str:
    """Derive Bearer token from ~/.grok/auth.json or env."""
    env = os.environ.get("GROK_AUTH") or os.environ.get("XAI_API_KEY")
    if env:
        return env.strip()
    path = auth_path or (GROK_HOME / "auth.json")
    if not path.is_file():
        raise SystemExit(
            f"missing {path}; run `grok login` or set GROK_AUTH / XAI_API_KEY"
        )
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not data:
        raise SystemExit(f"empty auth in {path}")
    # Prefer newest expires_at; keys look like https://auth.x.ai::<uuid>
    entries: list[tuple[str, dict[str, Any]]] = []
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(v.get("key"), str):
            entries.append((k, v))
    if not entries:
        raise SystemExit(f"no .key field in {path}")
    entries.sort(key=lambda kv: str(kv[1].get("expires_at") or ""), reverse=True)
    return entries[0][1]["key"]


def iter_sse_json(resp: Any) -> Iterator[dict[str, Any]]:
    for raw in resp:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


def collect_stream(chunks: Iterator[dict[str, Any]]) -> dict[str, Any]:
    text: list[str] = []
    reasoning: list[str] = []
    model = None
    last: dict[str, Any] = {}
    for obj in chunks:
        last = obj
        model = obj.get("model") or model
        for ch in obj.get("choices") or []:
            delta = ch.get("delta") or {}
            if delta.get("content"):
                text.append(delta["content"])
            if delta.get("reasoning_content"):
                reasoning.append(delta["reasoning_content"])
            msg = ch.get("message") or {}
            if msg.get("content"):
                text.append(msg["content"])
    return {
        "model": model,
        "text": "".join(text),
        "reasoning": "".join(reasoning),
        "last_chunk": last,
    }


def call(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE,
    cli_version: str = DEFAULT_CLI_VERSION,
    reasoning_effort: str | None = None,
    stream: bool = True,
    token: str | None = None,
) -> dict[str, Any]:
    token = token or load_auth_token()
    override = os.environ.get("GROK_MODEL_OVERRIDE", model)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if stream else "application/json",
        "User-Agent": f"grok/{cli_version}",
        # Required: middleware treats this as CLI session token (README).
        "X-XAI-Token-Auth": "xai-grok-cli",
        # Required: proxy routes by this header, not only JSON body (README).
        "x-grok-model-override": override,
        # Required: without it proxy returns 426 "version (none) is outdated".
        "x-grok-client-version": cli_version,
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort

    url = f"{base_url}/chat/completions"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=float(os.environ.get("GROK_HTTP_TIMEOUT", "180"))) as resp:
            if stream:
                result = collect_stream(iter_sse_json(resp))
            else:
                raw = json.loads(resp.read().decode("utf-8"))
                text = ""
                for ch in raw.get("choices") or []:
                    text += (ch.get("message") or {}).get("content") or ""
                result = {
                    "model": raw.get("model"),
                    "text": text,
                    "reasoning": "",
                    "last_chunk": raw,
                }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} from {url}: {err_body}") from e

    out_dir = Path(os.environ.get("GROK_CLONE_OUT", "/workspace/grok-build-clone"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "last_request.json").write_text(
        json.dumps({"url": url, "headers_redacted": {k: ("***" if k.lower() == "authorization" else v) for k, v in headers.items()}, "body": body}, indent=2)
        + "\n"
    )
    (out_dir / "last_result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Grok Build cli-chat-proxy single-turn client")
    p.add_argument("prompt", nargs="?", default=os.environ.get("GROK_CLONE_PROMPT"))
    p.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"model id (known: {', '.join(KNOWN_MODELS)})")
    p.add_argument("--effort", "--reasoning-effort", dest="effort", default=os.environ.get("GROK_REASONING_EFFORT"))
    p.add_argument("--base-url", default=DEFAULT_BASE)
    p.add_argument("--cli-version", default=DEFAULT_CLI_VERSION)
    p.add_argument("--no-stream", action="store_true", help="request non-streaming (often unsupported)")
    args = p.parse_args(argv)
    if not args.prompt:
        raise SystemExit("pass a prompt argv or GROK_CLONE_PROMPT")
    result = call(
        args.prompt,
        model=args.model,
        base_url=args.base_url,
        cli_version=args.cli_version,
        reasoning_effort=args.effort,
        stream=not args.no_stream,
    )
    sys.stdout.write(result["text"])
    if result["text"] and not result["text"].endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
