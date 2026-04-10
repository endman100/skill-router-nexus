#!/usr/bin/env python3
"""
Threads Post Writer — Preview MD 產生工具

用法：
    python to_preview_md.py <json_file_path> [base_filename]

參數：
    json_file_path  已通過驗證的 JSON 檔案路徑
    base_filename   輸出檔案的基底名稱（不含副檔名，可選）
                    若未提供，以 JSON 檔名（去掉副檔名）為基底

輸出：
    與 json_file_path 同目錄下的 <base_filename>-preview.md
    exit code 0 成功，exit code 1 失敗

注意：
    ⚠️ 產生的 -preview.md 檔案請勿手動修改。
       如需更新內容，請修改來源 JSON 後重新執行本腳本。
"""

import json
import os
import sys


def generate(data: list, output_path: str) -> None:
    lines = [
        "<!-- ⚠️ 此檔案由程式自動產生，請勿直接修改。"
        " 如需更新內容，請修改來源 JSON 後重新執行 to_preview_md.py。 -->",
        "",
    ]

    for para in data:
        for sentence in para:
            lines.append(sentence)
            lines.append("")  # 每句後空一行
        lines.append("----")  # 段落後分隔線

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python to_preview_md.py <json_file_path> [base_filename]")
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

    if not isinstance(data, list):
        print("錯誤：JSON 頂層必須是 list，請先執行 validate.py 確認格式")
        sys.exit(1)

    json_dir = os.path.dirname(os.path.abspath(json_path))

    if len(sys.argv) >= 3:
        base = sys.argv[2].removesuffix("-preview")
    else:
        base = os.path.splitext(os.path.basename(json_path))[0].removesuffix("-preview")

    output_path = os.path.join(json_dir, f"{base}-preview.md")

    generate(data, output_path)
    print(f"Preview MD 已輸出：{output_path}")


if __name__ == "__main__":
    main()
