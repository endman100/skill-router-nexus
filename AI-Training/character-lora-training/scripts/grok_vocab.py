#!/usr/bin/env python3
"""以 Grok Build 檢視拼圖與原圖、建立詞表，驗證後等待使用者確認。"""
import argparse, json
from pathlib import Path
from ws import parse_args
import vocab_tools
from grok_headless import options, retry, report, write_json, entry


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("project-dir", "images", "manifest", "out", "params"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--main-outfit")
    p.add_argument("--auto", action="store_true")
    options(p)
    a = parse_args(p, "grok_vocab", argv)
    if a.dry_run:
        print(f"sheets -> {a.out}; Grok views every sheet + original; check; auto={a.auto}")
        return 0
    ws_args = ["--workspace", str(a.project_dir)]
    status = vocab_tools.main(["sheets", *ws_args, "--images", str(a.images),
                               "--manifest", str(a.manifest), "--out", str(a.out)])
    if status:
        return status
    manifest = json.loads(a.manifest.read_text("utf-8"))
    names = set(json.loads((a.out / "names.json").read_text("utf-8")))
    originals = [(Path(manifest["nsfw_dir"]) if e.get("nsfw") else a.images) / e["filename"]
                 for e in manifest["images"] if e["filename"] in names]
    originals = [p.resolve() for p in originals]
    sheets = sorted(p.resolve() for p in (a.out / "contact_sheets").glob("sheet_*.jpg"))
    rules = (Path(__file__).resolve().parent.parent / "05_captioning.md").read_text("utf-8")
    rules = rules.split("## a.", 1)[1].split("## b.", 1)[0]
    prompt = (f"請依下列 a 節的詞表規則建立 vocab，以指定 schema 回傳。只做詞表，不做後續打標。\n{rules}\n"
              f"使用 read_file 檢視每一張拼圖：{json.dumps([str(p) for p in sheets])}\n"
              f"至少使用 read_file 開啟一張原圖：{json.dumps([str(p) for p in originals])}\n"
              f"可讀取 {a.params.resolve()} 的 trait 對應與配件清單，必要時更新配件清單。"
              "回傳 structuredOutput 作為 vocab.json，不自行執行其他腳本。")
    def accept(result):
        viewed = set(result["viewed_images"])
        if not set(originals) & viewed:
            raise ValueError("chat_history.jsonl has no original image view")
        if not set(sheets) <= viewed:
            raise ValueError("Not every contact sheet was viewed")
        write_json(a.out / "vocab.json", result["structured"])
        return result
    result, error = retry(prompt, a.out, a.out / "logs", "vocab", a,
                          schema=json.loads((a.out / "vocab.schema.json").read_text("utf-8")), accept=accept)
    status = 1
    if result:
        check = ["check", *ws_args, "--vocab", str(a.out / "vocab.json"), "--names", str(a.out / "names.json"),
                 "--params", str(a.params)]
        if a.main_outfit:
            check += ["--main-outfit", a.main_outfit]
        status = vocab_tools.main(check)
        if status:
            error = "vocab_tools check failed"
    report(a.out, [dict(name="vocab", ok=not status, error=error)])
    if not status:
        print((a.out / "vocab_summary.md").read_text("utf-8"))
        main = a.out / "main_outfit.json"
        if main.exists():
            print(main.read_text("utf-8"))
        if not a.auto:
            print("暫停：請使用者確認固定特徵、主要服裝及各服裝分組與圖數，確認後才進入 b. 打標。")
    return status


if __name__ == "__main__":
    raise SystemExit(entry(main))
