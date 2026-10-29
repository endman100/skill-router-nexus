#!/usr/bin/env python3
"""Grok Build single-turn client via official cli-chat-proxy (skill script).

Uses the same auth path as `grok login` / `grok -p`: session token in
~/.grok/auth.json + required CLI proxy headers. Not a wire forge of anti-abuse;
documented proxy access from Grok README ("Using auth.json for API Access").

OIDC refresh mirrors Grok CLI 1.0.67 AuthManager:
- discover token_endpoint from {issuer}/.well-known/openid-configuration
- POST grant_type=refresh_token + client_id + refresh_token (public client, auth method none)
- rewrite ~/.grok/auth.json key/refresh_token/expires_at (mode 0600)
- proactive refresh ~GROK_AUTH_EARLY_INVALIDATION_SECS before expires_at (default 300)
- on proxy HTTP 401, refresh once and retry
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

GROK_HOME = Path(os.environ.get("GROK_HOME", Path.home() / ".grok"))
DEFAULT_BASE = os.environ.get(
    "GROK_CLI_CHAT_PROXY_BASE_URL", "https://cli-chat-proxy.grok.com/v1"
).rstrip("/")
DEFAULT_CLI_VERSION = os.environ.get("GROK_CLI_VERSION", "1.0.67")
DEFAULT_MODEL = os.environ.get("GROK_MODEL", "grok-4.7")
EARLY_SECS = int(os.environ.get("GROK_AUTH_EARLY_INVALIDATION_SECS", "300"))

# Models listed by `grok models` on grok.com session (2026-10-28).
KNOWN_MODELS = (
    "grok-4.7",
    "grok-4.7-build-fast",
    "grok-4.6",
    "grok-4.5",
)


def _parse_expires_at(raw: Any) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _auth_path(auth_path: Path | None = None) -> Path:
    return auth_path or (GROK_HOME / "auth.json")


def _load_auth_file(path: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(
            f"missing {path}; run `grok login` or set GROK_AUTH / XAI_API_KEY"
        )
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not data:
        raise SystemExit(f"empty auth in {path}")
    entries: list[tuple[str, dict[str, Any]]] = []
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(v.get("key"), str):
            entries.append((k, v))
    if not entries:
        raise SystemExit(f"no .key field in {path}")
    entries.sort(key=lambda kv: str(kv[1].get("expires_at") or ""), reverse=True)
    scope, entry = entries[0]
    return data, scope, entry


def _write_auth_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _discover_token_endpoint(issuer: str) -> str:
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    with urllib.request.urlopen(url, timeout=30) as resp:
        disc = json.loads(resp.read().decode("utf-8"))
    te = disc.get("token_endpoint")
    if not te:
        raise SystemExit(f"OIDC discovery missing token_endpoint: {url}")
    return str(te)


def oidc_refresh_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Silent OIDC refresh like grok CLI AuthManager (public client)."""
    rt = entry.get("refresh_token")
    client_id = entry.get("oidc_client_id")
    issuer = entry.get("oidc_issuer") or "https://auth.x.ai"
    if not isinstance(rt, str) or not rt:
        raise SystemExit("auth entry has no refresh_token; re-run `grok login`")
    if not isinstance(client_id, str) or not client_id:
        raise SystemExit("auth entry has no oidc_client_id; re-run `grok login`")
    token_url = _discover_token_endpoint(str(issuer))
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": client_id,
        }
    ).encode()
    req = urllib.request.Request(
        token_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": f"grok/{DEFAULT_CLI_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OIDC refresh HTTP {e.code} from {token_url}: {err}") from e
    if status >= 400:
        raise SystemExit(f"OIDC refresh HTTP {status} from {token_url}: {raw}")
    tok = json.loads(raw)
    access = tok.get("access_token")
    if not isinstance(access, str) or not access:
        raise SystemExit(f"OIDC refresh missing access_token keys={list(tok.keys())}")
    new_rt = tok.get("refresh_token") if isinstance(tok.get("refresh_token"), str) else rt
    expires_in = int(tok.get("expires_in") or 21600)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat().replace("+00:00", "Z")
    out = dict(entry)
    out["key"] = access
    out["refresh_token"] = new_rt
    out["expires_at"] = expires_at
    return out


def ensure_fresh_auth(
    auth_path: Path | None = None,
    *,
    force: bool = False,
) -> str:
    """Return a usable Bearer token; refresh+persist when near/past expiry or force."""
    env = os.environ.get("GROK_AUTH") or os.environ.get("XAI_API_KEY")
    if env and not force:
        return env.strip()
    path = _auth_path(auth_path)
    data, scope, entry = _load_auth_file(path)
    exp = _parse_expires_at(entry.get("expires_at"))
    now = datetime.now(timezone.utc)
    need = force
    if exp is None:
        # no expiry: use as-is (CLI falls back to 30d for some providers)
        need = force
    else:
        need = force or exp <= now + timedelta(seconds=max(0, EARLY_SECS))
    if need:
        if not entry.get("refresh_token"):
            raise SystemExit(
                f"token expired/near-expiry ({entry.get('expires_at')}) but no "
                f"refresh_token in {path}; run `grok login`"
            )
        entry = oidc_refresh_entry(entry)
        data = dict(data)
        data[scope] = entry
        _write_auth_file(path, data)
    return str(entry["key"])


def load_auth_token(auth_path: Path | None = None) -> str:
    """Derive Bearer token from ~/.grok/auth.json or env (with OIDC auto-refresh)."""
    return ensure_fresh_auth(auth_path, force=False)


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
    timeout = float(os.environ.get("GROK_HTTP_TIMEOUT", "180"))

    def _do(tok: str) -> dict[str, Any]:
        hdrs = dict(headers)
        hdrs["Authorization"] = f"Bearer {tok}"
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), headers=hdrs, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if stream:
                return collect_stream(iter_sse_json(resp))
            raw = json.loads(resp.read().decode("utf-8"))
            text = ""
            for ch in raw.get("choices") or []:
                text += (ch.get("message") or {}).get("content") or ""
            return {
                "model": raw.get("model"),
                "text": text,
                "reasoning": "",
                "last_chunk": raw,
            }

    try:
        result = _do(token)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        if e.code == 401 and not (os.environ.get("GROK_AUTH") or os.environ.get("XAI_API_KEY")):
            # Match CLI: on 401, silent OIDC refresh once then retry.
            token = ensure_fresh_auth(force=True)
            headers["Authorization"] = f"Bearer {token}"
            try:
                result = _do(token)
            except urllib.error.HTTPError as e2:
                err2 = e2.read().decode("utf-8", errors="replace")
                raise SystemExit(f"HTTP {e2.code} from {url} after refresh: {err2}") from e2
        else:
            raise SystemExit(f"HTTP {e.code} from {url}: {err_body}") from e

    out_dir = Path(os.environ.get("GROK_CLONE_OUT", "/workspace/grok-build-clone"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "last_request.json").write_text(
        json.dumps(
            {
                "url": url,
                "headers_redacted": {
                    k: ("***" if k.lower() == "authorization" else v)
                    for k, v in headers.items()
                },
                "body": body,
            },
            indent=2,
        )
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
    p.add_argument("--force-refresh", action="store_true", help="OIDC refresh before call")
    args = p.parse_args(argv)
    if not args.prompt:
        raise SystemExit("pass a prompt argv or GROK_CLONE_PROMPT")
    if args.force_refresh:
        ensure_fresh_auth(force=True)
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
