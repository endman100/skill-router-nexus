#!/usr/bin/env python3
"""打標 a（詞表）的小工具。詞表由 grok_vocab.py 呼叫 Grok Build 看拼圖與原圖建立，這支程式不呼叫任何模型。

  sheets：從 manifest 取出收集圖（source_group = collected，不含生成圖），做 8 格拼圖（每格標檔名），
          寫 names.json 與 vocab.schema.json，給 Grok 看圖寫 vocab.json。
  check ：驗證 vocab.json（JSON schema、每張收集圖恰屬一套服裝、tag 不重複／不過長／無佔位詞），
          檢查每個 trait 都對應到 caption 欄位、固定欄位有選項；通過後寫 vocab_summary.md，
          給 --main-outfit 時同時寫 main_outfit.json。

用法：
  python3 vocab_tools.py sheets --images <訓練資料夾> --manifest <訓練資料夾>/manifest.json --out <vocab資料夾>
  python3 vocab_tools.py check --vocab <vocab資料夾>/vocab.json --names <vocab資料夾>/names.json \
      [--params ../templates/caption_vocab_params.json] [--main-outfit outfit_xxx]
"""
import argparse, json, sys
from pathlib import Path
from ws import parse_args
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DEFAULT_PARAMS = HERE.parent / "templates" / "caption_vocab_params.json"
BANNED = ("not discernible", "not visible", "unknown", "sheet", "panel", "inset", "layout", "reference")
OPTIONAL_FIELDS = {"character_head_features_tags", "character_accessories_tags", "character_clothing_tags"}


