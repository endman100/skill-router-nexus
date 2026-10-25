#!/usr/bin/env python3
"""以 Grok Build 維持服裝生成 N 張。先寫齊全部案例，再逐張生圖。

scenes.json 為案例計畫（穩定 id／檔名）。重跑與 --only 沿用該檔，只補缺少或損壞的 PNG。
場景設計用 grok_headless.PROFILES["read"]（隔離 cwd，只回 structuredOutput）；
每張圖用 PROFILES["image"]：參考圖複製到 <out>/.grok_gen_*/，Grok 只有 read_file + image_edit。
"""
import argparse
import json
import shutil
from pathlib import Path

from ws import parse_args
from codex_batch_image_gen import (
    KEEP, TEXT_FIELDS, assign_cases, grok_image_prompt, positive_int, run_case_generation,
)
from grok_headless import IMAGE_SCHEMA, entry, generated_image, isolated_cwd, options, png_bytes, retry, write_json


def design_cases(args, n):
    schema = {
        "type": "object", "additionalProperties": False, "required": ["scenes"],
        "properties": {"scenes": {
            "type": "array", "minItems": n, "maxItems": n,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": list(TEXT_FIELDS),
                "properties": {field: {"type": "string"} for field in TEXT_FIELDS},
            },
        }},
    }
    prompt = (
        f"請設計 {n} 個互不相同的 SFW 角色圖案例，順序對應 keep_01 到 keep_{n:02d}。"
        "每個案例包含具體的背景、姿勢、動作、表情、鏡頭。"
        "背景為乾淨、具真實場景感的動畫美術背景，同一批不可重複，姿勢、動作與表情的組合也不可重複。"
        "服裝維持參考圖，不要描述換裝。回傳一個物件，scenes 為案例陣列，不要寫禁止事項。"
    )

    def accept(result):
        return assign_cases(n, result["structured"], groups=(KEEP,))

    with isolated_cwd(args.out, "scenes") as work:
        plan, error = retry(prompt, work, args.out / "logs", "scenes", args, schema=schema,
                            profile="read", max_turns=5, accept=accept)
    if plan is None:
        raise RuntimeError(error or "scene planning failed")
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("n", type=positive_int, nargs="?", default=30)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scenes", "--cases", type=Path, dest="scenes",
                        help="案例計畫 JSON，預設 <out>/scenes.json")
    parser.add_argument("--max-rounds", type=positive_int, default=3)
    parser.add_argument("--design-only", action="store_true", help="寫入 scenes.json 後停止，不生圖")
    options(parser, only=True)
    args = parse_args(parser, "grok_generate", argv)
    folder = args.out / "keep_outfit"
    attempts_per_case = {}

    def designer(reference, n):
        del reference
        return design_cases(args, n)

    def generator(reference, case, dest):
        del dest
        attempts_per_case[case["id"]] = attempts_per_case.get(case["id"], 0) + 1
        found = {}

        def accept(result):
            found["data"] = png_bytes(generated_image(result))
            return found["data"]

        call_args = argparse.Namespace(**vars(args))
        call_args.retries = 0
        with isolated_cwd(args.out, "gen") as work:
            staged = work / ("reference" + Path(reference).suffix.lower())
            shutil.copy2(reference, staged)
            result, error = retry(
                grok_image_prompt(case).replace("{reference}", str(staged)), work, args.out / "logs",
                f"{case['id']}_round{attempts_per_case[case['id']]}", call_args,
                schema=IMAGE_SCHEMA, accept=accept, profile="image", max_turns=20)
        if "data" not in found:
            raise RuntimeError(error or "no image")
        return found["data"]

    result = run_case_generation(
        n=args.n, cases_file=args.scenes or (args.out / "scenes.json"),
        plan_groups=(KEEP,), generate_groups=(KEEP,),
        output_for=lambda case: folder / case["filename"], reference=args.reference,
        designer=designer, generator=generator, dry_run=args.dry_run,
        design_only=args.design_only, only=args.only, max_rounds=args.max_rounds)
    print(json.dumps(result["report"], ensure_ascii=False))
    if not args.dry_run and not args.design_only:
        remaining = set(result["report"]["remaining"])
        last_error = None
        if result["exit_code"]:
            for item in reversed(result["attempts"]):
                if item["error"] and item["id"] in remaining:
                    last_error = item["error"]
                    break
            last_error = last_error or f"{len(remaining)} planned image(s) still missing"
        write_json(args.out / "summary.json", {
            "results": result["attempts"], "missing": result["missing"], "last_error": last_error,
        })
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(entry(main))
