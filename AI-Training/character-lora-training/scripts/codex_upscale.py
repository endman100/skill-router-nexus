#!/usr/bin/env python3
"""Upscale small SFW images (long edge < MIN) with isolated Codex image generation.

Isolation via codex_isolated.py, model gpt-6.1-sol, effort medium,
--enable image_generation. Codex must keep content identical and only raise resolution.
Outer script verifies output dims (long edge >= MIN, aspect ratio within 3%) and never trusts
Codex blindly; failures are reported for the RealESRGAN fallback.
Only pass SFW images to this script.
"""
import argparse, json, shutil, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
from codex_isolated import run_isolated

INSTRUCTIONS = (
    "Upscale each input image so its long edge is at least {min}px while keeping the content "
    "identical: same character, face, hair, eyes, clothing, colours, pose, composition, background "
    "and aspect ratio. Only increase resolution and clarity; never add, remove or redraw content. "
    "Use the image viewer, shell tools (Python/Pillow) and image generation; write only in the workdir. "
    "Read generated images from CODEX_HOME/generated_images. No web access."
)

PROMPT = """請將 ./input 內每一張圖片提高解析度（放大），長邊至少 {min}px。
規則：內容必須與原圖完全相同——同一角色、臉、頭髮、眼睛、服裝、顏色、姿勢、構圖、背景與長寬比，
只提高解析度與清晰度，不可新增、刪除或重畫任何內容。
做法：逐張用圖片檢視工具開啟原圖，使用圖片生成工具 image_generation，以原圖為參考進行「僅放大／高解析重繪、內容不變」的生成。
生成圖片位於 {{CODEX_HOME}}/generated_images。若生成結果長寬比與原圖不同，用 Python/Pillow 將其裁切回原圖長寬比
（只裁去生成時多出的邊緣），再縮放到長邊至少 {min}px（不超過 1536px）。
完成後用圖片檢視工具並排比較原圖與結果：若角色或內容有任何改變，重新生成；重做兩次仍失敗則放棄該張。
最終檔案存成 ./output/<原檔名主體>.png（PNG）。用 Python 檢查每張輸出的尺寸，長邊必須 ≥ {min}px。
放棄或無法處理的圖片寫入 ./output/failed.json，格式為 JSON 陣列：[{{"filename": "...", "reason": "..."}}]；沒有失敗時寫 []。
檔案清單：
{files}
僅在工作目錄內寫入，不得存取網路。最終訊息彙總成功與失敗數量。"""


def check(src, out, min_long):
    with Image.open(src) as a, Image.open(out) as b:
        (w0, h0), (w1, h1) = a.size, b.size
    ok_size = max(w1, h1) >= min_long
    ok_ratio = abs((w1 / h1) / (w0 / h0) - 1) <= 0.03
    return ok_size and ok_ratio, dict(src_size=[w0, h0], out_size=[w1, h1], ok_size=ok_size, ok_ratio=ok_ratio)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out_dir", type=Path)
    p.add_argument("images", nargs="+", type=Path)
    p.add_argument("--min-long", type=int, default=768)
    p.add_argument("--batch", type=int, default=6)
    p.add_argument("--effort", default="medium")
    p.add_argument("--timeout", type=float, default=3600)
    p.add_argument("--keep-generated", type=Path, default=None, help="copy all Codex generated images here before cleanup")
    p.add_argument("--log-dir", type=Path, default=None, help="default: <out_dir>/codex_calls")
    a = p.parse_args(argv)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    a.log_dir = a.log_dir or a.out_dir / "codex_calls"
    results = {}
    for bi in range(0, len(a.images), a.batch):
        batch = a.images[bi:bi + a.batch]
        label = f"upscale_b{bi // a.batch + 1:02d}"
        inputs = [(str(s), s.stem + s.suffix.lower()) for s in batch]
        files = "\n".join(f"- {n}" for _, n in inputs)
        root, work, status, _ = run_isolated(
            PROMPT.format(min=a.min_long, files=files), INSTRUCTIONS.format(min=a.min_long), inputs,
            effort=a.effort, timeout=a.timeout, image_generation=True, log_dir=a.log_dir, label=label)
        failed = {}
        fj = work / "output" / "failed.json"
        if fj.is_file():
            try:
                failed = {e["filename"]: e.get("reason", "") for e in json.loads(fj.read_text("utf-8")) if isinstance(e, dict)}
            except Exception as e:
                failed = {}
        for src in batch:
            out = work / "output" / (src.stem + ".png")
            r = dict(source=str(src), call=label, codex_status=status)
            if out.is_file():
                try:
                    ok, info = check(src, out, a.min_long)
                except Exception as e:
                    ok, info = False, dict(error=str(e))
                r.update(info)
                if ok:
                    dest = a.out_dir / (src.stem + ".png")
                    shutil.copyfile(out, dest)
                    r.update(ok=True, output=str(dest))
                else:
                    r.update(ok=False, reason="output failed dimension/aspect check")
            else:
                r.update(ok=False, reason=failed.get(src.name) or failed.get(src.stem + src.suffix.lower()) or "no output")
            results[src.name] = r
            print(json.dumps(r, ensure_ascii=False), flush=True)
        if a.keep_generated:
            gi = root / "home" / "generated_images"
            if gi.is_dir():
                shutil.copytree(gi, a.keep_generated / label, dirs_exist_ok=True)
            if (work / "output").is_dir():
                shutil.copytree(work / "output", a.keep_generated / label / "_output", dirs_exist_ok=True)
        shutil.rmtree(root, ignore_errors=True)
    (a.out_dir / "codex_upscale_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), "utf-8")
    print(f"ok={sum(r['ok'] for r in results.values())} failed={sum(not r['ok'] for r in results.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
