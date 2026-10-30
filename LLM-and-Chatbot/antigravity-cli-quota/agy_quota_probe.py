#!/usr/bin/env python3
"""Read-only Antigravity quota probe. Uses local agy OAuth token; NEVER calls generation.
Endpoints (Cloud Code PA v1internal, JSON over HTTPS POST, Bearer auth):
  loadCodeAssist            -> project id / tier
  retrieveUserQuotaSummary  -> groups[].buckets[] remainingFraction/resetTime/window
  fetchAvailableModels      -> models{}.quotaInfo per model
  retrieveUserQuota         -> buckets[] (gemini-cli style)
If token expired: run `agy models` once (no generation) to let the CLI refresh it.
Usage: python3 agy_quota_probe.py [--raw] [--host daily-cloudcode-pa.googleapis.com]
"""
import json, sys, datetime, urllib.request, urllib.error, os
TOK = os.path.expanduser("~/.gemini/antigravity-cli/antigravity-oauth-token")
host = "daily-cloudcode-pa.googleapis.com"
if "--host" in sys.argv: host = sys.argv[sys.argv.index("--host")+1]
raw = "--raw" in sys.argv
d = json.load(open(TOK)); t = d["token"]
exp = datetime.datetime.fromisoformat(t["expiry"][:26] + t["expiry"][-6:])
if exp < datetime.datetime.now(exp.tzinfo):
    sys.exit(f"token expired at {t['expiry']}; run `agy models` to refresh (no generation)")
H = {"Authorization": f"Bearer {t['access_token']}", "Content-Type": "application/json",
     "User-Agent": "antigravity/1.4.10 linux/amd64"}
def call(m, body):
    req = urllib.request.Request(f"https://{host}/v1internal:{m}", json.dumps(body).encode(), H, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        b = e.read()
        try: return e.code, json.loads(b)
        except Exception: return e.code, b.decode(errors="replace")[:500]
out = {}
s, lca = call("loadCodeAssist", {"metadata": {"ideType": "ANTIGRAVITY", "platform": "PLATFORM_UNSPECIFIED", "pluginType": "GEMINI"}})
out["loadCodeAssist"] = {"status": s, "body": lca}
proj = lca.get("cloudaicompanionProject") if isinstance(lca, dict) else None
if isinstance(proj, dict): proj = proj.get("id")
body = {"project": proj} if proj else {}
for m in ("retrieveUserQuotaSummary", "fetchAvailableModels", "retrieveUserQuota"):
    s, b = call(m, body); out[m] = {"status": s, "body": b}
if raw: print(json.dumps(out, indent=1, ensure_ascii=False)); sys.exit()
print("account:", d.get("id_token_email"), "| project:", proj, "| tier:", (lca.get("currentTier") or {}).get("id") if isinstance(lca, dict) else None)
q = out["retrieveUserQuotaSummary"]
print("\n[retrieveUserQuotaSummary] HTTP", q["status"])
if isinstance(q["body"], dict):
    for g in q["body"].get("groups", []) or [{"displayName": "(top)", "buckets": q["body"].get("buckets", [])}]:
        print(" group:", g.get("displayName"))
        for bk in g.get("buckets", []):
            print(f"   {bk.get('displayName') or bk.get('bucketId')}: remainingFraction={bk.get('remainingFraction', 0)} remainingAmount={bk.get('remainingAmount')} window={bk.get('window')} reset={bk.get('resetTime')} disabled={bk.get('disabled')}")
fm = out["fetchAvailableModels"]
print("\n[fetchAvailableModels] HTTP", fm["status"])
if isinstance(fm["body"], dict):
    for k, v in (fm["body"].get("models") or {}).items():
        qi = v.get("quotaInfo") or {}
        print(f"   {k:40s} {v.get('displayName','')[:30]:30s} remainingFraction={qi.get('remainingFraction', 0 if qi.get('resetTime') else None)} reset={qi.get('resetTime')}")
ru = out["retrieveUserQuota"]
print("\n[retrieveUserQuota] HTTP", ru["status"])
if isinstance(ru["body"], dict):
    for bk in ru["body"].get("buckets", []):
        print(f"   {bk.get('modelId'):32s} {bk.get('tokenType')} remainingFraction={bk.get('remainingFraction', 0)} reset={bk.get('resetTime')}")
print("\n(note: proto3 JSON omits zero, so a missing remainingFraction == 0)")
