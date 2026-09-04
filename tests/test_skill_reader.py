import json
from pathlib import Path

import pytest

from skill_reader import (
    build_roadmap,
    list_subcategories,
    load_taxonomy,
    parse_category_map,
    parse_fm,
    scan,
    validate_structure,
)


ROOT = Path(__file__).resolve().parents[1]


def test_parse_simple_frontmatter() -> None:
    metadata = parse_fm(
        '---\nname: sample-skill\ndescription: "A short description."\n---\nBody\n'
    )
    assert metadata == {
        "name": "sample-skill",
        "description": "A short description.",
    }


def test_parse_literal_block_description() -> None:
    metadata = parse_fm(
        "---\nname: sample-skill\ndescription: |\n  First line.\n  Second line.\n---\n"
    )
    assert metadata["description"] == "First line.\nSecond line."


def test_parse_folded_block_description() -> None:
    metadata = parse_fm(
        "---\nname: sample-skill\ndescription: >-\n  First line.\n  Second line.\n---\n"
    )
    assert metadata["description"] == "First line. Second line."


def test_parse_block_description_stops_at_next_key() -> None:
    metadata = parse_fm(
        "---\nname: sample-skill\ndescription: >\n"
        "  Folded description.\nmetadata:\n  owner: test\n---\n"
    )
    assert metadata["description"] == "Folded description."


def test_parse_indented_frontmatter_fields() -> None:
    metadata = parse_fm(
        "---\n  name: sample-skill\n  description: Indented metadata.\n  ---\n"
    )
    assert metadata == {
        "name": "sample-skill",
        "description": "Indented metadata.",
    }


def test_nested_description_does_not_override_top_level() -> None:
    metadata = parse_fm(
        "---\nname: sample-skill\ndescription: Top-level description.\n"
        "metadata:\n  description: Nested metadata value.\n---\n"
    )
    assert metadata["description"] == "Top-level description."


def write_skill(path: Path, name: str, description: str) -> None:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n",
        encoding="utf-8",
    )


def write_taxonomy(root: Path, categories: dict) -> None:
    (root / "category-taxonomy.json").write_text(
        json.dumps({"schema_version": 2, "categories": categories}),
        encoding="utf-8",
    )


def write_router(root: Path) -> None:
    (root / "SKILL.md").write_text(
        "## 知識庫分類地圖\n\n"
        "| # | 資料夾 | 英文名 | 說明 |\n"
        "|---|---|---|---|\n"
        "| 1 | `Coding/` | Coding | Actual coding description. |\n"
        "| 2 | `Science/` | Science | Actual science description. |\n\n"
        "> **新增 skill 時**\n",
        encoding="utf-8",
    )


def sample_taxonomy() -> dict:
    return {
        "Science": {
            "subcategories": [
                {
                    "id": "bioinformatics",
                    "name": "Bioinformatics",
                    "description": "Sequence and omics methods.",
                },
                {
                    "id": "quantum",
                    "name": "Quantum",
                    "description": "Quantum computing methods.",
                },
            ]
        }
    }


def test_flat_category_scan_remains_backward_compatible(tmp_path) -> None:
    write_skill(
        tmp_path / "Coding" / "python-testing", "python-testing", "Test Python."
    )

    assert scan(tmp_path, ["Coding"]) == [
        {
            "category": "Coding",
            "subcategory": None,
            "skill": "python-testing",
            "path": f"{tmp_path.name}/Coding/python-testing/SKILL.md",
            "name": "python-testing",
            "description": "Test Python.",
        }
    ]


def test_physical_subcategory_filter_uses_parent_child_paths(tmp_path) -> None:
    write_skill(
        tmp_path / "Science" / "bioinformatics" / "biopython",
        "biopython",
        "Sequence analysis.",
    )
    write_skill(
        tmp_path / "Science" / "quantum" / "qiskit",
        "qiskit",
        "Quantum circuits.",
    )
    write_taxonomy(tmp_path, sample_taxonomy())

    skills = scan(tmp_path, ["Science"], subcategories=["quantum"])

    assert [skill["skill"] for skill in skills] == ["qiskit"]
    assert skills[0]["subcategory"] == "quantum"
    assert skills[0]["path"].endswith("Science/quantum/qiskit/SKILL.md")