def make_schema():
    tag = {"type": "string", "minLength": 2, "maxLength": 40, "pattern": "^[a-z0-9][a-z0-9 \\-]*[a-z0-9]$"}
    vis = {"enum": ["always", "sometimes"]}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object", "additionalProperties": False,
        "required": ["character_features", "outfits"],
        "properties": {
            "character_features": {"type": "array", "minItems": 3, "items": {
                "type": "object", "additionalProperties": False, "required": ["trait", "tag", "visibility"],
                "properties": {"trait": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"}, "tag": tag, "visibility": vis}}},
            "outfits": {"type": "array", "minItems": 1, "items": {
                "type": "object", "additionalProperties": False, "required": ["id", "name", "tags", "images"],
                "properties": {
                    "id": {"type": "string", "pattern": "^outfit_[a-z0-9_]+$"},
                    "name": {"type": "string", "minLength": 1, "maxLength": 60},
                    "tags": {"type": "array", "minItems": 1, "items": {
                        "type": "object", "additionalProperties": False, "required": ["tag", "visibility"],
                        "properties": {"tag": tag, "visibility": vis}}},
                    "images": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string"}}}}},
        },
    }


def make_sheets(folder, names, out_dir, per=8, cols=4, cell=320):
    """folder：資料夾，或 {檔名: 路徑}（NSFW 收集圖在 manifest 的 nsfw_dir，只給 Grok 看）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("sheet_*.jpg"):
        old.unlink()
    font = ImageFont.load_default()
    label_h, rows = 18, (per + cols - 1) // cols
    sheets = []
    for k in range(0, len(names), per):
        sheet = Image.new("RGB", (cols * cell, rows * (cell + label_h)), "white")
        d = ImageDraw.Draw(sheet)
        for j, n in enumerate(names[k:k + per]):
            im = Image.open(folder[n] if isinstance(folder, dict) else folder / n).convert("RGB")
            im.thumbnail((cell, cell))
            x, y = (j % cols) * cell, (j // cols) * (cell + label_h)
            d.text((x + 4, y + 2), n, fill="black", font=font)
            sheet.paste(im, (x + (cell - im.width) // 2, y + label_h + (cell - im.height) // 2))
        p = out_dir / f"sheet_{k // per + 1:02d}.jpg"
        sheet.save(p, quality=88)
        sheets.append(p)
    return sheets


def validate(data, names, schema):
    import jsonschema
    errs = [f"schema: {e.json_path}: {e.message}" for e in jsonschema.Draft202012Validator(schema).iter_errors(data)]
    if errs:
        return errs
    seen = {}
    for o in data["outfits"]:
        for im in o["images"]:
            seen.setdefault(im, []).append(o["id"])
    errs += [f"image {n} not assigned to any outfit" for n in names if n not in seen]
    errs += [f"image {n} assigned to several outfits {v}" for n, v in seen.items() if len(v) > 1]
    errs += [f"unknown image {n}" for n in seen if n not in names]
    ids = [o["id"] for o in data["outfits"]]
    errs += [f"duplicate outfit id {i}" for i in set(ids) if ids.count(i) > 1]
    feat = [f["tag"] for f in data["character_features"]]
    errs += [f"duplicate character tag {x}" for x in set(feat) if feat.count(x) > 1]
    for o in data["outfits"]:
        ot = [t["tag"] for t in o["tags"]]
        errs += [f"{o['id']}: duplicate tag {x}" for x in set(ot) if ot.count(x) > 1]
        errs += [f"{o['id']}: tag {x} is already a character feature" for x in ot if x in feat]
    for x in feat + [t["tag"] for o in data["outfits"] for t in o["tags"]]:
        if len(x.split()) > 4:
            errs.append(f"tag too long (>4 words): {x}")
        if any(b in x for b in BANNED):
            errs.append(f"banned word in tag: {x}")
    return errs


def summary_md(data):
    lines = ["| 特徵 | tag | visibility |", "|---|---|---|"]
    lines += [f"| {f['trait']} | {f['tag']} | {f['visibility']} |" for f in data["character_features"]]
    lines += ["", "| id | 名稱 | 圖片數 | tags |", "|---|---|---:|---|"]
    for o in data["outfits"]:
        tags = ", ".join(t["tag"] + ("" if t["visibility"] == "always" else "*") for t in o["tags"])
        lines.append(f"| {o['id']} | {o['name']} | {len(o['images'])} | {tags} |")
    lines += ["", "\\* = sometimes"]
    return "\n".join(lines) + "\n"


# ---- trait -> caption field mapping (shared with codex_caption_v2.py) ----

def _match(trait, pattern):
    return trait.startswith(pattern[:-1]) if pattern.endswith("*") else trait == pattern


def trait_field(trait, field_traits):
    """Exact trait names win; otherwise the longest matching `prefix*` pattern. None = unmapped."""
    for field, pats in field_traits.items():
        if trait in pats:
            return field
    best = max(((len(p), f) for f, pats in field_traits.items() for p in pats if p.endswith("*") and _match(trait, p)),
               default=None)
    return best[1] if best else None


def feature_options(features, field_traits):
    """caption field -> [{tag, visibility}] in field_traits pattern order, then vocab order."""
    opts = {}
    for field, pats in field_traits.items():
        out = opts.setdefault(field, [])
        for pat in pats:
            for f in features:
                item = {"tag": f["tag"], "visibility": f["visibility"]}
                if _match(f["trait"], pat) and trait_field(f["trait"], field_traits) == field and item not in out:
                    out.append(item)
    return opts


def coverage(vocab, params):
    errs, warns = [], []
    ft = params["field_traits"]
    for f in vocab["character_features"]:
        if trait_field(f["trait"], ft) is None:
            errs.append(f"trait {f['trait']} ({f['tag']}) 沒有對應的 caption 欄位（改 trait 名或 params field_traits）")
    opts = feature_options(vocab["character_features"], ft)
    for field in params["template_vars"]:
        if field in ft and not opts.get(field):
            (warns if field in OPTIONAL_FIELDS else errs).append(f"固定欄位 {field} 在詞表裡沒有任何 tag")
    return errs, warns, opts


def cmd_sheets(a):
    m = json.loads(a.manifest.read_text("utf-8"))
    entries = [i for i in m["images"] if i["source_group"] == a.group]
    names = sorted(i["filename"] for i in entries)
    nsfw_dir = Path(m["nsfw_dir"]) if m.get("nsfw_dir") else None
    paths = {i["filename"]: (nsfw_dir if i.get("nsfw") and nsfw_dir else a.images) / i["filename"] for i in entries}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "names.json").write_text(json.dumps(names, ensure_ascii=False), "utf-8")
    (a.out / "vocab.schema.json").write_text(json.dumps(make_schema(), indent=1), "utf-8")
    sheets = make_sheets(paths, names, a.out / "contact_sheets", per=a.per)
    print(f"{len(names)} 張收集圖，{len(sheets)} 張拼圖 -> {a.out / 'contact_sheets'}")


def cmd_check(a):
    data = json.loads(a.vocab.read_text("utf-8"))
    names = json.loads(a.names.read_text("utf-8"))
    params = json.loads(a.params.read_text("utf-8"))
    errs = validate(data, names, make_schema())
    cerrs, warns, opts = coverage(data, params) if not errs else ([], [], {})
    errs += cerrs
    outfits = {o["id"]: o for o in data.get("outfits", [])}
    if a.main_outfit and a.main_outfit not in outfits:
        errs.append(f"main outfit {a.main_outfit} 不在 outfits 裡")
    for w in warns:
        print("WARN", w)
    if errs:
        print("\n".join("ERROR " + e for e in errs)); return 1
    for field, o in opts.items():
        print(f"{field}: {', '.join(t['tag'] for t in o) or '-'}")
    (a.vocab.parent / "vocab_summary.md").write_text(summary_md(data), "utf-8")
    if a.main_outfit:
        o = outfits[a.main_outfit]
        (a.vocab.parent / "main_outfit.json").write_text(json.dumps(dict(
            main_outfit_id=o["id"], name=o["name"], tags=o["tags"], image_count=len(o["images"])),
            ensure_ascii=False, indent=2), "utf-8")
    print("PASS")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheets")
    s.add_argument("--images", type=Path, required=True); s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True); s.add_argument("--group", default="collected")
    s.add_argument("--per", type=int, default=8)
    c = sub.add_parser("check")
    c.add_argument("--vocab", type=Path, required=True); c.add_argument("--names", type=Path, required=True)
    c.add_argument("--params", type=Path, default=DEFAULT_PARAMS); c.add_argument("--main-outfit")
    a = parse_args(p, {"sheets": s, "check": c}, argv)
    return cmd_sheets(a) if a.cmd == "sheets" else cmd_check(a)


if __name__ == "__main__":
    sys.exit(main())
