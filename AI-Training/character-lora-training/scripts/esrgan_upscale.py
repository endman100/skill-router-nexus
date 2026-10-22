#!/usr/bin/env python3
"""最後備案放大：Codex（SFW）與 Grok 都放大不了的圖，用 RealESRGAN_x4plus_anime_6B 在 CPU 上放大（spandrel），
長邊超過 --max-long 用 LANCZOS 縮回。

用法：python3 esrgan_upscale.py <輸出資料夾> 圖1 圖2 ... [--model RealESRGAN_x4plus_anime_6B.pth] [--max-long 1280]
輸出：<輸出>/<stem>.png、<輸出>/esrgan_results.json
"""
import argparse, json, os, sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image
import spandrel

DEFAULT_MODEL = os.environ.get("ESRGAN_MODEL", "/workspace/models/realesrgan/RealESRGAN_x4plus_anime_6B.pth")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out_dir", type=Path)
    p.add_argument("images", nargs="+", type=Path)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--max-long", type=int, default=1280)
    p.add_argument("--threads", type=int, default=8)
    a = p.parse_args(argv)
    torch.set_num_threads(a.threads)
    model = spandrel.ModelLoader().load_from_file(a.model).eval()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    res = {}
    for f in a.images:
        im = Image.open(f).convert("RGB"); w, h = im.size
        x = torch.from_numpy(np.asarray(im, dtype=np.float32) / 255.).permute(2, 0, 1)[None]
        with torch.no_grad():
            y = model(x)[0].clamp(0, 1).permute(1, 2, 0).numpy()
        up = Image.fromarray((y * 255).round().astype(np.uint8))
        if max(up.size) > a.max_long:
            s = a.max_long / max(up.size)
            up = up.resize((round(up.width * s), round(up.height * s)), Image.Resampling.LANCZOS)
        dest = a.out_dir / (f.stem + ".png"); up.save(dest)
        res[f.name] = dict(source=str(f), src_size=[w, h], out_size=list(up.size), output=str(dest),
                           method="RealESRGAN_x4plus_anime_6B (CPU)")
        print(json.dumps(res[f.name]), flush=True)
    (a.out_dir / "esrgan_results.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    sys.exit(main())
