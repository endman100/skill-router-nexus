#!/usr/bin/env python3
"""Resize pre-step (使用者's spec): long edge >1280 -> LANCZOS 1280; long edge <768 -> listed for upscale
(Codex for SFW, RealESRGAN fallback). Writes OUT/<group>/<group>__<filename>.png and OUT/resize_manifest.json."""
import argparse, hashlib, json, sys
from pathlib import Path
from ws import parse_args
from PIL import Image, ImageOps
EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("groups", nargs="+", help="name=dir")
    p.add_argument("--min-long", type=int, default=768)
    p.add_argument("--max-long", type=int, default=1280)
    a = parse_args(p, "resize", argv)
    man = []
    for g in a.groups:
        name, d = g.split("=", 1)
        (a.out / name).mkdir(parents=True, exist_ok=True)
        (a.out / "_needs_upscale" / name).mkdir(parents=True, exist_ok=True)
        for f in sorted(Path(d).iterdir()):
            if f.suffix.lower() not in EXT or not f.is_file():
                continue
            with Image.open(f) as im:
                im = ImageOps.exif_transpose(im)
                im = im.convert("RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB")
                if im.mode == "RGBA":
                    bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg.convert("RGB")
                w, h = im.size; action = "none"
                if max(w, h) > a.max_long:
                    s = a.max_long / max(w, h)
                    im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.Resampling.LANCZOS); action = "downscale_lanczos"
                filename = name + "__" + f.name + ".png"
                dest = a.out / name / filename
                if max(w, h) < a.min_long:
                    dest = a.out / "_needs_upscale" / name / filename; action = "needs_upscale"
                im.save(dest)
            man.append(dict(group=name, source=str(f), source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),
                            source_size=[w, h], action=action, output=str(dest), output_size=list(im.size),
                            target_long=a.min_long))
    old = json.loads((a.out / "resize_manifest.json").read_text()) if (a.out / "resize_manifest.json").is_file() else []
    keep = [m for m in old if m["group"] not in {g.split("=")[0] for g in a.groups}]
    (a.out / "resize_manifest.json").write_text(json.dumps(keep + man, ensure_ascii=False, indent=1))
    from collections import Counter
    print(Counter((m["group"], m["action"]) for m in man))

if __name__ == "__main__":
    main()
