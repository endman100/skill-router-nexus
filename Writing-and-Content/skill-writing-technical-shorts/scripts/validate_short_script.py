from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path


FORBIDDEN_PATTERNS = (
    (re.compile(r"benchmark", re.IGNORECASE), "不可直接寫出 benchmark 名稱或成績。"),
    (
        re.compile(r"Apache[^。！？\n]{0,24}(?:授權|license)", re.IGNORECASE),
        "不可介紹 Apache 授權條款。",
    ),
    (
        re.compile(r"本地部署|本機部署|部署框架|操作指令"),
        "不可說明本地部署、部署框架或操作指令。",
    ),
    (
        re.compile(r"顯示卡記憶體|GPU\s*記憶體|顯存", re.IGNORECASE),
        "標準技術用詞請寫 VRAM，不要寫顯示卡記憶體、GPU 記憶體或顯存。",
    ),
)

ENDING_CTA = re.compile(
    r"立即|歡迎|前往|點擊|訂閱|追蹤|試用|使用這個功能|建議你|如果你想"
)


def visible_character_count(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def first_nonempty_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def ending_text(text: str, sentence_count: int = 2) -> str:
    compact = re.sub(r"\s+", "", text)
    sentences = [part for part in re.split(r"(?<=[。！？])", compact) if part]
    return "".join(sentences[-sentence_count:])


def validate(
    text: str,
    *,
    topic: str,
    target: int = 720,
    tolerance: float = 0.1,
) -> dict[str, object]:
    if target <= 0:
        raise ValueError("target 必須大於 0")
    if not 0 <= tolerance <= 1:
        raise ValueError("tolerance 必須介於 0 與 1 之間")

    errors: list[str] = []
    warnings: list[str] = []
    count = visible_character_count(text)
    decimal_target = Decimal(target)
    decimal_tolerance = Decimal(str(tolerance))
    minimum = int(
        (decimal_target * (Decimal(1) - decimal_tolerance)).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    maximum = int(
        (decimal_target * (Decimal(1) + decimal_tolerance)).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    expected_first_line = f"什麼是 {topic}？"
    actual_first_line = first_nonempty_line(text)

    if actual_first_line != expected_first_line:
        errors.append(f"第一個非空白行必須完全等於：{expected_first_line}")

    if not minimum <= count <= maximum:
        errors.append(
            f"字數為 {count} 個非空白字，應介於 {minimum} 到 {maximum} 之間。"
        )

    for pattern, message in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            errors.append(message)

    if ENDING_CTA.search(ending_text(text)):
        errors.append("結尾不可加入使用建議或行動呼籲。")

    if re.search(r"^\s*#{1,6}\s", text, re.MULTILINE):
        errors.append("正文不可包含 Markdown 標題。")
    if re.search(r"https?://", text, re.IGNORECASE):
        errors.append("正文不可包含來源網址；請把來源放在正文之外。")

    if not re.search(r"相較|相比|相對|前代|過往|舊方法|舊方案|傳統", text):
        warnings.append("未明確找到與前代或過往方案的差異說明。")
    if not re.search(r"限制|取捨|代價|上限|仍非|仍會|不過", text):
        warnings.append("未明確找到限制或取捨說明。")

    return {
        "valid": not errors,
        "characters_excluding_whitespace": count,
        "allowed_range": [minimum, maximum],
        "first_line": actual_first_line,
        "errors": errors,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a Traditional Chinese technical Short script."
    )
    parser.add_argument("file", type=Path, help="UTF-8 text or Markdown script file")
    parser.add_argument("--topic", required=True, help="Topic used in the exact first line")
    parser.add_argument("--target", type=int, default=720, help="Target non-whitespace count")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.1,
        help="Allowed fractional deviation from target (default: 0.1)",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        text = args.file.read_text(encoding="utf-8")
        result = validate(
            text,
            topic=args.topic,
            target=args.target,
            tolerance=args.tolerance,
        )
    except (OSError, UnicodeError, ValueError) as error:
        result = {
            "valid": False,
            "characters_excluding_whitespace": 0,
            "allowed_range": [],
            "first_line": "",
            "errors": [str(error)],
            "warnings": [],
        }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if result["valid"] else "FAIL"
        print(f"[{status}] {args.file}")
        print(
            "Characters excluding whitespace: "
            f"{result['characters_excluding_whitespace']} "
            f"(allowed: {result['allowed_range']})"
        )
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")

    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
