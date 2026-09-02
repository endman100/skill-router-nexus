from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "AI-Research" / "autoscirub"
VERIFY_ENTRY = ROOT / "Agent-Verification" / "autoscirub-verify" / "SKILL.md"

STAGE_REFERENCES = {
    "rubric-skeleton-induction.md",
    "scientific-literature-grounding.md",
    "task-data-exploration.md",
    "criterion-synthesis.md",
    "criterion-level-verification.md",
    "targeted-revision.md",
}


def test_autoscirub_package_has_controller_stages_and_license() -> None:
    assert (PACKAGE / "SKILL.md").is_file()
    assert (PACKAGE / "LICENSE").is_file()
    assert VERIFY_ENTRY.is_file()
    assert {path.name for path in (PACKAGE / "references").glob("*.md")} == STAGE_REFERENCES


def test_controller_declares_every_stage_reference() -> None:
    content = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")

    for filename in STAGE_REFERENCES:
        assert f"references/{filename}" in content
    assert "do not preload all six references" in content
    assert "at most three revision rounds" in content


def test_skill_frontmatter_is_minimal_and_trigger_boundaries_are_explicit() -> None:
    for path in (PACKAGE / "SKILL.md", VERIFY_ENTRY):
        content = path.read_text(encoding="utf-8")
        match = re.match(r"---\n(.*?)\n---", content, flags=re.DOTALL)
        assert match is not None
        keys = {
            line.split(":", 1)[0]
            for line in match.group(1).splitlines()
            if ":" in line
        }
        assert keys == {"name", "description"}

    controller = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
    verifier = VERIFY_ENTRY.read_text(encoding="utf-8")
    assert "Do not use for simple paper lookup" in controller
    assert "existing `.autoscirub/executable_rubric.json`" in verifier
    assert "supplements rather than replaces general completion verification" in verifier


def test_all_markdown_relative_references_resolve() -> None:
    markdown_link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    for path in PACKAGE.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        for target in markdown_link.findall(content):
            if "://" in target or target.startswith("#"):
                continue
            assert (path.parent / target).resolve().exists(), (path, target)