def test_query_search_is_case_insensitive_and_subcategory_scoped(tmp_path) -> None:
    write_skill(
        tmp_path / "Science" / "bioinformatics" / "biopython",
        "biopython",
        "Sequence analysis.",
    )
    write_skill(
        tmp_path / "Science" / "bioinformatics" / "tables",
        "tables",
        "Static table formatting.",
    )
    write_taxonomy(tmp_path, sample_taxonomy())

    skills = scan(
        tmp_path,
        ["Science"],
        subcategories=["bioinformatics"],
        query="SEQUENCE",
    )
    assert [skill["skill"] for skill in skills] == ["biopython"]


def test_list_subcategories_reports_declared_names_and_counts(tmp_path) -> None:
    write_skill(
        tmp_path / "Science" / "bioinformatics" / "biopython",
        "biopython",
        "Sequence analysis.",
    )
    (tmp_path / "Science" / "quantum").mkdir(parents=True)
    write_taxonomy(tmp_path, sample_taxonomy())

    assert list_subcategories(tmp_path, ["Science"]) == [
        {
            "category": "Science",
            "id": "bioinformatics",
            "name": "Bioinformatics",
            "description": "Sequence and omics methods.",
            "count": 1,
        },
        {
            "category": "Science",
            "id": "quantum",
            "name": "Quantum",
            "description": "Quantum computing methods.",
            "count": 0,
        },
    ]


def test_list_subcategories_does_not_invent_children_for_flat_category(
    tmp_path,
) -> None:
    write_skill(
        tmp_path / "Coding" / "python-testing", "python-testing", "Test Python."
    )
    assert list_subcategories(tmp_path, ["Coding"]) == []


def test_duplicate_subcategory_definition_is_rejected(tmp_path) -> None:
    write_taxonomy(
        tmp_path,
        {
            "Science": {
                "subcategories": [
                    {"id": "same", "name": "One", "description": "One."},
                    {"id": "same", "name": "Two", "description": "Two."},
                ]
            }
        },
    )
    with pytest.raises(ValueError, match="重複定義 subcategory"):
        load_taxonomy(tmp_path)


def test_configured_category_requires_at_least_one_subcategory(tmp_path) -> None:
    write_taxonomy(tmp_path, {"Science": {"subcategories": []}})
    with pytest.raises(ValueError, match="至少一個 subcategory"):
        load_taxonomy(tmp_path)


def test_taxonomy_rejects_invalid_first_level_category_id(tmp_path) -> None:
    write_taxonomy(tmp_path, {"bad_category": sample_taxonomy()["Science"]})
    with pytest.raises(ValueError, match="第一層分類名稱"):
        load_taxonomy(tmp_path)


def test_taxonomy_rejects_overlong_subcategory_id(tmp_path) -> None:
    invalid = sample_taxonomy()
    invalid["Science"]["subcategories"][0]["id"] = "a" * 65
    write_taxonomy(tmp_path, invalid)
    with pytest.raises(ValueError, match="subcategory id"):
        load_taxonomy(tmp_path)


def test_validation_rejects_invalid_flat_category_id(tmp_path) -> None:
    (tmp_path / "SKILL.md").write_text(
        "## 知識庫分類地圖\n\n"
        "| # | 資料夾 | 英文名 | 說明 |\n"
        "|---|---|---|---|\n"
        "| 1 | `bad_category/` | Bad Category | Invalid category. |\n\n"
        "> **新增 skill 時**\n",
        encoding="utf-8",
    )
    (tmp_path / "bad_category").mkdir()

    assert any("第一層分類名稱" in error for error in validate_structure(tmp_path))


def test_parse_category_map_returns_actual_first_level_descriptions(tmp_path) -> None:
    write_router(tmp_path)
    assert parse_category_map(tmp_path / "SKILL.md") == [
        {
            "position": 1,
            "category": "Coding",
            "name": "Coding",
            "description": "Actual coding description.",
        },
        {
            "position": 2,
            "category": "Science",
            "name": "Science",
            "description": "Actual science description.",
        },
    ]


