#!/usr/bin/env python3
"""Read-only Codex/ChatGPT usage probe.
GET https://chatgpt.com/backend-api/wham/usage
Auth from ~/.codex/auth.json (never printed).
Usage:
  python3 codex_usage_probe.py           # human summary (Asia/Taipei)
  python3 codex_usage_probe.py --json    # full JSON
  python3 codex_usage_probe.py wham/usage  # optional path override (default wham/usage)
"""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

TPE = timezone(timedelta(hours=8))
CODEX_HOME = os.path.expanduser(os.environ.get("CODEX_HOME", "~/.codex"))

def load_auth():
    with open(os.path.join(CODEX_HOME, "auth.json")) as f:
        return json.load(f)["tokens"]

def fetch(path="wham/usage"):
    t = load_auth()
    req = urllib.request.Request(
        "https://chatgpt.com/backend-api/" + path.lstrip("/"),
        headers={
            "Authorization": "Bearer " + t["access_token"],
            "chatgpt-account-id": t.get("account_id", ""),
            "originator": "codex_cli_rs",
            "User-Agent": "codex_cli_rs/0.163.0 (Linux; x86_64) quota-probe",
            "Accept": "application/json",
        },
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        code, body, hdrs = r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        code, body, hdrs = e.code, e.read(), dict(e.headers)
    for k in list(hdrs):
        if k.lower() == "set-cookie":
            hdrs[k] = "<redacted>"
    out = {"status": code, "headers": hdrs}
    try:
        out["body"] = json.loads(body)
    except Exception:
        out["body_text"] = body[:2000].decode("utf-8", "replace")
    return out

def tpe_ts(epoch):
    if epoch is None:
        return None
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).astimezone(TPE).strftime(
        "%Y-%m-%d %H:%M (Asia/Taipei)"
    )

def summarize(out):
    if out.get("status") != 200 or "body" not in out:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 1
    b = out["body"]
    rl = b.get("rate_limit") or {}
    pw = rl.get("primary_window") or {}
    cr = b.get("credits") or {}
    print(f"Codex plan={b.get('plan_type')} used={pw.get('used_percent')}% "
          f"window_s={pw.get('limit_window_seconds')} reset={tpe_ts(pw.get('reset_at'))}")
    print(f"credits balance={cr.get('balance')} has_credits={cr.get('has_credits')} "
          f"approx_local={cr.get('approx_local_messages')} approx_cloud={cr.get('approx_cloud_messages')}")
    if rl.get("secondary_window"):
        sw = rl["secondary_window"]
        print(f"secondary used={sw.get('used_percent')}% reset={tpe_ts(sw.get('reset_at'))}")
    return 0

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--json"]
    want_json = "--json" in sys.argv
    path = args[0] if args else "wham/usage"
    out = fetch(path)
    if want_json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(0 if out.get("status") == 200 else 1)
    sys.exit(summarize(out))
