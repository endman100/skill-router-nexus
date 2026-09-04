# skill_reader.py — skill-router-nexus 查詢與結構驗證工具
# 用法：python -B skill_reader.py [--roadmap] [-c <category>] [-s <subcategory>] [-q <query>]
import argparse
import json
import re
import sys
from pathlib import Path

SKIP = {"__pycache__", ".git", "node_modules"}
TAXONOMY_FILE = "category-taxonomy.json"
CATEGORY_ID_PATTERN = r"^[A-Z0-9][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*$"
SUBCATEGORY_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
MAX_ID_LENGTH = 64


def _valid_id(value, pattern):
    return (
        isinstance(value, str)
        and len(value) <= MAX_ID_LENGTH
        and re.fullmatch(pattern, value) is not None
    )


def parse_fm(content):
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}

    frontmatter = lines[1:end]
    significant_lines = [
        line
        for line in frontmatter
        if line.strip() and not line.lstrip().startswith("#")
    ]
    base_indent = min(
        (len(line) - len(line.lstrip()) for line in significant_lines),
        default=0,
    )
    if base_indent:
        frontmatter = [
            line[base_indent:] if line.strip() else "" for line in frontmatter
        ]

    meta = {}
    index = 0
    while index < len(frontmatter):
        line = frontmatter[index]
        match = re.match(r"^(name|description)\s*:\s*(.*?)\s*$", line)
        if not match:
            index += 1
            continue

        key, raw_value = match.groups()
        if re.fullmatch(r"[|>][+-]?", raw_value):
            block_lines = []
            index += 1
            while index < len(frontmatter):
                block_line = frontmatter[index]
                if block_line and not block_line[0].isspace():
                    break
                block_lines.append(block_line)
                index += 1

            non_empty = [line for line in block_lines if line.strip()]
            indent = min(
                (len(line) - len(line.lstrip()) for line in non_empty),
                default=0,
            )
            normalized = [
                line[indent:].rstrip() if line.strip() else "" for line in block_lines
            ]

            if raw_value.startswith("|"):
                value = "\n".join(normalized).strip()
            else:
                paragraphs = []
                paragraph = []
                for block_line in normalized:
                    if block_line:
                        paragraph.append(block_line.strip())
                    elif paragraph:
                        paragraphs.append(" ".join(paragraph))
                        paragraph = []
                if paragraph:
                    paragraphs.append(" ".join(paragraph))
                value = "\n\n".join(paragraphs).strip()

            meta[key] = value
            continue

        if (
            len(raw_value) >= 2
            and raw_value[0] == raw_value[-1]
            and raw_value[0] in {'"', "'"}
        ):
            raw_value = raw_value[1:-1]
        meta[key] = raw_value
        index += 1
    return meta


def parse_values(raw_values):
    if not raw_values:
        return []

    values = []
    for item in raw_values:
        values.extend(token.strip() for token in item.split(",") if token.strip())
    return list(dict.fromkeys(values))


def parse_categories(raw_categories):
    """Backward-compatible alias used by existing callers."""
    return parse_values(raw_categories)


def load_taxonomy(base, taxonomy_path=None):
    path = Path(taxonomy_path) if taxonomy_path else Path(base) / TAXONOMY_FILE
    if not path.exists():
        return {"schema_version": 2, "categories": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"無法讀取 category taxonomy {path}: {exc}") from exc

    if data.get("schema_version") != 2 or not isinstance(data.get("categories"), dict):
        raise ValueError(
            "category taxonomy 必須使用 schema_version 2 並包含 categories"
        )

    for category, category_data in data["categories"].items():
        if not _valid_id(category, CATEGORY_ID_PATTERN):
            raise ValueError(
                f"第一層分類名稱必須符合 Title-Kebab-Case 且不超過 "
                f"{MAX_ID_LENGTH} 字元: {category}"
            )
        subcategories = (
            category_data.get("subcategories")
            if isinstance(category_data, dict)
            else None
        )
        if not isinstance(subcategories, list) or not subcategories:
            raise ValueError(f"分類 {category} 必須包含至少一個 subcategory")

        seen = set()
        for subcategory in subcategories:
            if not isinstance(subcategory, dict):
                raise ValueError(f"分類 {category} 包含無效的 subcategory")
            subcategory_id = subcategory.get("id")
            if not _valid_id(subcategory_id, SUBCATEGORY_ID_PATTERN):
                raise ValueError(
                    f"分類 {category} 包含無效的 subcategory id: {subcategory_id}"
                )
            if subcategory_id in seen:
                raise ValueError(
                    f"分類 {category} 重複定義 subcategory: {subcategory_id}"
                )
            seen.add(subcategory_id)
            for field in ("name", "description"):
                if (
                    not isinstance(subcategory.get(field), str)
                    or not subcategory[field].strip()
                ):
                    raise ValueError(
                        f"subcategory {category}/{subcategory_id} 缺少 {field}"
                    )
    return data


