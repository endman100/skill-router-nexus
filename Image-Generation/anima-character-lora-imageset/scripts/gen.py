#!/usr/bin/env python3
"""Anima 角色 LoRA 圖冊生成。只用標準函式庫，在能連到 ComfyUI 的機器上跑。
例：
  python3 gen.py character.json --test                      # 試圖 4 組（單人、無性愛）
  python3 gen.py character.json --per 4 --url http://127.0.0.1:8188 --url http://127.0.0.1:8189
  python3 gen.py character.json --only 1,3 --per 2 --dry-run
"""
import argparse, copy, csv, json, os, random, re, sys, time, urllib.parse, urllib.request
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
L = lambda n: json.load(open(os.path.join(HERE, n)))

def build_prompt(c, tpl, action, outfit):
    head = c["character"].rstrip(", ") + ", " + outfit.rstrip(", ") + ", "
    rest = tpl["people"] + action + ", " + tpl["scene"] + ", " + tpl["tail"]
    return head + rest

def get(url, path, timeout=30): return json.load(urllib.request.urlopen(url + path, timeout=timeout))

def idle(url):
    try: q = get(url, "/queue", 10)
    except Exception: return False
    return not q.get("queue_running") and not q.get("queue_pending")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character"); ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--per", type=int, default=4, help="每個動作幾張")
    ap.add_argument("--only", default="", help="逗號分隔的動作編號（從 1 開始）")
    ap.add_argument("--test", action="store_true", help="只生 4 組單人試圖，確認 LoRA 生效")
    ap.add_argument("--out", default=""); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="endpoint 不空也照送")
    a = ap.parse_args()
    c, tpl, acts, base = json.load(open(a.character)), L("template.json"), L("actions.json"), L("workflow_api.json")
    if a.test: plan = [("test", tpl["test_action"].replace("solo", "1girl, solo"))] * 4; per = 1
    else:
        plan = [(f"act{i+1:02d}", t) for i, t in enumerate(acts)]
        if a.only: plan = [plan[int(n) - 1] for n in a.only.split(",") if n]
        per = a.per
    urls = a.url or ["http://127.0.0.1:8188"]
    if not (a.dry_run or a.force):
        urls = [u for u in urls if idle(u)]
        if not urls: sys.exit("沒有空的 ComfyUI endpoint（用 --force 強制）")
    out = a.out or os.path.join(os.getcwd(), c["name"] + ("_test" if a.test else ""))
    os.makedirs(os.path.join(out, "review"), exist_ok=True)
    jobs, k = [], 0
    for cat, act in plan:
        for _ in range(per):
          seed = random.randrange(10**8, 10**9)
          for var, outfit in (("clothed", c["outfit"]), ("nude", tpl["nude_outfit"])):
            p = build_prompt(c, tpl, act, outfit)
            if a.test: p = p.replace(tpl["people"], "")
            wf = copy.deepcopy(base)
            wf["5"]["inputs"]["text"] = p
            wf["4"]["inputs"].update(lora_name=c["lora"], strength_model=c["strength"], strength_clip=c["strength"])
            wf["8"]["inputs"]["seed"] = seed
            wf["10"]["inputs"]["filename_prefix"] = f"{c['name']}/{cat}_{seed}_{var}"
            jobs.append(dict(cat=cat, var=var, seed=seed, prompt=p, wf=wf, url=urls[k % len(urls)])); k += 1
    json.dump(jobs[0]["wf"], open(os.path.join(out, "workflow_api.json"), "w"), indent=1, ensure_ascii=False)
    if a.dry_run:
        for j in jobs: print(j["cat"], j["var"], j["seed"], j["url"], "\n ", j["prompt"])
        return print(len(jobs), "jobs (dry run)")
    for j in jobs:
        r = urllib.request.Request(j["url"] + "/prompt", data=json.dumps({"prompt": j["wf"]}).encode(), headers={"Content-Type": "application/json"})
        j["pid"] = json.load(urllib.request.urlopen(r, timeout=60))["prompt_id"]
    print(f"queued {len(jobs)} jobs on {urls}", flush=True)
    pending, t0 = list(jobs), time.time()
    while pending:
        time.sleep(5)
        for j in list(pending):
            try: h = get(j["url"], "/history/" + j["pid"])
            except Exception: continue
            e = h.get(j["pid"]); st = (e or {}).get("status", {})
            if not e: continue
            if st.get("status_str") == "error": j["err"] = str(st.get("messages"))[-500:]; pending.remove(j); continue
            if st.get("completed"):
                j["files"] = [i for o in e["outputs"].values() for i in o.get("images", [])]; pending.remove(j)
        print(f"  {len(jobs)-len(pending)}/{len(jobs)} done, {time.time()-t0:.0f}s", flush=True)
    count, rows = {}, []
    for j in jobs:
        for i in j.get("files", []):
            key = (j["cat"], j["var"]); count[key] = count.get(key, 0) + 1
            fn = f"{j['cat']}_{count[key]:02d}_{j['var']}.png"
            q = urllib.parse.urlencode(dict(filename=i["filename"], subfolder=i["subfolder"], type=i["type"]))
            open(os.path.join(out, "review", fn), "wb").write(urllib.request.urlopen(j["url"] + "/view?" + q, timeout=120).read())
            rows.append([fn, i["filename"], j["cat"], j["var"], j["seed"], j["url"], c["lora"], c["strength"], c.get("source", ""), j["prompt"]])
    with open(os.path.join(out, "manifest.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["file", "source_file", "category", "outfit_variant", "seed", "endpoint", "lora", "strength", "lora_source", "positive_prompt"]); w.writerows(rows)
    errs = [j for j in jobs if "err" in j]
    print(f"DONE {len(rows)} images -> {out}/review, errors {len(errs)}")
    for j in errs: print("ERR", j["cat"], j["seed"], j["err"])

if __name__ == "__main__": main()