def test_roadmap_exposes_first_level_descriptions_and_child_names_only(
    tmp_path,
) -> None:
    write_router(tmp_path)
    write_skill(
        tmp_path / "Coding" / "python-testing", "python-testing", "Test Python."
    )
    write_skill(
        tmp_path / "Science" / "bioinformatics" / "biopython",
        "biopython",
        "Sequence analysis.",
    )
    (tmp_path / "Science" / "quantum").mkdir(parents=True)
    write_taxonomy(tmp_path, sample_taxonomy())

    roadmap = build_roadmap(tmp_path)
    assert roadmap == [
        {
            "position": 1,
            "category": "Coding",
            "name": "Coding",
            "description": "Actual coding description.",
            "subcategory_count": 0,
            "subcategories": [],
            "skill_count": 1,
        },
        {
            "position": 2,
            "category": "Science",
            "name": "Science",
            "description": "Actual science description.",
            "subcategory_count": 2,
            "subcategories": ["bioinformatics", "quantum"],
            "skill_count": 1,
        },
    ]
    assert "Sequence and omics methods." not in json.dumps(roadmap)


def test_validation_accepts_new_skill_in_declared_subcategory(tmp_path) -> None:
    write_router(tmp_path)
    write_skill(
        tmp_path / "Coding" / "python-testing", "python-testing", "Test Python."
    )
    write_skill(
        tmp_path / "Science" / "bioinformatics" / "new-skill",
        "new-skill",
        "A new sequence method.",
    )
    (tmp_path / "Science" / "quantum").mkdir(parents=True)
    write_taxonomy(tmp_path, sample_taxonomy())
    assert validate_structure(tmp_path) == []


def test_validation_rejects_flat_skill_in_subcategorized_parent(tmp_path) -> None:
    write_router(tmp_path)
    write_skill(tmp_path / "Science" / "misplaced", "misplaced", "Wrong level.")
    (tmp_path / "Science" / "bioinformatics").mkdir(parents=True)
    (tmp_path / "Science" / "quantum").mkdir(parents=True)
    write_taxonomy(tmp_path, sample_taxonomy())
    assert any(
        "必須放在已宣告的 subcategory" in error
        for error in validate_structure(tmp_path)
    )


def test_validation_rejects_undeclared_subcategory(tmp_path) -> None:
    write_router(tmp_path)
    write_skill(
        tmp_path / "Science" / "unknown" / "new-skill",
        "new-skill",
        "Unknown branch.",
    )
    (tmp_path / "Science" / "bioinformatics").mkdir(parents=True)
    (tmp_path / "Science" / "quantum").mkdir(parents=True)
    write_taxonomy(tmp_path, sample_taxonomy())
    assert any(
        "未宣告的 subcategory" in error for error in validate_structure(tmp_path)
    )


def test_repository_taxonomy_is_selective_and_matches_physical_tree() -> None:
    taxonomy = load_taxonomy(ROOT)
    assert set(taxonomy["categories"]) == {"Science", "Web-Design"}
    assert validate_structure(ROOT) == []

    for category, category_data in taxonomy["categories"].items():
        declared = {item["id"] for item in category_data["subcategories"]}
        physical = {
            path.name
            for path in (ROOT / category).iterdir()
            if path.is_dir()
            and any((child / "SKILL.md").is_file() for child in path.iterdir())
        }
        assert declared == physical


def test_repository_taxonomy_declares_its_json_schema() -> None:
    raw = json.loads((ROOT / "category-taxonomy.json").read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schemas" / "category-taxonomy.schema.json").read_text(encoding="utf-8")
    )
    assert raw["$schema"] == "./schemas/category-taxonomy.schema.json"
    assert schema["$id"].endswith("category-taxonomy.schema.json")
    assert schema["properties"]["schema_version"]["const"] == 2
    category_schema = schema["properties"]["categories"]
    assert category_schema["propertyNames"]["maxLength"] == 64
    subcategory_schema = category_schema["additionalProperties"]["properties"][
        "subcategories"
    ]["items"]["properties"]["id"]
    assert subcategory_schema["maxLength"] == 64