def parse_category_map(router_path):
    content = Path(router_path).read_text(encoding="utf-8")
    entries = []
    in_map = False
    row_pattern = re.compile(
        r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$"
    )
    for line in content.splitlines():
        if line.strip() == "## 知識庫分類地圖":
            in_map = True
            continue
        if in_map and line.startswith("> **新增 skill"):
            break
        if not in_map:
            continue
        match = row_pattern.match(line)
        if not match:
            continue
        position, folder, name, description = match.groups()
        entries.append(
            {
                "position": int(position),
                "category": folder.strip().rstrip("/"),
                "name": name.strip(),
                "description": description.strip(),
            }
        )
    return entries


def _category_dirs(base, categories):
    base = Path(base)
    if categories:
        dirs = []
        missing = []
        for category in categories:
            cat_path = base / category
            if not cat_path.is_dir():
                missing.append(category)
            else:
                dirs.append((category, cat_path))
        if missing:
            raise ValueError(f"找不到分類：{', '.join(missing)}")
        return dirs

    router_path = base / "SKILL.md"
    if router_path.is_file():
        return [
            (entry["category"], base / entry["category"])
            for entry in parse_category_map(router_path)
            if (base / entry["category"]).is_dir()
        ]
    return [
        (path.name, path)
        for path in sorted(base.iterdir())
        if path.is_dir() and path.name not in SKIP
    ]


def _subcategory_metadata(taxonomy, category):
    items = taxonomy.get("categories", {}).get(category, {}).get("subcategories", [])
    return {item["id"]: item for item in items}


def _flat_skill_dirs(category_path):
    for path in sorted(category_path.iterdir()):
        if path.is_dir() and path.name not in SKIP and (path / "SKILL.md").is_file():
            yield path


def _nested_skill_dirs(category_path, subcategory_ids):
    for subcategory_id in subcategory_ids:
        subcategory_path = category_path / subcategory_id
        if not subcategory_path.is_dir():
            continue
        for skill_path in sorted(subcategory_path.iterdir()):
            if (
                skill_path.is_dir()
                and skill_path.name not in SKIP
                and (skill_path / "SKILL.md").is_file()
            ):
                yield subcategory_id, skill_path


def _skill_record(base, category, subcategory, skill_path):
    skill_file = skill_path / "SKILL.md"
    meta = parse_fm(skill_file.read_text(encoding="utf-8"))
    return {
        "category": category,
        "subcategory": subcategory,
        "skill": skill_path.name,
        "path": str(skill_file.relative_to(Path(base).parent)).replace("\\", "/"),
        "name": meta.get("name", skill_path.name),
        "description": meta.get("description", ""),
    }


def scan(base, categories=None, subcategories=None, query=None, taxonomy=None):
    base = Path(base)
    taxonomy = taxonomy or load_taxonomy(base)
    requested = set(subcategories or [])
    discovered = set()
    results = []

    for category, category_path in _category_dirs(base, categories):
        declared = _subcategory_metadata(taxonomy, category)
        discovered.update(declared)
        if declared:
            selected = [item for item in declared if not requested or item in requested]
            locations = _nested_skill_dirs(category_path, selected)
        else:
            locations = ((None, path) for path in _flat_skill_dirs(category_path))

        for subcategory, skill_path in locations:
            record = _skill_record(base, category, subcategory, skill_path)
            if query:
                haystack = "\n".join(
                    (record["skill"], record["name"], record["description"])
                ).casefold()
                if query.casefold() not in haystack:
                    continue
            results.append(record)

    unknown = requested - discovered
    if unknown:
        raise ValueError(f"找不到 subcategory：{', '.join(sorted(unknown))}")
    return results


