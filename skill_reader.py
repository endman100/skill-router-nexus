# skill_reader.py — skill-router-nexus 子 skill 掃描工具
# 由 SKILL.md Step 2 路由流程呼叫，請勿單獨修改路由邏輯
# 用法：python skill_reader.py [-c <category>]
import argparse
import re
import sys
from pathlib import Path

SKIP = {"__pycache__", ".git", "node_modules"}


def parse_fm(content):
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    meta = {}
    for line in content[3:end].splitlines():
        m = re.match(r'^(name|description)\s*:\s*["\']?(.*?)["\']?\s*$', line)
        if m:
            meta[m.group(1)] = m.group(2).strip("\"'")
    return meta


def scan(base, category=None):
    if category:
        cat_path = base / category
        if not cat_path.is_dir():
            print(f"找不到分類：{category}", file=sys.stderr)
            sys.exit(1)
        dirs = [(category, cat_path)]
    else:
        dirs = [(d.name, d) for d in sorted(base.iterdir()) if d.is_dir() and d.name not in SKIP]

    results = []
    for cat, cat_path in dirs:
        for skill_dir in sorted(cat_path.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name in SKIP:
                continue
            f = skill_dir / "SKILL.md"
            if not f.exists():
                continue
            meta = parse_fm(f.read_text(encoding="utf-8"))
            results.append({
                "category": cat,
                "skill": skill_dir.name,
                "path": str(f.relative_to(base.parent)).replace("\\", "/"),
                "name": meta.get("name", skill_dir.name),
                "description": meta.get("description", ""),
            })
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--category", "-c")
    args = p.parse_args()

    base = Path(__file__).parent
    skills = scan(base, args.category)
    if not skills:
        print("（找不到任何 skill）")
    else:
        for s in skills:
            print(f"[{s['category']}] {s['skill']}")
            print(f"  name : {s['name']}")
            print(f"  desc : {s['description']}")
            print(f"  path : {s['path']}")
            print()