#!/usr/bin/env python3
"""從去重、分流後的 SFW 圖片生成角色設定圖，預設等待使用者確認。"""
import argparse
import json
from pathlib import Path
import shutil
import sys

from codex_clean import IMAGE_EXTENSIONS
from codex_isolated import run_isolated
from ws import parse_args

DEFAULT_SHEET_SKILL = Path(__file__).resolve().parent.parent / "../../Image-Generation/character-sheet"
INSTRUCTIONS = "依複製的 character-sheet 技能，以 SFW 參考圖生成角色設定圖。僅在工作目錄內寫入，不得存取網路。"
PROMPT = """請用圖片檢視工具瀏覽 ./input/images/ 的全部 SFW 圖片，
挑選 4 張目標角色主要服裝的代表圖，作為本次生成的原始參考圖。
依照 ./input/character-sheet/SKILL.md 及其參照文件生成角色設定圖，
採用預設 unmeasured 5×3 版面，服裝維持參考圖原樣。
將選用參考圖的 input/images/ 相對路徑清單寫入 ./output/chosen-inputs.json（JSON 陣列）。
生成圖片位於 {CODEX_HOME}/generated_images，最終設定圖寫入 ./output/character-sheet.png。
僅在工作目錄內寫入（含暫存檔），不得存取網路。
"""


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", nargs="+", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--log-dir", type=Path)
    p.add_argument("--sheet-skill", type=Path, default=DEFAULT_SHEET_SKILL)
    p.add_argument("--model", default="gpt-6.1-sol")
    p.add_argument("--effort", default="high")
    p.add_argument("--timeout", type=float, default=3600)
    p.add_argument("--codex", default="codex")
    p.add_argument("--auto", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = parse_args(p, "sheet", argv)
    a.log_dir = a.log_dir or a.out.parent / "codex_sheet"
    if a.out.is_file() and not a.dry_run:
        print(f"已有角色設定圖，跳過生成：{a.out}")
        return 0
    paths = []
    for path in a.inputs:
        paths.extend(sorted(f for f in path.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS)
                     if path.is_dir() else [path])
    inputs = [(path.resolve(), "images/" + path.name) for path in paths]
    inputs.append((a.sheet_skill.resolve(), "character-sheet"))
    if a.dry_run:
        print(json.dumps(dict(inputs=[[str(s), n] for s, n in inputs], out=str(a.out),
                              log_dir=str(a.log_dir), model=a.model, effort=a.effort, timeout=a.timeout,
                              auto=a.auto, skip=a.out.is_file(), prompt=PROMPT), ensure_ascii=False))
        return 0
    root, work, status, _ = run_isolated(
        PROMPT, INSTRUCTIONS, inputs, model=a.model, effort=a.effort, timeout=a.timeout,
        image_generation=True, log_dir=a.log_dir, label="sheet", codex=a.codex)
    try:
        if status:
            return status
        a.out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(work / "output/character-sheet.png", a.out)
        shutil.copyfile(work / "output/chosen-inputs.json", a.log_dir / "chosen-inputs.json")
    finally:
        shutil.rmtree(root)
    print(a.out)
    if not a.auto:
        print("請暫停，等待使用者確認角色設定圖（或替換此圖）後，再執行清理。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
