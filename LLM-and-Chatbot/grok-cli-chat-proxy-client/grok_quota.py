#!/usr/bin/env python3
"""Grok weekly quota readout (unified/Cursor-merged billing), read-only, zero generation.
Same call the grok TUI `/usage` -> "Usage limit" tab makes:
  GET https://cli-chat-proxy.grok.com/v1/billing?format=credits
  headers: Authorization Bearer from ~/.grok/auth.json, X-XAI-Token-Auth: xai-grok-cli,
           x-grok-client-version / User-Agent: grok/<ver>
Backend is flaky (503 cursor billing / meter unavailable); this script retries.
Plain /v1/billing (no format) returns legacy monthly zeros for unified users — ignore it.
Usage: python3 grok_quota.py [--json] [--tries N]
"""
import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from grok_cli_chat_proxy_client import load_auth_token  # noqa: E402

URL = "https://cli-chat-proxy.grok.com/v1/billing?format=credits"
VER = "1.0.67"
TPE = timezone(timedelta(hours=8))

def fetch(tries=12):
    tok = load_auth_token(); last = None
    for i in range(tries):
        req = urllib.request.Request(URL, headers={"Authorization": "Bearer " + tok, "Accept": "application/json",
              "User-Agent": f"grok/{VER}", "X-XAI-Token-Auth": "xai-grok-cli", "x-grok-client-version": VER})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return {"ok": True, "attempts": i + 1, "body": json.loads(r.read())}
        except urllib.error.HTTPError as e:
            last = {"status": e.code, "body": e.read()[:500].decode("utf-8", "replace")}
            if e.code not in (429, 500, 502, 503, 504): break
        time.sleep(min(1.5 * (i + 1), 6))
    return {"ok": False, "attempts": i + 1, "last_error": last}

def tpe(s):
    return datetime.fromisoformat(s).astimezone(TPE).strftime("%Y-%m-%d %H:%M (Asia/Taipei)")

if __name__ == "__main__":
    tries = int(sys.argv[sys.argv.index("--tries") + 1]) if "--tries" in sys.argv else 12
    res = fetch(tries)
    if "--json" in sys.argv or not res["ok"]:
        print(json.dumps(res, indent=2, ensure_ascii=False)); sys.exit(0 if res["ok"] else 1)
    c = res["body"]["config"]; p = c.get("currentPeriod", {})
    print(f"Grok {p.get('type','?').replace('USAGE_PERIOD_TYPE_','').lower()} limit used: {c.get('creditUsagePercent')}%  "
          f"(remaining ~{100 - float(c.get('creditUsagePercent') or 0):.0f}%)")
    print(f"Period: {tpe(p['start'])} -> resets {tpe(p['end'])}")
    for u in c.get("productUsage", []): print(f"  {u['product']:<10} {u['usagePercent']}%")
    print(f"unified={c.get('isUnifiedBillingUser')} prepaidBalance={c.get('prepaidBalance',{}).get('val')} "
          f"topUp={c.get('topUpMethod')} attempts={res['attempts']}")
