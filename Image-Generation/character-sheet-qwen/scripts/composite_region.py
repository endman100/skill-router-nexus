"""Keep a Qwen correction inside an inspected region; retain the clean base outside it."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def composite(base, candidate, box, feather=3):
    if base.size != candidate.size:
        raise ValueError("Base and candidate must have identical dimensions; do not stretch an edit")
    left, top, right, bottom = box
    if not (0 <= left < right < base.width and 0 <= top < bottom < base.height):
        raise ValueError("Correction rectangle must lie inside the images")
    if feather < 0:
        raise ValueError("Feather must be nonnegative")
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    return Image.composite(candidate.convert("RGB"), base.convert("RGB"), mask), mask


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--box", nargs=4, required=True, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"))
    parser.add_argument("--feather", type=float, default=3)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Retain existing versions; choose a new output filename")
    with Image.open(args.base) as base, Image.open(args.candidate) as candidate:
        result, mask = composite(base, candidate, tuple(args.box), args.feather)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mask_path = args.output.with_suffix(".mask.png")
    mask.save(mask_path)
    result.save(args.output)
    record = {
        "operation": "deterministic region composite of Qwen-generated pixels",
        "base": str(args.base.resolve()), "candidate": str(args.candidate.resolve()),
        "mask": str(mask_path.resolve()), "box_inclusive": args.box, "feather_px": args.feather,
        "mask_nonzero_bbox": list(mask.getbbox()),
        "sha256": {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in [args.base, args.candidate, mask_path, args.output]},
    }
    args.output.with_suffix(".composite.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
