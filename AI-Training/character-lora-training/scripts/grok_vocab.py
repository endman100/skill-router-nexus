#!/usr/bin/env python3
"""以 Grok Build 檢視拼圖與原圖、建立詞表，驗證後等待使用者確認。

隔離：拼圖、原圖、詞表規則、params、vocab.schema.json 先複製到 <out>/.grok_vocab_*/（每次新建），
Grok 以該資料夾為 cwd、預設 `--sandbox strict`（kernel 限制只能讀 cwd + 系統路徑 + ~/.grok），
prompt 也明令只能讀該資料夾內的檔案，避免讀到 /workspace 其他舊詞表。Grok 若更新了配件清單，
先把原 params 備份成 caption_vocab_params.prev_<時間>.json，再寫回 --params。結束後移除這個暫存複本。
"""
import argparse, json, shutil, tempfile, time
from pathlib import Path
from ws import parse_args
import vocab_tools
from grok_headless import options, retry, report, write_json, entry

ISOLATION = ("Only read files inside the current working directory (the isolated input folder given in the prompt). "
             "Never read, list or search any other path (no parent folders, no /workspace, no home folders, "
             "no older vocab files). Do not run scripts.")


def stage_inputs(work, sheets, originals, params, schema, rules):
    """Copy every input Grok may read into the isolated folder; returns (sheets, originals, params) copies."""
    (work / "contact_sheets").mkdir(parents=True)
    (work / "originals").mkdir()
    s = [shutil.copy2(p, work / "contact_sheets" / p.name) for p in sheets]
    o = [shutil.copy2(p, work / "originals" / p.name) for p in originals]
    prm = Path(shutil.copy2(params, work / "caption_vocab_params.json"))
    shutil.copy2(schema, work / "vocab.schema.json")
    (work / "vocab_rules.md").write_text(rules, "utf-8")
    return [Path(p).resolve() for p in s], [Path(p).resolve() for p in o], prm


def sync_params(staged, target):
    """Grok may extend outfit_accessory_tags in its copy; back up the target, then write it back."""
    new = staged.read_text("utf-8")
    if new == target.read_text("utf-8"):
        return None
    data = json.loads(new)                                        # must stay valid JSON with the same keys
    if set(data) != set(json.loads(target.read_text("utf-8"))):
        raise ValueError("Grok changed caption_vocab_params.json keys; not written back")
    backup = target.with_name(f"{target.stem}.prev_{time.strftime('%Y%m%d_%H%M%S')}.json")
    shutil.copy2(target, backup)
    target.write_text(new, "utf-8")
    return backup


def build_prompt(rules, params_data, sheets, originals):
    notes = params_data.get("trait_notes", {})
    fixed = vocab_tools.fixed_traits(params_data)
    lines = [
        "請依 vocab_rules.md（下列 a 節）的詞表規則建立 vocab，以指定 schema 回傳。只做詞表，不做後續打標。",
        rules,
        f"隔離規則：{ISOLATION} 所有輸入都已複製到目前工作資料夾：vocab_rules.md、caption_vocab_params.json、"
        "vocab.schema.json、contact_sheets/、originals/。",
        f"使用 read_file 檢視每一張拼圖：{json.dumps([str(p) for p in sheets])}",
        f"至少使用 read_file 開啟一張原圖（建議主要服裝、正面且臉部清楚），看清臉型、髮型、瀏海、眼睛與配件："
        f"{json.dumps([str(p) for p in originals])}",
        f"每張必填的 trait（fixed_traits，一定要寫進 character_features）：{', '.join(fixed) or '-'}。",
    ]
    for trait, note in notes.items():
        lines.append(f"trait `{trait}` 必須填寫（看過原圖後判斷）：{note}")
    lines.append("可讀取 ./caption_vocab_params.json 的 trait 對應與配件清單；角色有清單外的配件時，"
                 "只修改該檔的 outfit_accessory_tags（其他鍵不要動）。回傳 structuredOutput 作為 vocab.json，不自行執行其他腳本。")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("project-dir", "images", "manifest", "out", "params"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--main-outfit")
    p.add_argument("--auto", action="store_true")
    p.add_argument("--sandbox", default="strict", help="Grok Build sandbox profile（off 為不限制，不建議）")
    options(p)
    a = parse_args(p, "grok_vocab", argv)
    if a.dry_run:
        params_data = json.loads(a.params.read_text("utf-8"))
        print(f"sheets -> {a.out}; inputs copied to {a.out}/.grok_vocab_*/ (cwd, --sandbox {a.sandbox}); "
              f"Grok views every sheet + >=1 original; fixed_traits={vocab_tools.fixed_traits(params_data)}; "
              f"trait_notes={list(params_data.get('trait_notes', {}))}; check; auto={a.auto}")
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
    schema = json.loads((a.out / "vocab.schema.json").read_text("utf-8"))
    with tempfile.TemporaryDirectory(prefix=".grok_vocab_", dir=a.out) as temporary:
        work = Path(temporary).resolve()
        w_sheets, w_originals, w_params = stage_inputs(work, sheets, originals, a.params,
                                                       a.out / "vocab.schema.json", rules)
        prompt = build_prompt(rules, json.loads(a.params.read_text("utf-8")), w_sheets, w_originals)

        def accept(result):
            viewed = set(result["viewed_images"])
            if not set(w_originals) & viewed:
                raise ValueError("chat_history.jsonl has no original image view")
            if not set(w_sheets) <= viewed:
                raise ValueError("Not every contact sheet was viewed")
            write_json(a.out / "vocab.json", result["structured"])
            return result
        result, error = retry(prompt, work, a.out / "logs", "vocab", a, schema=schema, accept=accept,
                              sandbox=None if a.sandbox == "off" else a.sandbox, rules=ISOLATION)
        if result:
            backup = sync_params(w_params, a.params)
            if backup:
                print(f"Grok 更新了 {a.params}（原檔備份 {backup.name}）")
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
            print("暫停：請使用者確認每張必填特徵（身高、體型、年齡）、臉型與其他特徵、主要服裝及各服裝分組與圖數，確認後才進入 b. 打標。")
    return status


if __name__ == "__main__":
    raise SystemExit(entry(main))
