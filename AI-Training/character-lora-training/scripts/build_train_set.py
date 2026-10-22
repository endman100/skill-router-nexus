#!/usr/bin/env python3
"""整理訓練集：把已調整尺寸（resize_prep.py + 放大結果併回）的各組圖依序編號成 0001.png…，寫 manifest.json。
編號前自動核對來源旁 resize_manifest.json 的 needs_upscale 項目：同名圖已併回、可讀且長邊達標才繼續。

NSFW 隔離在這一步完成（Codex 打標程式不再檢查 NSFW）：
  - 一般群組（group=dir）→ <訓練資料夾>/，這個資料夾整個交給 codex_caption_v2.py（Codex）。
  - NSFW 群組（group:nsfw=dir，例如 02 清理時 WD Tagger 分到 nsfw/、由 Grok 處理的收集圖）→ --nsfw-out
    （預設 <訓練資料夾>_nsfw/），由 Grok 打標，永遠不會出現在 Codex 的輸入資料夾。
  - 防呆：同一個來源資料夾不可同時當一般群組與 NSFW 群組；一般群組的圖若與 NSFW 群組的圖 sha256 相同，直接停止。
編號跨兩個資料夾連續；manifest.json（在 <訓練資料夾>/）列出全部圖，nsfw=true 的圖在 manifest 的 nsfw_dir。
codex_caption_v2.py 依 manifest 的 source_group 決定模板。

用法：
  python3 build_train_set.py <訓練資料夾> --character "<角色名> (<作品名>)" --trigger <trigger> \
      collected=<dir> gen_codex_keep=<dir> gen_grok_keep=<dir> gen_codex_change=<dir> [collected:nsfw=<dir>] \
      [--nsfw-out <dir>]
  群組名必須與 caption_vocab_params.json 的 collected_group / keep_outfit_groups / change_outfit_groups 一致。
"""
import argparse, hashlib, json, math, shutil, sys
from collections import Counter
from pathlib import Path
from ws import parse_args
from PIL import Image

EXT = {".png", ".jpg", ".jpeg", ".webp"}


def parse_spec(spec):
    key, d = spec.split("=", 1)
    group, _, flag = key.partition(":")
    if flag not in ("", "nsfw"):
        sys.exit(f"未知旗標 {flag!r}（只接受 群組:nsfw=dir）")
    return group, flag == "nsfw", Path(d)


def list_images(d):
    return [f for f in sorted(d.iterdir()) if f.is_file() and f.suffix.lower() in EXT]


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_upscales(specs):
    """編號前核對 resize manifest：每張待放大圖都必須可讀且已併回來源群組。"""
    dirs = {d.resolve() for _, _, d in specs}
    manifests = sorted({d.parent / "resize_manifest.json" for d in dirs})
    failed = []
    for manifest in manifests:
        if not manifest.is_file():
            continue
        for entry in json.loads(manifest.read_text("utf-8")):
            if entry["action"] != "needs_upscale":
                continue
            folder = manifest.parent / entry["group"]
            dest = folder / Path(entry["output"]).name
            if folder not in dirs:
                failed.append(f"{dest}: 群組未傳入，無法進入後續流程")
                continue
            try:
                with Image.open(dest) as im:
                    im.load()
                    target = max(768, entry.get("target_long", 768))
                    if max(im.size) < target:
                        failed.append(f"{dest}: 長邊 {max(im.size)} < {target}")
            except Exception as e:
                failed.append(f"{dest}: 缺少或無法讀取圖片（{type(e).__name__}: {e}）")
    if failed:
        sys.exit("放大檢查失敗，停止編號：\n" + "\n".join(failed))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out", type=Path)
    p.add_argument("groups", nargs="+", help="group=dir 或 group:nsfw=dir，依此順序編號")
    p.add_argument("--character", required=True)
    p.add_argument("--trigger", required=True)
    p.add_argument("--nsfw-out", type=Path, help="NSFW 圖的資料夾（預設 <訓練資料夾>_nsfw）")
    p.add_argument("--repeat-target", type=int, default=480, help="num_repeats 建議值 = ceil(target / 圖數)")
    a = parse_args(p, "build", argv)
    specs = [parse_spec(s) for s in a.groups]
    check_upscales(specs)
    out = a.out.resolve()
    nsfw_out = (a.nsfw_out or a.out.parent / f"{a.out.name}_nsfw").resolve()
    if nsfw_out == out or out in nsfw_out.parents or nsfw_out in out.parents:
        sys.exit(f"--nsfw-out {nsfw_out} 不可與 {out} 相同或互相包含")
    # 防呆：一般群組與 NSFW 群組不可共用來源資料夾或相同圖片
    sfw_dirs = {d.resolve() for _, n, d in specs if not n}
    nsfw_dirs = {d.resolve() for _, n, d in specs if n}
    if sfw_dirs & nsfw_dirs:
        sys.exit(f"同一資料夾同時被當一般群組與 NSFW 群組：{sorted(map(str, sfw_dirs & nsfw_dirs))}")
    nsfw_sha = {sha256(f): f for _, n, d in specs if n for f in list_images(d)}
    clash = [(str(f), str(nsfw_sha[h])) for _, n, d in specs if not n for f in list_images(d)
             if (h := sha256(f)) in nsfw_sha]
    if clash:
        sys.exit(f"一般群組含有 NSFW 群組的圖（sha256 相同），停止：{clash}")
    for d in (out, nsfw_out) if nsfw_dirs else (out,):
        if d.exists() and any(d.iterdir()):
            sys.exit(f"{d} 不是空資料夾")
        d.mkdir(parents=True, exist_ok=True)
    images, n = [], 0
    for group, is_nsfw, d in specs:
        for f in list_images(d):
            n += 1
            name = f"{n:04d}.png"
            dst = (nsfw_out if is_nsfw else out) / name
            if f.suffix.lower() == ".png":
                shutil.copy2(f, dst)
            else:
                Image.open(f).convert("RGB").save(dst)
            with Image.open(dst) as im:
                dims = list(im.size)
            images.append(dict(filename=name, sha256=sha256(dst), dims=dims,
                               source_group=group, source_file=str(f.resolve()), nsfw=is_nsfw))
    manifest = dict(character=a.character, trigger=a.trigger, count=n,
                    num_repeats_suggested=math.ceil(a.repeat_target / max(n, 1)),
                    nsfw_dir=str(nsfw_out) if nsfw_dirs else None, images=images)
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    print(n, dict(Counter((i["source_group"], i["nsfw"]) for i in images)))
    print(f"Codex 打標資料夾（只有 SFW）：{out}")
    if nsfw_dirs:
        print(f"NSFW（Grok 打標，不給 Codex）：{nsfw_out}")


if __name__ == "__main__":
    sys.exit(main())
