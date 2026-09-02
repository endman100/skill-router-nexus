from skill_reader import parse_fm


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
        "---\n"
        "name: sample-skill\n"
        "description: |\n"
        "  First line.\n"
        "  Second line.\n"
        "---\n"
    )

    assert metadata["description"] == "First line.\nSecond line."


def test_parse_folded_block_description() -> None:
    metadata = parse_fm(
        "---\n"
        "name: sample-skill\n"
        "description: >-\n"
        "  First line.\n"
        "  Second line.\n"
        "---\n"
    )

    assert metadata["description"] == "First line. Second line."


def test_parse_block_description_stops_at_next_key() -> None:
    metadata = parse_fm(
        "---\n"
        "name: sample-skill\n"
        "description: >\n"
        "  Folded description.\n"
        "metadata:\n"
        "  owner: test\n"
        "---\n"
    )

    assert metadata["description"] == "Folded description."


def test_parse_indented_frontmatter_fields() -> None:
    metadata = parse_fm(
        "---\n"
        "  name: sample-skill\n"
        "  description: Indented metadata.\n"
        "  ---\n"
    )

    assert metadata == {
        "name": "sample-skill",
        "description": "Indented metadata.",
    }


def test_nested_description_does_not_override_top_level() -> None:
    metadata = parse_fm(
        "---\n"
        "name: sample-skill\n"
        "description: Top-level description.\n"
        "metadata:\n"
        "  description: Nested metadata value.\n"
        "---\n"
    )

    assert metadata["description"] == "Top-level description."
