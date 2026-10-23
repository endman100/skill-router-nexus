#!/usr/bin/env python3
"""以 Grok Build 逐張打標 NSFW，驗證轉換後複製成功項目；不呼叫 Codex。"""
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path
import jsonschema
from ws import parse_args
from codex_caption_v2 import sha, IMAGE_EXT
from grok_headless import options, retry, report, write_json, entry

HERE = Path(__file__).resolve().parent


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("project-dir", "images", "out", "final-dir", "manifest"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--schema", type=Path, help="本機建立分組 schema 時使用的 base schema")
    p.add_argument("--templates", type=Path, help="本機建立 prompt 時使用的模板資料夾")
    options(p, only=True)
    a = parse_args(p, "grok_caption", argv)
    assignment = a.out / "assignment.json"
    if not assignment.exists():
        command = [sys.executable, "-B", str(HERE / "codex_caption_v2.py"),
                   "--workspace", str(a.project_dir), "--nsfw-schema", "--dry-run",
                   "--images", str(a.images), "--out", str(a.out), "--manifest", str(a.manifest)]
        for flag in ("schema", "templates"):
            if getattr(a, flag):
                command += ["--" + flag, str(getattr(a, flag))]
        subprocess.run(command, check=True)
    jobs = {j["name"]: j for j in json.loads(assignment.read_text("utf-8"))}
    images = [p for p in sorted(a.images.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXT
              and (not a.only or p.name in a.only)]
    if a.dry_run:
        print(json.dumps(dict(images=[p.name for p in images], out=str(a.out),
                              final_dir=str(a.final_dir)), ensure_ascii=False))
        return 0
    results = []
    for src in images:
        rec = dict(name=src.name, ok=False)
        try:
            job = jobs[src.name]
            schema_file = a.out / "schemas" / f"{job['group']}_{job['outfit']}.schema.json"
            schema = json.loads(schema_file.read_text("utf-8"))
            with tempfile.TemporaryDirectory(prefix="grok-caption-") as temporary:
                work = Path(temporary)
                # Preserve generated prompt's relative paths, and supply absolute paths too.
                (work / "input/images").mkdir(parents=True)
                (work / "output").mkdir()
                attached = work / "input/images" / src.name
                shutil.copy2(src, attached)
                shutil.copy2(schema_file, work / "input/schema.json")
                prompt = ((a.out / "prompts" / f"{src.stem}.txt").read_text("utf-8") +
                          f"\n請使用 read_file 檢視圖片：{attached}。以指定 schema 回傳 structuredOutput。")
                def accept(result):
                    data = result["structured"]
                    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(data))
                    if errors:
                        raise ValueError("; ".join(e.message for e in errors))
                    data = {k: data[k] for k in schema["properties"]}
                    write_json(a.out / "json" / f"{src.stem}.json", data)
                    return data
                result, error = retry(prompt, work, a.out / "logs", src.stem, a,
                                      schema=schema, accept=accept)
                rec.update(ok=result is not None, error=error)
        except (OSError, ValueError, KeyError) as exc:
            rec["error"] = str(exc)
        if not rec["ok"]:
            (a.out / "json" / f"{src.stem}.json").unlink(missing_ok=True)
            (a.out / "txt" / f"{src.stem}.txt").unlink(missing_ok=True)
        results.append(rec)
    successful = [r["name"] for r in results if r["ok"]]
    converted = None
    if successful:
        converted = subprocess.run([sys.executable, "-B", str(HERE / "caption_convert.py"),
                                    "--workspace", str(a.project_dir), str(a.out / "json"), str(a.out / "txt"),
                                    "--validate-with", str(a.out), "--only", *successful],
                                   capture_output=True, text=True)
        (a.out / "convert.stdout.txt").write_text(converted.stdout, "utf-8")
        (a.out / "convert.stderr.txt").write_text(converted.stderr, "utf-8")
    a.final_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.manifest, a.final_dir / "manifest.json")
    for rec in results:
        src = a.images / rec["name"]
        txt = a.out / "txt" / f"{src.stem}.txt"
        if rec["ok"]:
            try:
                if converted.returncode or not txt.is_file():
                    raise ValueError("caption_convert failed: " + converted.stderr)
                dst = a.final_dir / src.name
                shutil.copy2(src, dst)
                shutil.copy2(txt, a.final_dir / txt.name)
                if sha(src) != sha(dst) or sha(txt) != sha(a.final_dir / txt.name):
                    raise ValueError("sha256 mismatch")
            except (OSError, ValueError, KeyError) as exc:
                rec.update(ok=False, error=str(exc))
        if not rec["ok"]:
            (a.final_dir / src.name).unlink(missing_ok=True)
            (a.final_dir / txt.name).unlink(missing_ok=True)
    return report(a.out, results)


if __name__ == "__main__":
    raise SystemExit(entry(main))