def list_subcategories(base, categories=None, taxonomy=None):
    base = Path(base)
    taxonomy = taxonomy or load_taxonomy(base)
    results = []
    for category, category_path in _category_dirs(base, categories):
        for subcategory_id, metadata in _subcategory_metadata(
            taxonomy, category
        ).items():
            count = sum(
                1
                for _subcategory, _skill in _nested_skill_dirs(
                    category_path, [subcategory_id]
                )
            )
            results.append(
                {
                    "category": category,
                    "id": subcategory_id,
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "count": count,
                }
            )
    return results


def build_roadmap(base, taxonomy=None):
    base = Path(base)
    taxonomy = taxonomy or load_taxonomy(base)
    results = []
    for entry in parse_category_map(base / "SKILL.md"):
        category = entry["category"]
        category_path = base / category
        if not category_path.is_dir():
            continue
        subcategory_ids = list(_subcategory_metadata(taxonomy, category))
        item = dict(entry)
        item.update(
            {
                "subcategory_count": len(subcategory_ids),
                "subcategories": subcategory_ids,
                "skill_count": len(scan(base, [category], taxonomy=taxonomy)),
            }
        )
        results.append(item)
    return results


def _metadata_errors(skill_path):
    meta = parse_fm((skill_path / "SKILL.md").read_text(encoding="utf-8"))
    errors = []
    if not meta.get("name"):
        errors.append(f"{skill_path}: SKILL.md 缺少 name")
    if not meta.get("description"):
        errors.append(f"{skill_path}: SKILL.md 缺少 description")
    return errors


def validate_structure(base, categories=None, taxonomy=None):
    base = Path(base)
    taxonomy = taxonomy or load_taxonomy(base)
    errors = []
    category_map = {
        item["category"]: item for item in parse_category_map(base / "SKILL.md")
    }
    selected = categories or list(category_map)

    for category in taxonomy.get("categories", {}):
        if category not in category_map:
            errors.append(f"{category}: taxonomy 分類未登錄於第一層分類地圖")

    for category in category_map:
        if not _valid_id(category, CATEGORY_ID_PATTERN):
            errors.append(
                f"{category}: 第一層分類名稱必須符合 Title-Kebab-Case 且不超過 "
                f"{MAX_ID_LENGTH} 字元"
            )

    for category in selected:
        category_path = base / category
        if not category_path.is_dir():
            errors.append(f"{category}: 第一層分類目錄不存在")
            continue

        declared = _subcategory_metadata(taxonomy, category)
        seen_skills = set()
        if declared:
            for skill_path in _flat_skill_dirs(category_path):
                errors.append(
                    f"{category}/{skill_path.name}: 已啟用第二層，skill 必須放在已宣告的 subcategory"
                )

            for subcategory_id in declared:
                subcategory_path = category_path / subcategory_id
                if not subcategory_path.is_dir():
                    errors.append(
                        f"{category}/{subcategory_id}: 已宣告的 subcategory 目錄不存在"
                    )
                    continue
                child_dirs = [
                    child
                    for child in subcategory_path.iterdir()
                    if child.is_dir() and child.name not in SKIP
                ]
                if len(child_dirs) > 50:
                    errors.append(
                        f"{category}/{subcategory_id}: subcategory 超過 50 個 skill"
                    )
                for skill_path in child_dirs:
                    if not (skill_path / "SKILL.md").is_file():
                        errors.append(f"{skill_path}: skill 目錄缺少 SKILL.md")
                        continue
                    if skill_path.name in seen_skills:
                        errors.append(
                            f"{category}: skill {skill_path.name} 在多個 subcategory 重複"
                        )
                    seen_skills.add(skill_path.name)
                    errors.extend(_metadata_errors(skill_path))

            for child in category_path.iterdir():
                if not child.is_dir() or child.name in declared or child.name in SKIP:
                    continue
                if (child / "SKILL.md").is_file():
                    continue
                if any(
                    grandchild.is_dir() and (grandchild / "SKILL.md").is_file()
                    for grandchild in child.iterdir()
                ):
                    errors.append(f"{category}/{child.name}: 未宣告的 subcategory")
        else:
            for skill_path in _flat_skill_dirs(category_path):
                errors.extend(_metadata_errors(skill_path))
            for child in category_path.iterdir():
                if not child.is_dir() or child.name in SKIP:
                    continue
                if (child / "SKILL.md").is_file():
                    continue
                if any(
                    grandchild.is_dir() and (grandchild / "SKILL.md").is_file()
                    for grandchild in child.iterdir()
                ):
                    errors.append(
                        f"{category}/{child.name}: 未宣告的 subcategory；先更新 {TAXONOMY_FILE}"
                    )
    return errors


