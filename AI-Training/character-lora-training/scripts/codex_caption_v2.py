#!/usr/bin/env python3
"""打標 b：逐張打標，一張圖一次隔離 Codex 呼叫（codex_isolated.py），固定欄位用 JSON schema enum 鎖在詞表內。

分組（manifest 的 source_group + vocab 的 outfits）：
  A        固定模板，主要服裝：主要服裝的收集圖 + 維持服裝生成圖（Codex keep、Grok keep）
  B_fixed  固定模板，套該造型的清單：收集圖中其他造型
  B_free   自由模板：Codex 換裝圖；服裝／配件自由，但 character_clothing_tags 不准用主要服裝 tag
正式打標只讀 --images 資料夾內的圖片（manifest 只用來查 source_group），全部交給 Codex。
本程式不做 NSFW 判斷：正式打標只能指定 SFW 資料夾；NSFW 資料夾僅能搭配 --dry-run 在本機建立 schema，
此模式只列檔名、不開啟圖片、不呼叫 Codex，供 Grok 打標及 caption_convert 驗證使用。
每張圖的 schema：詞表欄位 = 該組選項的 enum（不得自創 tag）。params 的 fixed_traits（身高、體型、年齡）對應欄位
每張必填、不可留空；其他詞表欄位為可選，看不到可留空（陣列 []、字串 ""）；自由欄位必填；NSFW 欄位不輸出。
模板中的 {{required_vocab_lines}} / {{optional_vocab_lines}} 依 params 的 template_vars 順序產生。
Codex 寫 ./output/<stem>.json → jsonschema 驗證 → 失敗重試（--retries）。
JSON → txt：caption_convert.py（drop_empty → 刪 detailed_description → json_to_string →
merge_all_caption([only_prefix(['anime style', trigger]), …])，即原 repo 轉換）；txt 以 `anime style, <trigger>, ` 開頭。
模型不在 Codex models_cache.json 時直接停止（不換模型）。

用法：
  python3 codex_caption_v2.py --character "<角色名>" --work "<作品名>" --trigger <trigger> \
     --images <訓練資料夾> --manifest <訓練資料夾>/manifest.json \
     --vocab <vocab>/vocab.json --main-outfit <vocab>/main_outfit.json --out <輸出資料夾> \
     [--model gpt-6-luna --effort max --workers 16 --retries 2] [--only 0001.png ...] [--dry-run] [--final-dir <dir>]
"""
import argparse, hashlib, json, os, re, shutil, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from ws import parse_args
import jsonschema
sys.path.insert(0, str(Path(__file__).parent))
from codex_isolated import run_isolated
from vocab_tools import feature_options, fixed_fields
from caption_convert import convert

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
LOCK = threading.Lock()
DROP_FIELDS = {"NSFW"}                       # 不輸出（使用者 2026-10-22）
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
FREE_IN_FREE_TEMPLATE = {"character_clothing_tags", "character_accessories_tags"}
INSTRUCTIONS = ("Follow the user's prompt. Use the image viewer to look at images. "
                "Write files only in the workdir. No web access.")


# ---- JSON -> txt：caption_convert.py（原 repo 轉換 + drop_empty）----

def parse_json(path):
    text = path.read_text(encoding="utf-8-sig").strip()
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


# ---- prompts / schemas ----

def fill(template, values):
    missing = sorted({m for m in VAR_RE.findall(template) if m not in values})
    if missing:
        raise KeyError(f"template variables without value: {missing}")
    return VAR_RE.sub(lambda m: str(values[m.group(1)]), template)


def tag_list(items):
    return [t["tag"] for t in items]


def field_options(vocab, params, outfit, template_kind):
    """詞表欄位 -> [{tag}]。固定模板時，服裝 tag 分進 clothing / accessories。"""
    opts = feature_options(vocab["character_features"], params["field_traits"])
    if template_kind == "fixed":
        acc_set = set(params["outfit_accessory_tags"])
        opts["character_clothing_tags"] = [t for t in outfit["tags"] if t["tag"] not in acc_set]
        opts["character_accessories_tags"] = opts.get("character_accessories_tags", []) + \
            [t for t in outfit["tags"] if t["tag"] in acc_set]
    return opts


def vocab_fields(opts, template_kind):
    """Fields locked to the vocab enum for this template."""
    return set(opts) - (FREE_IN_FREE_TEMPLATE if template_kind == "free" else set())


