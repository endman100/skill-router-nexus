#!/usr/bin/env python3
"""備援：Codex 沒有交出可用詞表時，以 Grok Build 檢視拼圖與原圖、從零建立詞表，驗證後等待使用者確認。

主路徑見 05_captioning.md a 節：Codex 先寫 vocab.json，Grok 只改錯誤 trait。本腳本會覆寫 vocab.json，
Codex 草稿可用時不要執行。

隔離與最小權限（grok_headless.PROFILES["read"]）：拼圖、原圖、詞表規則、params、vocab.schema.json
先複製到 <out>/.grok_vocab_*/（每次新建），Grok 以該資料夾為 cwd，只有 read_file/list_dir、
dontAsk、沙箱 lora_min（strict + 拒讀 /tmp、/var/tmp，只能讀 cwd + 系統路徑 + ~/.grok），
無 shell、無寫檔、無網路、無子代理。Grok 不再改檔：清單外的配件以 structuredOutput 的
outfit_accessory_tags_add 回報，由腳本把原 params 備份成 caption_vocab_params.prev_<時間>.json 後寫回。
"""
import argparse, json, shutil, time
from pathlib import Path
from ws import parse_args
import vocab_tools
from grok_headless import options, retry, report, write_json, entry, isolated_cwd, SANDBOX

ISOLATION = ("Only read files inside the current working directory (the isolated input folder given in the prompt). "
             "Never read, list or search any other path (no parent folders, no /workspace, no home folders, "
             "no older vocab files). Do not run scripts.")
MAX_TURNS = 80      # one read_file per sheet/original plus the answer


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


def wrap_schema(schema):
    """vocab schema + the accessory tags Grok wants added (replaces editing the params file)."""
    inner = {k: v for k, v in schema.items() if k != "$schema"}
    tag = inner["properties"]["outfits"]["items"]["properties"]["tags"]["items"]["properties"]["tag"]
    return {"$schema": schema.get("$schema", "https://json-schema.org/draft/2020-12/schema"),
            "type": "object", "additionalProperties": False,
            "required": ["vocab", "outfit_accessory_tags_add"],
            "properties": {"vocab": inner,
                           "outfit_accessory_tags_add": {"type": "array", "uniqueItems": True, "items": tag}}}


def sync_params(add, target):
    """Append Grok's new accessory tags to outfit_accessory_tags; back up the target first."""
    data = json.loads(target.read_text("utf-8"))
    current = data["outfit_accessory_tags"]
    new = [t for t in dict.fromkeys(add) if t not in current]
    if not new:
        return None, []
    backup = target.with_name(f"{target.stem}.prev_{time.strftime('%Y%m%d_%H%M%S')}.json")
    shutil.copy2(target, backup)
    data["outfit_accessory_tags"] = current + new
    target.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8")
    return backup, new


def build_prompt(rules, params_data, sheets, originals):
    notes = params_data.get("trait_notes", {})
    fixed = vocab_tools.fixed_traits(params_data)
    lines = [
        "這次是備援撰寫（Codex 沒有可用草稿）。請依 vocab_rules.md（下列 a 節）直接建立整份 vocab，"
        "以指定 schema 回傳。不要等 Codex，不要只列修正。只做詞表，不做後續打標。",
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
    lines.append("可讀取 ./caption_vocab_params.json 的 trait 對應與配件清單（outfit_accessory_tags）。"
                 "不要修改任何檔案（也沒有寫檔工具）：structuredOutput.vocab 填詞表（依 vocab.schema.json）；"
                 "角色有清單外的配件 tag 時，列在 structuredOutput.outfit_accessory_tags_add（沒有就給空清單），由腳本寫回。")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("project-dir", "images", "manifest", "out", "params"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--main-outfit")
    p.add_argument("--auto", action="store_true")
    p.add_argument("--sandbox", default=SANDBOX,
                   help=f"Grok Build sandbox profile（預設 {SANDBOX}；strict 較寬鬆，可讀 /tmp；off 為不限制，不建議）")
    options(p)
    a = parse_args(p, "grok_vocab", argv)
    if a.dry_run:
        params_data = json.loads(a.params.read_text("utf-8"))
        print(f"sheets -> {a.out}; inputs copied to {a.out}/.grok_vocab_*/ (cwd, profile=read, --sandbox {a.sandbox}); "
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
    with isolated_cwd(a.out, "vocab") as work:
        w_sheets, w_originals, _ = stage_inputs(work, sheets, originals, a.params,
                                                       a.out / "vocab.schema.json", rules)
        prompt = build_prompt(rules, json.loads(a.params.read_text("utf-8")), w_sheets, w_originals)

        def accept(result):
            viewed = set(result["viewed_images"])
            if not set(w_originals) & viewed:
                raise ValueError("chat_history.jsonl has no original image view")
            if not set(w_sheets) <= viewed:
                raise ValueError("Not every contact sheet was viewed")
            write_json(a.out / "vocab.json", result["structured"]["vocab"])
            return result
        result, error = retry(prompt, work, a.out / "logs", "vocab", a, schema=wrap_schema(schema), accept=accept,
                              profile="read", max_turns=MAX_TURNS,
                              sandbox=None if a.sandbox == "off" else a.sandbox, rules=ISOLATION)
        if result:
            backup, added = sync_params(result["structured"]["outfit_accessory_tags_add"], a.params)
            if backup:
                print(f"已把配件 {added} 加入 {a.params}（原檔備份 {backup.name}）")
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
            print("暫停：請使用者確認每張必填特徵（身高、體型、年齡）、臉型與其他特徵、主要服裝及各服裝分組與圖數。"
                  "每個服裝 tag 與角色特徵都要帶出現率 tag (k/n, p%) 與繁體中文翻譯；摘要中的 (?/n) 須先點算、寫回 count 並重跑 check。"
                  "主要服裝不要留下低於半數的少數 tag，除非使用者明確要求。確認後才進入 b. 打標。")
    return status


if __name__ == "__main__":
    raise SystemExit(entry(main))
