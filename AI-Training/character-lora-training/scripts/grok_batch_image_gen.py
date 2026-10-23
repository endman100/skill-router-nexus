#!/usr/bin/env python3
"""以 Grok Build 維持服裝生成 N 張，重跑僅補足有效 PNG 缺額。"""
import argparse, hashlib, json
from pathlib import Path
from ws import parse_args
from codex_batch_image_gen import existing_images, next_number, update_missing_json, positive_int
from grok_headless import options, retry, write_json, generated_image, png_bytes, IMAGE_SCHEMA, entry

PROMPT = "幫我維持服裝設計與角色特徵 生成1張這個角色在不同背景 不同姿勢 不同動作 不同表情 不同長寬比的一張圖 採用乾淨的日系動畫賽璐璐上色，線稿俐落，色塊均勻，陰影簡潔，漸層平滑。皮膚與服裝表面乾淨，不添加膠片顆粒、紙張紋理、斑駁筆觸、細碎雜點或過度銳化。背景使用簡潔的動畫美術風格，避免密集零碎的材質細節。保留角色與服裝的必要細節。"
RATIOS = ("1:1", "4:3", "3:4", "16:9", "9:16")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("n", type=positive_int, nargs="?", default=30)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--scenes", type=Path)
    p.add_argument("--max-rounds", type=positive_int, default=3)
    options(p, only=True)
    a = parse_args(p, "grok_generate", argv)
    folder = a.out / "keep_outfit"
    valid, invalid = existing_images(folder) if folder.exists() else ([], [])
    number = next_number(folder) if folder.exists() else 1
    need = max(0, a.n - len(valid))
    scenes_file = a.scenes or a.out / "scenes.json"
    print(json.dumps(dict(target=a.n, existing_valid=len(valid), existing_invalid=[p.name for p in invalid],
                          to_generate=need, next_filename=f"{number:02d}.png", scenes=str(scenes_file),
                          reference=str(a.reference), aspect_ratios=RATIOS, only=a.only), ensure_ascii=False))
    if a.dry_run:
        return 0
    folder.mkdir(parents=True, exist_ok=True)
    results, last_error = [], None
    scenes = []
    if need:
        if scenes_file.exists():
            scenes = json.loads(scenes_file.read_text("utf-8"))["scenes"]
        else:
            schema = {"type": "object", "required": ["scenes"], "additionalProperties": False,
                      "properties": {"scenes": {"type": "array", "minItems": a.n, "maxItems": a.n,
                          "uniqueItems": True, "items": {"type": "string"}}}}
            prompt = (f"請設計 {a.n} 個互不相同的 SFW 角色圖場景，各自包含背景、姿勢、動作、表情、鏡頭。"
                      "背景為乾淨、具真實場景感的動畫美術背景；服裝維持參考圖。回傳 scenes 字串清單。")
            result, last_error = retry(prompt, a.out, a.out / "logs", "scenes", a, schema=schema)
            if result:
                write_json(scenes_file, result["structured"])
                scenes = result["structured"]["scenes"]
        if not scenes and not last_error:
            last_error = "Empty scenes list"
    call_args = argparse.Namespace(**vars(a))
    call_args.retries = 0
    hashes = {hashlib.sha256(p.read_bytes()).digest() for p in valid}
    for round_no in range(1, a.max_rounds + 1):
        if not need or not scenes:
            break
        numbers = ([int(Path(n).stem) for n in a.only if not (folder / n).exists()] if a.only
                   else range(next_number(folder), next_number(folder) + need))
        for number in numbers:
            if not need:
                break
            name = f"{number:02d}.png"
            scene = scenes[(number - 1) % len(scenes)]
            ratio = RATIOS[(number - 1) % len(RATIOS)]
            sheet = str(a.reference.resolve())
            prompt = (f'{PROMPT}\n{scene}\noutfit identical to the reference front view\n'
                      f'用 image_edit，image={json.dumps([sheet, sheet])}，aspect_ratio="{ratio}"。'
                      '一次產生一張；必須檢視結果並與參考正面比較，若服裝走樣則重新生成該張，'
                      '回報最終 session 圖片絕對路徑 output_file。'
                      '遇工具拒絕則記錄失敗，不改寫要求繞過限制。')
            def accept(result):
                data = png_bytes(generated_image(result))
                digest = hashlib.sha256(data).digest()
                if digest in hashes:
                    raise ValueError("sha256 duplicate image discarded")
                with (folder / name).open("xb") as handle:
                    handle.write(data)
                hashes.add(digest)
                return str(folder / name)
            # Each round provides one attempt per missing image.
            result, error = retry(prompt, a.out, a.out / "logs", f"{Path(name).stem}_round{round_no}", call_args,
                                  schema=IMAGE_SCHEMA, accept=accept)
            results.append(dict(name=name, round=round_no, ok=result is not None, error=error))
            if result:
                need -= 1
            else:
                last_error = error
    missing = max(0, a.n - len(existing_images(folder)[0]))
    update_missing_json(folder, "keep_outfit", missing, last_error)
    write_json(a.out / "summary.json", dict(results=results, missing=missing, last_error=last_error if missing else None))
    return int(bool(missing))


if __name__ == "__main__":
    raise SystemExit(entry(main))