def build_schema(base, opts, template_kind, main_outfit_tags, required=(), described=None):
    """required: caption fields of params fixed_traits -> enum and never empty.
    described: free fields the template describes; other non-vocab fields are dropped
    (e.g. shape_of_the_face with an older params file that has no face_shape mapping)."""
    fixed = vocab_fields(opts, template_kind)
    props = {k: v for k, v in base["properties"].items() if k not in DROP_FIELDS
             and (described is None or k in fixed or k in described)}
    out = {}
    for f, spec in props.items():
        is_array = "array" in [s.get("type") for s in spec.get("anyOf", [spec])]
        title = spec.get("title", f)
        if f in fixed and f in required:                # enum, never empty (fixed traits)
            tags = list(dict.fromkeys(tag_list(opts[f])))
            if not tags:
                raise ValueError(f"每張必填欄位 {f} 在詞表裡沒有 tag（先跑 vocab_tools.py check）")
            if is_array:
                out[f] = {"title": title, "type": "array", "uniqueItems": True, "minItems": 1,
                          "items": {"type": "string", "enum": tags}}
            else:
                out[f] = {"title": title, "type": "string", "enum": tags}
        elif f in fixed:                                # enum, may be empty when not visible
            tags = list(dict.fromkeys(tag_list(opts[f])))
            if not tags:                                # empty enum is rejected by the API (minItems 1)
                out[f] = {"title": title, "type": "array", "maxItems": 0} if is_array else \
                    {"title": title, "type": "string", "enum": [""]}
            elif is_array:
                listed = {"type": "array", "uniqueItems": True, "minItems": 1, "items": {"type": "string", "enum": tags}}
                out[f] = {"title": title, "anyOf": [{"type": "array", "maxItems": 0}, listed]}
            else:
                out[f] = {"title": title, "type": "string", "enum": tags + [""]}
        elif is_array:
            item = {"type": "string", "minLength": 1}
            if template_kind == "free" and f == "character_clothing_tags" and main_outfit_tags:
                item["not"] = {"enum": main_outfit_tags}
            out[f] = {"title": title, "type": "array", "items": item}
        else:
            out[f] = {"title": title, "type": "string", "minLength": 1}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
            "additionalProperties": False, "required": list(props), "properties": out}


def vocab_lines(opts, params, template_kind, required):
    """Prompt lines for the required / optional vocab fields, in template_vars order."""
    fixed, hints = vocab_fields(opts, template_kind), params.get("field_hints", {})
    lines = {True: [], False: []}
    for field in params["template_vars"]:
        if field not in fixed:
            continue
        tags = ", ".join(dict.fromkeys(tag_list(opts.get(field, [])))) or "(none, leave empty)"
        hint = f" ({hints[field]})" if field in hints else ""
        lines[field in required].append(f"- {field}{hint}: {tags}")
    return "\n".join(lines[True]) or "- (none)", "\n".join(lines[False]) or "- (none)"


def assign_groups(images, vocab, main_id, params):
    by_img = {im: o for o in vocab["outfits"] for im in o["images"]}
    outfits = {o["id"]: o for o in vocab["outfits"]}
    jobs = []
    for e in images:
        n, g = e["filename"], e["source_group"]
        if g == params["collected_group"]:
            o = by_img.get(n)
            if o is None:
                raise ValueError(f"{n}: collected image not in any vocab outfit")
            key = ("A", "fixed", main_id) if o["id"] == main_id else ("B_fixed", "fixed", o["id"])
        elif g in params["keep_outfit_groups"]:
            key = ("A", "fixed", main_id)
        elif g in params["change_outfit_groups"]:
            key = ("B_free", "free", main_id)
        else:
            raise ValueError(f"{n}: unknown source_group {g}")
        jobs.append(dict(name=n, group=key[0], template=key[1], outfit=outfits[key[2]], source_group=g))
    return jobs


def folder_images(folder, manifest, only=None):
    """--images 資料夾內的圖片（依檔名排序），每張以 manifest 查 source_group；不在 manifest 的圖直接報錯。"""
    by_name = {e["filename"]: e for e in manifest["images"]}
    names = sorted(f.name for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXT)
    if only:
        names = [n for n in names if n in set(only)]
    unknown = [n for n in names if n not in by_name]
    if unknown:
        raise ValueError(f"{folder} 中的圖不在 manifest：{unknown}")
    return [by_name[n] for n in names]


