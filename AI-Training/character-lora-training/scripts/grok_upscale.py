#!/usr/bin/env python3
"""以 Grok Build 逐張放大，檢查長邊與長寬比；失敗交由使用者選擇 ESRGAN。

最小權限（grok_headless.PROFILES["image"]）：每張圖複製到 <out_dir>/.grok_upscale_*/（沙箱 lora_min），
Grok 只有 read_file + image_edit；原圖尺寸寫在 prompt 中，不需 shell。
"""
import argparse, shutil
from pathlib import Path
from PIL import Image
from ws import parse_args
from codex_upscale import check
from grok_headless import options, retry, report, png_bytes, generated_image, IMAGE_SCHEMA, entry, isolated_cwd


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out_dir", type=Path)
    p.add_argument("images", nargs="+", type=Path)
    p.add_argument("--min-long", type=int, default=768)
    p.add_argument("--batch", type=int, default=1, help="相容參數；仍逐張呼叫")
    p.add_argument("--keep-generated", type=Path)
    p.add_argument("--log-dir", type=Path)
    options(p, only=True)
    a = parse_args(p, "grok_upscale", argv)
    images = [p for p in a.images if not a.only or p.name in a.only]
    if a.dry_run:
        print(f"images={[str(p) for p in images]}; out={a.out_dir}; min_long={a.min_long}; aspect_error<=3%")
        return 0
    a.out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for src in images:
        with isolated_cwd(a.out_dir, "upscale") as work:
            attached = work / src.name
            shutil.copy2(src, attached)
            with Image.open(attached) as im:
                width, height = im.size
            prompt = (f"請檢視 {attached}（原圖 {width}x{height}px），呼叫一次單圖 image_edit，image=[{str(attached)!r}]。"
                      f"same image, higher resolution, no content change; long edge at least {a.min_long}px。"
                      "保持相同角色、臉、頭髮、眼睛、服裝、顏色、姿勢、構圖、背景與長寬比。"
                      "檢視並比較結果，回傳 session 中最終圖片絕對路徑 output_file。"
                      "遇工具拒絕則記錄失敗，不改寫要求繞過限制。")
            def accept(result):
                output = generated_image(result)
                if a.keep_generated:
                    shutil.copytree(result["session_dir"] / "images",
                                    a.keep_generated / result["session_id"], dirs_exist_ok=True)
                ok, info = check(src, output, a.min_long)
                if not ok:
                    raise ValueError(f"output failed dimension/aspect check: {info}")
                (a.out_dir / (src.stem + ".png")).write_bytes(png_bytes(output))
                return info
            result, error = retry(prompt, work, a.log_dir or a.out_dir / "logs", src.stem, a,
                                  schema=IMAGE_SCHEMA, accept=accept, profile="image", max_turns=12)
            results.append(dict(name=src.name, ok=result is not None, error=error, dimensions=result))
    return report(a.out_dir, results)


if __name__ == "__main__":
    raise SystemExit(entry(main))
