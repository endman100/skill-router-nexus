#!/usr/bin/env python3
"""
Threads Post Writer — JSON 驗證工具

用法：
    python validate.py <json_file_path>

輸出：
    - 驗證失敗：印出所有錯誤，exit code 1
    - 驗證成功：印出「驗證成功：共 N 段」，exit code 0

JSON 格式規範：
    頂層為 list，每個元素為一個段落（list of str）。
    範例：
    [
      ["第一句。", "第二句。", "第三句。", "第四句。", "第五句。"],
      ["第一句。", "第二句。", ...],
      ...
    ]

驗證規則：
    1. 頂層必須是 list
    2. 段落數量：8–9 段
    3. 每個段落至少 8 句
"""

import json
import sys


def validate(data) -> list[str]:
    errors: list[str] = []

    if not isinstance(data, list):
        return ["頂層必須是一個 list"]

    count = len(data)
    if not (5 <= count <= 9):
        errors.append(f"段落數量錯誤：目前 {count} 段，應為 5–9 段")

    for i, para in enumerate(data):
        if not isinstance(para, list):
            errors.append(f"第 {i + 1} 段格式錯誤：應為 list（句子陣列），實際為 {type(para).__name__}")
            continue
        if len(para) < 8:
            errors.append(
                f"第 {i + 1} 段句子不足：目前 {len(para)} 句，至少需要 8 句"
            )

    return errors


def main() -> None:
    if len(sys.argv) != 2:
        print("用法：python validate.py <json_file_path>")
        sys.exit(1)

    json_path = sys.argv[1]

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"錯誤：JSON 解析失敗 — {e}")
        sys.exit(1)

    errors = validate(data)

    if errors:
        for err in errors:
            print(f"[錯誤] {err}")
        sys.exit(1)
    else:
        print(f"驗證成功：共 {len(data)} 段")


if __name__ == "__main__":
    main()