def check_model(model):
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    cache = json.loads((home / "models_cache.json").read_text(encoding="utf-8-sig"))
    if not any(m.get("slug") == model for m in cache.get("models", [])):
        sys.exit(f"模型 {model} 不在 {home}/models_cache.json：停止，請告知 使用者（不換模型）。")


# ---- run ----

def run_one(job, a, attempt, results):
    stem = Path(job["name"]).stem
    label = f"{job['group']}_{stem}" + (f"_retry{attempt}" if attempt else "")
    t0 = time.time()
    root, work, status, _ = run_isolated(job["prompt"], INSTRUCTIONS,
                                         [(str(a.images / job["name"]), f"images/{job['name']}"),
                                          (str(job["schema_file"]), "schema.json")],
                                         effort=a.effort, model=a.model, timeout=a.timeout,
                                         log_dir=a.out / "logs", label=label)
    t1 = time.time()
    f = work / "output" / f"{stem}.json"
    rec = dict(name=job["name"], group=job["group"], outfit=job["outfit"]["id"], call=label, attempt=attempt,
               codex_status=status, start=t0, end=t1, latency_s=round(t1 - t0, 1))
    try:
        data = parse_json(f)
        errs = [f"{e.json_path}: {e.message}" for e in jsonschema.Draft202012Validator(job["schema"]).iter_errors(data)]
        if not errs:
            data = {k: data[k] for k in job["schema"]["properties"]}          # schema 欄位順序
            stage, final = convert(data, a.trigger)
            for sub in ("json", "stage_txt", "txt"):
                (a.out / sub).mkdir(exist_ok=True)
            (a.out / "json" / f"{stem}.json").write_text(json.dumps(data, ensure_ascii=False), "utf-8")
            (a.out / "stage_txt" / f"{stem}.txt").write_text(stage, "utf-8")
            (a.out / "txt" / f"{stem}.txt").write_text(final, "utf-8")
    except Exception as e:
        data, errs = None, [f"caption failed: {type(e).__name__}: {e}"]
    rec["errors"] = errs
    if errs and f.is_file():
        d = a.out / "failed_raw"; d.mkdir(exist_ok=True)
        shutil.copyfile(f, d / f"{label}.json")
    shutil.rmtree(root, ignore_errors=True)
    with LOCK:
        results.append(rec)
        print(f"{label}: {'ok' if not errs else 'FAIL'} {rec['latency_s']}s status={status}", flush=True)
    return rec


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--character", required=True); p.add_argument("--work", required=True)
    p.add_argument("--trigger", required=True)
    p.add_argument("--images", type=Path, required=True); p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--vocab", type=Path, required=True); p.add_argument("--main-outfit", type=Path, required=True)
    p.add_argument("--templates", type=Path, default=TEMPLATES, help="模板資料夾")
    p.add_argument("--params", type=Path, default=TEMPLATES / "caption_vocab_params.json")
    p.add_argument("--schema", type=Path, default=TEMPLATES / "Character_Caption_BaseModel_Anima.schema.json")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", default="gpt-6-luna"); p.add_argument("--effort", default="max")
    p.add_argument("--workers", type=int, default=16); p.add_argument("--retries", type=int, default=2)
    p.add_argument("--timeout", type=float, default=1800)
    p.add_argument("--only", nargs="*", help="只打這些檔名（測試用）")
    p.add_argument("--dry-run", action="store_true", help="只寫 prompts/schemas，不呼叫 Codex")
    p.add_argument("--final-dir", type=Path, help="僅複製 JSON 與 txt 均成功的圖片及 txt（核對 sha256）")
    p.add_argument("--nsfw-schema", action="store_true", help="搭配 --workspace：使用 NSFW 的 --images 與 --out 預設路徑（images_nsfw、captions_nsfw；不預設 --final-dir）")
    a = parse_args(p, "caption", argv)
    a.out.mkdir(parents=True, exist_ok=True)
    params = json.loads(a.params.read_text("utf-8"))
    vocab = json.loads(a.vocab.read_text("utf-8"))
    main_o = json.loads(a.main_outfit.read_text("utf-8"))
    manifest = json.loads(a.manifest.read_text("utf-8"))
    base = json.loads(a.schema.read_text("utf-8"))
    tmpl = {"fixed": (a.templates / "caption_fixed_outfit_single.tmpl").read_text("utf-8"),
            "free": (a.templates / "caption_free_outfit_single.tmpl").read_text("utf-8")}
    main_tags = tag_list(main_o["tags"])
    images = folder_images(a.images, manifest, a.only)
    jobs = assign_groups(images, vocab, main_o["main_outfit_id"], params)
    for d in ("prompts", "schemas"):
        (a.out / d).mkdir(exist_ok=True)
    shutil.copyfile(a.params, a.out / "params.json")
    required = fixed_fields(params)
    for j in jobs:
        stem = Path(j["name"]).stem
        opts = field_options(vocab, params, j["outfit"], j["template"])
        described = set(re.findall(r"^- ([a-z_]+):", tmpl[j["template"]], re.M))
        j["schema"] = build_schema(base, opts, j["template"], main_tags, required, described)
        j["schema_file"] = a.out / "schemas" / f"{j['group']}_{j['outfit']['id']}.schema.json"
        j["schema_file"].write_text(json.dumps(j["schema"], ensure_ascii=False, indent=1), "utf-8")
        values = {"character": a.character, "work": a.work, "trigger": a.trigger,
                  "image_path": f"./input/images/{j['name']}", "output_path": f"./output/{stem}.json",
                  "schema_path": "./input/schema.json", "main_outfit_tags": ", ".join(main_tags)}
        for field, var in params["template_vars"].items():
            values[var] = ", ".join(dict.fromkeys(tag_list(opts.get(field, []))))
        values["required_vocab_lines"], values["optional_vocab_lines"] = vocab_lines(opts, params, j["template"], required)
        j["prompt"] = fill(tmpl[j["template"]], values)
        (a.out / "prompts" / f"{stem}.txt").write_text(j["prompt"], "utf-8")
    (a.out / "assignment.json").write_text(json.dumps(
        [{k: (v["id"] if k == "outfit" else v) for k, v in j.items() if k in ("name", "group", "template", "outfit", "source_group")}
         for j in jobs], ensure_ascii=False, indent=1), "utf-8")
    if a.dry_run:
        print(f"dry run: {len(jobs)} prompts in {a.out / 'prompts'}"); return 0
    check_model(a.model)
    results, t_start = [], time.time()
    todo = sorted(jobs, key=lambda j: j["name"])
    for attempt in range(a.retries + 1):
        if not todo:
            break
        with ThreadPoolExecutor(a.workers) as ex:
            recs = list(ex.map(lambda j: run_one(j, a, attempt, results), todo))
        failed = {r["name"] for r in recs if r["errors"]}
        todo = [j for j in todo if j["name"] in failed]
    ok = {r["name"] for r in results if not r["errors"]
          and (a.out / "json" / f"{Path(r['name']).stem}.json").is_file()
          and (a.out / "txt" / f"{Path(r['name']).stem}.txt").is_file()}
    groups = {}
    for r in results:
        g = groups.setdefault(r["group"], dict(start=r["start"], end=r["end"], calls=0, images=set()))
        g["start"], g["end"] = min(g["start"], r["start"]), max(g["end"], r["end"]); g["calls"] += 1; g["images"].add(r["name"])
    summary = dict(model=a.model, effort=a.effort, workers=a.workers, wall_s=round(time.time() - t_start, 1),
                   codex_calls=len(results), images=len(jobs), passed=len(ok),
                   failed=sorted(j["name"] for j in jobs if j["name"] not in ok),
                   first_try_pass=sum(1 for r in results if r["attempt"] == 0 and not r["errors"]),
                   avg_latency_s=round(sum(r["latency_s"] for r in results) / max(len(results), 1), 1),
                   groups={k: dict(wall_s=round(v["end"] - v["start"], 1), calls=v["calls"], images=len(v["images"]))
                           for k, v in groups.items()})
    (a.out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), "utf-8")
    (a.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), "utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if a.final_dir:
        a.final_dir.mkdir(parents=True, exist_ok=True)
        if a.manifest.resolve() != (a.final_dir / "manifest.json").resolve():
            shutil.copyfile(a.manifest, a.final_dir / "manifest.json")
        bad = []
        for j in jobs:
            src, dst = a.images / j["name"], a.final_dir / j["name"]
            t = a.out / "txt" / f"{Path(j['name']).stem}.txt"
            if j["name"] not in ok:
                dst.unlink(missing_ok=True)
                (a.final_dir / t.name).unlink(missing_ok=True)
                continue
            shutil.copy2(src, dst)
            if sha(src) != sha(dst):
                bad.append(j["name"])
            shutil.copyfile(t, a.final_dir / t.name)
        print(f"final dir {a.final_dir}: sha mismatches={bad}")
    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