def _print_skills(skills, show_subcategory=False):
    for skill in skills:
        print(f"[{skill['category']}] {skill['skill']}")
        if show_subcategory and skill["subcategory"]:
            print(f"  subcategory: {skill['subcategory']}")
        print(f"  name : {skill['name']}")
        print(f"  desc : {skill['description']}")
        print(f"  path : {skill['path']}")
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--category",
        "-c",
        action="append",
        help="可重複指定或用逗號分隔，例如 -c GitHub -c Coding",
    )
    parser.add_argument(
        "--subcategory",
        "-s",
        action="append",
        help="只掃描指定第二層 subcategory；可重複指定或用逗號分隔",
    )
    parser.add_argument(
        "--list-subcategories",
        action="store_true",
        help="列出所選第一層分類的 subcategory 詳細資料與 skill 數量",
    )
    parser.add_argument(
        "--roadmap",
        action="store_true",
        help="列出所有第一層分類的實際描述、第二層名稱與分叉數，不展開 skill",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="驗證父子目錄、taxonomy、SKILL.md metadata 與新增 skill 放置規則",
    )
    parser.add_argument(
        "--query",
        "-q",
        help="在目前 category／subcategory 範圍內搜尋 skill 名稱與描述",
    )
    parser.add_argument("--json", action="store_true", help="輸出機器可讀 JSON")
    args = parser.parse_args()

    base = Path(__file__).parent
    categories = parse_values(args.category)
    subcategories = parse_values(args.subcategory)

    try:
        taxonomy = load_taxonomy(base)
        if args.validate:
            errors = validate_structure(base, categories or None, taxonomy)
            if errors:
                if args.json:
                    print(
                        json.dumps(
                            {"valid": False, "errors": errors},
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                else:
                    for error in errors:
                        print(f"ERROR: {error}", file=sys.stderr)
                return 1
            output = {"valid": True, "errors": []}
        elif args.roadmap:
            output = build_roadmap(base, taxonomy)
        elif args.list_subcategories:
            output = list_subcategories(base, categories or None, taxonomy)
        else:
            output = scan(
                base,
                categories or None,
                subcategories=subcategories,
                query=args.query,
                taxonomy=taxonomy,
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.validate:
        print("VALID: category taxonomy 與 skill 目錄結構一致")
    elif args.roadmap:
        for item in output:
            print(f"[{item['position']}] {item['category']} — {item['name']}")
            print(f"  desc : {item['description']}")
            branches = ", ".join(item["subcategories"]) or "—"
            print(f"  subcategories ({item['subcategory_count']}): {branches}")
            print(f"  skills: {item['skill_count']}")
            print()
    elif args.list_subcategories:
        if not output:
            print("（所選分類未啟用第二層 subcategory）")
        else:
            for item in output:
                print(f"[{item['category']}] {item['id']} ({item['count']})")
                print(f"  name : {item['name']}")
                print(f"  desc : {item['description']}")
                print()
    elif not output:
        print("（找不到任何 skill）")
    else:
        _print_skills(output, show_subcategory=bool(subcategories))
    return 0


if __name__ == "__main__":
    sys.exit(main())
