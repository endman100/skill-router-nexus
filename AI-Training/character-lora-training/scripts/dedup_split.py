#!/usr/bin/env python3
"""清理第 1、2 步（Grok VM 本機，不呼叫 Codex）：合併 Codex/Grok 收集圖 → sha256 去重 → pHash 去近似圖
（距離 <= --phash-dist，保留面積最大者）→ WD Tagger rating 分流：general/sensitive → sfw/，questionable/explicit → nsfw/。

用法：
  python3 dedup_split.py <輸出資料夾> codex=<codex收集資料夾> grok=<grok收集資料夾> [--phash-dist 6] [--model-dir DIR]
輸出：<輸出>/dedup/、<輸出>/sfw/、<輸出>/nsfw/（統一流水號檔名，非 png/jpg/webp 轉 png）、
      <輸出>/input_mapping.json（全部輸入圖片的新檔名與原始路徑）、
      <輸出>/dedup.json（保留／去掉的圖與原因）、<輸出>/rating.json（每張 rating 分數與分流）。
"""
import argparse, hashlib, json, os, shutil, sys
from pathlib import Path
from ws import parse_args
from PIL import Image
import imagehash
sys.path.insert(0, str(Path(__file__).parent))
from wdtag import Tagger, first_rgb, DEFAULT_MODEL_DIR

Image.MAX_IMAGE_PIXELS = None
SIDE = {".txt", ".json", ".md"}
KEEP_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def load(sources):
    items, skipped = [], []
    for src, d in sources:
        for f in sorted(Path(d).rglob("*")):
            if not f.is_file() or f.suffix.lower() in SIDE:
                continue
            try:
                with Image.open(f) as im:
                    fmt, (w, h), frames, rgb = im.format, im.size, getattr(im, "n_frames", 1), first_rgb(im)
            except Exception as e:
                skipped.append(dict(file=f"{src}/{f.relative_to(d)}", reason=f"{type(e).__name__}: {e}")); continue
            items.append(dict(source=src, path=f, orig=f"{src}/{f.relative_to(d)}",
                              name=f"{len(items) + 1:06d}{f.suffix.lower()}", ext=f.suffix.lower(),
                              fmt=fmt, w=w, h=h, frames=frames, sha=hashlib.sha256(f.read_bytes()).hexdigest(),
                              phash=imagehash.phash(rgb), rgb=rgb))
    return items, skipped


def dedup(items, max_dist):
    seen, uniq, dropped = {}, [], []
    for it in items:
        if it["sha"] in seen:
            dropped.append(dict(file=it["orig"], duplicate_of=seen[it["sha"]]["name"], reason="sha256"))
        else:
            seen[it["sha"]] = it; uniq.append(it)
    kept = []
    for it in sorted(uniq, key=lambda x: (-x["w"] * x["h"], -x["path"].stat().st_size, x["orig"])):
        best = min(((k, int(it["phash"] - k["phash"])) for k in kept), key=lambda kd: kd[1], default=None)
        if best and best[1] <= max_dist:
            dropped.append(dict(file=it["orig"], duplicate_of=best[0]["name"], reason="phash", distance=best[1]))
            it["dupof"] = best[0]
        else:
            kept.append(it)
    by_name = {i["name"]: i for i in uniq}
    for dr in dropped:            # sha twin of an image that was later phash-dropped -> point to final kept image
        o = by_name.get(dr["duplicate_of"])
        if dr["reason"] == "sha256" and o is not None and "dupof" in o:
            dr["duplicate_of"] = o["dupof"]["name"]
    return sorted(kept, key=lambda x: x["name"]), dropped


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out", type=Path)
    p.add_argument("sources", nargs="+", help="name=dir，例如 codex=collect/codex grok=collect/grok")
    p.add_argument("--phash-dist", type=int, default=6)
    p.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    a = parse_args(p, "dedup", argv)
    sources = [s.split("=", 1) for s in a.sources]
    items, skipped = load(sources)
    kept, dropped = dedup(items, a.phash_dist)
    for sub in ("dedup", "sfw", "nsfw"):
        (a.out / sub).mkdir(parents=True, exist_ok=True)
    mapping = [dict(filename=k["name"], source=k["source"], original=k["orig"],
                    original_path=str(k["path"].resolve())) for k in items]
    (a.out / "input_mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), "utf-8")
    for k in kept:
        shutil.copy2(k["path"], a.out / "dedup" / k["name"])
    (a.out / "dedup.json").write_text(json.dumps(dict(
        input_count=len(items), kept_count=len(kept), dropped=dropped, skipped=skipped,
        kept=[dict(file=k["name"], original=k["orig"], width=k["w"], height=k["h"], sha256=k["sha"], phash=str(k["phash"]))
              for k in kept]), ensure_ascii=False, indent=1), "utf-8")
    tagger, res = Tagger(a.model_dir), []
    for k in kept:
        t = tagger.tag(k["rgb"])
        name, conv = k["name"], None
        if k["ext"] in KEEP_EXT:
            shutil.copy2(k["path"], a.out / t["bucket"] / name)
        else:                                   # gif/bmp/... -> first frame png
            name = Path(name).stem + ".png"; k["rgb"].save(a.out / t["bucket"] / name); conv = "png"
        res.append(dict(file=name, dedup_file=k["name"], scores={r: t["rating"][r] for r in t["rating"]},
                        top=t["top_rating"], bucket=t["bucket"], converted_to=conv))
    sfw = sum(r["bucket"] == "sfw" for r in res)
    (a.out / "rating.json").write_text(json.dumps(dict(sfw=sfw, nsfw=len(res) - sfw, results=res),
                                                  ensure_ascii=False, indent=1), "utf-8")
    print(f"input={len(items)} kept={len(kept)} dropped={len(dropped)} skipped={len(skipped)} sfw={sfw} nsfw={len(res) - sfw}")


if __name__ == "__main__":
    sys.exit(main())
