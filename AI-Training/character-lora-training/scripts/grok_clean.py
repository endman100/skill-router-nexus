#!/usr/bin/env python3
"""逐張清理 NSFW 與 Codex 拒絕的圖片，保留上游分流。

最小權限（grok_headless.PROFILES["image"]）：每張圖複製到 <out>/.grok_clean_*/（沙箱 lora_min），
Grok 只有 read_file + image_edit（去字），無 shell、無寫檔、無網路。裁切改由 Grok 在 structuredOutput
回報 crop（0–1 比例），本腳本以 PIL 套用到最終圖（image_edit 結果或原圖）。
"""
import argparse, io, json, shutil
from pathlib import Path
from PIL import Image
from ws import parse_args
from codex_collect import is_image
from grok_headless import options, retry, report, write_json, generated_image, entry, isolated_cwd

SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["decision", "rating", "reason", "output_file", "crop"], "properties": {
              "decision": {"enum": ["keep", "reject", "suspicious"]},
              "rating": {"enum": ["sfw", "nsfw"]}, "reason": {"type": "string"},
              "output_file": {"type": "string"},
              "crop": {"type": "object", "additionalProperties": False,
                       "required": ["left", "top", "right", "bottom"],
                       "properties": {k: {"type": "number", "minimum": 0, "maximum": 1}
                                      for k in ("left", "top", "right", "bottom")}}}}
PROMPT = """請以圖片檢視工具開啟 {source}，清理目標角色：{target}。
確認角色存在、品質足夠，拒收線稿、草稿、黑白或單色圖。
若有文字、對話框或浮水印，使用 image_edit（image=["{source}"]）移除，檢視結果並與原圖比較，
確認臉、頭髮、眼睛、服裝、顏色、姿勢及比例未走樣；失敗則拒收。
可疑內容（例如外觀未成年且不適合收錄的圖片）標為 suspicious 並排除。
依圖片判定 rating 為 sfw 或 nsfw。你沒有 shell 或寫檔工具，不要自行存檔或裁切：
output_file 填 image_edit 產生的 session 圖片絕對路徑；不需去字則填空字串（使用原圖）。
crop 填只保留目標角色及少量邊界的裁切框（相對最終圖寬高的 0–1 比例：left、top、right、bottom；
不需裁切則 0,0,1,1），由腳本套用。
拒收時說明 reason。遇工具拒絕，記錄失敗，不改寫要求繞過限制。以指定 schema 回傳。"""


def cropped_png(path, box):
    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        l, t, r, b = (round(box[k] * size) for k, size in
                      (("left", w), ("top", h), ("right", w), ("bottom", h)))
        if r - l < 32 or b - t < 32:
            raise ValueError(f"crop box too small: {box}")
        if (l, t, r, b) != (0, 0, w, h):
            im = im.crop((l, t, r, b))
        buffer = io.BytesIO()
        im.save(buffer, format="PNG")
    return buffer.getvalue()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True)
    for name in ("nsfw", "sfw", "codex-clean", "out", "collected-sfw", "collected-nsfw"):
        p.add_argument("--" + name, type=Path, required=True)
    options(p, only=True)
    a = parse_args(p, "grok_clean", argv)
    paths = [(f, True) for f in sorted(a.nsfw.glob("*")) if f.is_file() and is_image(f)]
    rejected_file = a.codex_clean / "rejected.json"
    if rejected_file.exists():
        paths += [(a.sfw / e["filename"], False) for e in json.loads(rejected_file.read_text("utf-8"))]
    if a.only:
        paths = [(f, n) for f, n in paths if f.name in a.only]
    if a.dry_run:
        print(json.dumps(dict(inputs=[str(f) for f, _ in paths], out=str(a.out),
                              copy_codex=[str(f) for f in a.codex_clean.glob("*.png")]), ensure_ascii=False))
        return 0
    a.collected_sfw.mkdir(parents=True, exist_ok=True)
    a.collected_nsfw.mkdir(parents=True, exist_ok=True)
    for f in a.codex_clean.glob("*.png"):
        shutil.copy2(f, a.collected_sfw / f.name)
    results, rejected, suspicious = [], [], []
    for index, (src, from_nsfw) in enumerate(paths, 1):
        rec = dict(filename=src.name, source=str(src), from_nsfw=from_nsfw, ok=False)
        try:
            with isolated_cwd(a.out, "clean") as work:
                attached = work / src.name
                shutil.copy2(src, attached)
                def accept(result):
                    data = result["structured"]
                    if data["decision"] != "keep":
                        return data, None
                    output = generated_image(result) if data["output_file"] else attached
                    return data, cropped_png(output, data["crop"])
                result, error = retry(PROMPT.format(source=attached, target=a.target), work,
                                      a.out / "logs", f"{index:04d}_{src.stem}", a, schema=SCHEMA, accept=accept,
                                      profile="image")
                if result:
                    data, image = result
                    rec.update(data)
                    if data["decision"] == "keep":
                        dest = (a.collected_nsfw if from_nsfw or data["rating"] == "nsfw" else a.collected_sfw) / (src.stem + ".png")
                        dest.write_bytes(image)
                        rec.update(ok=True, output=str(dest))
                    elif data["decision"] == "suspicious":
                        suspicious.append(rec.copy())
                        print(f"可疑內容，已排除：{src.name}：{data['reason']}")
                    else:
                        rejected.append(rec.copy())
                else:
                    rec["reason"] = error
                    rejected.append(rec.copy())
        except (OSError, ValueError) as exc:
            rec["reason"] = str(exc)
            rejected.append(rec.copy())
        for folder in (a.collected_sfw, a.collected_nsfw):
            old = folder / (src.stem + ".png")
            if not rec["ok"] or str(old) != rec["output"]:
                old.unlink(missing_ok=True)
        results.append(rec)
    write_json(a.out / "rejected.json", rejected)
    write_json(a.out / "suspicious.json", suspicious)
    return report(a.out, results)


if __name__ == "__main__":
    raise SystemExit(entry(main))
