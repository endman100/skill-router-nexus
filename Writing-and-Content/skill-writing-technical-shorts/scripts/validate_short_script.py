from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path


DEFAULT_MIN_CHARS = 650
DEFAULT_MAX_CHARS = 1000

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
    (
        re.compile(
            r"(?:不是|並非|并非)[^。！？\n]{0,80}而是"
            r"|不在[於于][^。！？\n]{0,80}而在[於于]"
            r"|不只是[^。！？\n]{0,80}更是"
            r"|不[僅仅][^。！？\n]{0,80}(?:還|还|更)"
            r"|[與与]其[^。！？\n]{0,80}不如"
        ),
        "不可使用「不是 A，而是 B」等二元對比句殼；請直接陳述具體差異。",
    ),
    (
        re.compile(
            r"(?:別急著|别急着)[^。！？\n]{0,60}先"
            r"|(?:先別|先别)[^。！？\n]{0,60}先"
            r"|順序別反了|顺序别反了|別搞反了|别搞反了"
            r"|記住這句話|记住这句话"
        ),
        "不可使用命令式模板開場；請從具體問題、行為或結果起句。",
    ),
    (
        re.compile(
            r"真正|其實|其实|本質上|本质上|核心在於|核心在于"
            r"|關鍵在於|关键在于|說白了|说白了|歸根結底|归根结底"
            r"|更重要的是|結果有點出乎意料|结果有点出乎意料"
            r"|這說明|这说明|這背後|这背后"
        ),
        "不可使用「真正／其實／核心在於」等假洞察提示詞；請直接寫事實或判斷。",
    ),
    (
        re.compile(
            r"(?:我的結論是|我的结论是|原因很簡單|原因很简单|重點是|重点是"
            r"|分成三類|分成三类|更重要的是)[：:]"
        ),
        "不可使用冒號講義腔；請改成普通句子或拆成兩句。",
    ),
    (
        re.compile(
            r"大部分人以為|这根本是在|這根本是在|愣住了|更扯的是|結果呢|结果呢"
            r"|震撼全球|深入探討|深入探讨|想像一下|想象一下"
            r"|對一般使用者來說|对一般使用者来说|懶人包[｜|]?|懒人包[｜|]?|👇"
        ),
        "不可使用模板化或聳動語句；請改寫成可驗證的具體描述。",
    ),
)

VAGUE_LANGUAGE_PATTERNS = (
    (
        re.compile(r"東西|东西|這件事|这件事|這些|这些|一類|一类|幾個方向|几个方向"),
        "發現含糊指稱；請換成確切類別或物件名稱。",
    ),
    (
        re.compile(r"更適合|更适合|更像|更自然|更高級|更高级"),
        "發現含糊比較；請寫明和哪個版本相比、哪個可觀察行為改變。",
    ),
    (
        re.compile(r"(?:這條|这条|這篇|这篇|這個|这个)(?:[，,。！？!?]|$)"),
        "發現可能懸空的指示詞；請補上「影片、論文、工具」等名詞。",
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
    target: int | None = None,
    tolerance: float = 0.1,
    min_chars: int = DEFAULT_MIN_CHARS,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict[str, object]:
    if not 0 <= tolerance <= 1:
        raise ValueError("tolerance 必須介於 0 與 1 之間")
    if target is not None and target <= 0:
        raise ValueError("target 必須大於 0")
    if min_chars <= 0 or max_chars <= 0:
        raise ValueError("min-chars 與 max-chars 必須大於 0")
    if min_chars > max_chars:
        raise ValueError("min-chars 不可大於 max-chars")

    errors: list[str] = []
    warnings: list[str] = []
    count = visible_character_count(text)
    if target is None:
        minimum = min_chars
        maximum = max_chars
    else:
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

    for pattern, message in VAGUE_LANGUAGE_PATTERNS:
        if pattern.search(text):
            warnings.append(message)

    if ENDING_CTA.search(ending_text(text)):
        errors.append("結尾不可加入使用建議或行動呼籲。")

    if re.search(r"^\s*#{1,6}\s", text, re.MULTILINE):
        errors.append("正文不可包含 Markdown 標題。")
    if re.search(r"https?://", text, re.IGNORECASE):
        errors.append("正文不可包含來源網址；請把來源放在正文之外。")

    if not re.search(
        r"相較|相比|相對|上一代|前一代|前代|舊版|旧版|過往|舊方法|舊方案|傳統",
        text,
    ):
        warnings.append("未明確找到前一版本或過往方法的具體差異說明。")
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
    parser.add_argument(
        "--target",
        type=int,
        default=None,
        help="Optional legacy target count; when set, overrides min/max range",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.1,
        help="Allowed fractional deviation from target (default: 0.1)",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=DEFAULT_MIN_CHARS,
        help=f"Minimum non-whitespace count (default: {DEFAULT_MIN_CHARS})",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help=f"Maximum non-whitespace count (default: {DEFAULT_MAX_CHARS})",
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
            min_chars=args.min_chars,
            max_chars=args.max_chars,
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
