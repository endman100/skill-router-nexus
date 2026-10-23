#!/usr/bin/env python3
"""以 Grok Build 收集角色圖片與來源網址。"""
import argparse, tempfile
from pathlib import Path
from ws import parse_args
from codex_collect import make_prompt, copy_results, result_files
from grok_headless import options, retry, report, entry


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--query", required=True)
    p.add_argument("--out", type=Path, required=True)
    options(p)
    a = parse_args(p, "grok_collect", argv)
    if a.out.exists() and any(f.name not in {"logs", "summary.json", "failed.json"} for f in a.out.iterdir()):
        raise ValueError(f"Destination is not empty: {a.out}")
    if a.dry_run:
        print(f"{make_prompt(a.query)}\nweb=True; destination={a.out}; retries={a.retries}")
        return 0
    with tempfile.TemporaryDirectory(prefix="grok-collect-") as temporary:
        work = Path(temporary)
        def accept(result):
            images, _, manifest = result_files(work)
            if not images and manifest is None:
                raise ValueError("Nothing produced (no images or sources.json)")
            return result
        result, error = retry(make_prompt(a.query), work, a.out / "logs", "collect", a,
                              web=True, accept=accept)
        rec = dict(name="collect", ok=result is not None, error=error)
        if result:
            rec.update(copy_results(work, a.out))
            rec["ok"] = rec["produced"] and not rec["error"]
    return report(a.out, [rec])


if __name__ == "__main__":
    raise SystemExit(entry(main))
