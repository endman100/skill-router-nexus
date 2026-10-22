#!/usr/bin/env python3
"""WD Tagger（SmilingWolf wd-eva02-large-tagger-v3，ONNX CPU），在 Grok VM 本機跑。
dedup_split.py 用它分 sfw/nsfw；Grok 處理 NSFW／被拒圖時也可直接用它看 tag。

用法：python3 wdtag.py [--model-dir DIR] 圖1 圖2 ...   → stdout 印出 JSON
模型資料夾：--model-dir，或環境變數 WD_TAGGER_DIR，預設 /workspace/models/wd-eva02-large-tagger-v3
"""
import argparse, csv, json, os, sys
import numpy as np
from PIL import Image
import onnxruntime as ort

Image.MAX_IMAGE_PIXELS = None
DEFAULT_MODEL_DIR = os.environ.get("WD_TAGGER_DIR", "/workspace/models/wd-eva02-large-tagger-v3")
SFW_RATINGS = ("general", "sensitive")          # questionable / explicit -> nsfw


class Tagger:
    def __init__(self, model_dir=DEFAULT_MODEL_DIR):
        rows = list(csv.DictReader(open(f"{model_dir}/selected_tags.csv", encoding="utf-8")))
        self.names = [r["name"] for r in rows]
        self.cats = [int(r["category"]) for r in rows]
        so = ort.SessionOptions(); so.intra_op_num_threads = os.cpu_count()
        self.sess = ort.InferenceSession(f"{model_dir}/model.onnx", so, providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0]
        self.size = self.inp.shape[1]

    def _prep(self, rgb):
        w, h = rgb.size; m = max(w, h)
        sq = Image.new("RGB", (m, m), (255, 255, 255)); sq.paste(rgb, ((m - w) // 2, (m - h) // 2))
        return np.asarray(sq.resize((self.size, self.size), Image.BICUBIC), dtype=np.float32)[:, :, ::-1]

    def tag(self, rgb, gthr=0.35, cthr=0.1):
        p = self.sess.run(None, {self.inp.name: self._prep(rgb)[None]})[0][0]
        order = np.argsort(-p)
        rating = {self.names[i]: round(float(p[i]), 4) for i in range(len(p)) if self.cats[i] == 9}
        general = {self.names[i]: round(float(p[i]), 4) for i in order if self.cats[i] == 0 and p[i] >= gthr}
        character = {self.names[i]: round(float(p[i]), 4) for i in order if self.cats[i] == 4 and p[i] >= cthr}
        top = max(rating, key=rating.get)
        return dict(rating=rating, top_rating=top, bucket="sfw" if top in SFW_RATINGS else "nsfw",
                    general=general, character=character)


def first_rgb(im):
    """First frame, alpha composited on white."""
    try:
        im.seek(0)
    except Exception:
        pass
    im = im.convert("RGBA"); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
    return bg.convert("RGB")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("images", nargs="+")
    p.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    a = p.parse_args(argv)
    t = Tagger(a.model_dir)
    out = []
    for path in a.images:
        with Image.open(path) as im:
            size, rgb = list(im.size), first_rgb(im)
        out.append(dict(file=os.path.basename(path), size=size, **t.tag(rgb)))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
