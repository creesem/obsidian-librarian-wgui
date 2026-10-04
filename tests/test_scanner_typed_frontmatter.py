"""Tests for the typed (YAML-faithful) frontmatter reader."""

from __future__ import annotations

from pathlib import Path

from obsidian_inventory import build_index, extract_frontmatter, read_frontmatter_typed


def test_typed_reader_preserves_scalars() -> None:
    content = "---\ntype: project\nstatus: active\n---\n# Body\n"
    assert read_frontmatter_typed(content) == {"type": "project", "status": "active"}


def test_typed_reader_preserves_block_list() -> None:
    content = (
        "---\n"
        "type: project\n"
        "people:\n"
        "  - \"[[Alex Rivera]]\"\n"
        "  - \"[[Sam Okafor]]\"\n"
        "---\n"
        "# Body\n"
    )
    assert read_frontmatter_typed(content)["people"] == ["[[Alex Rivera]]", "[[Sam Okafor]]"]


def test_typed_reader_preserves_flow_list() -> None:
    content = "---\nsystems: [CareLogic, Snowflake]\n---\n# Body\n"
    assert read_frontmatter_typed(content)["systems"] == ["CareLogic", "Snowflake"]


def test_typed_reader_preserves_nested_map() -> None:
    content = "---\ntype: ticket\nexternal:\n  system: servicedesk-plus\n  id: '31814'\n---\n"
    parsed = read_frontmatter_typed(content)
    assert parsed["external"] == {"system": "servicedesk-plus", "id": "31814"}


def test_typed_reader_handles_missing_block() -> None:
    assert read_frontmatter_typed("# No frontmatter\n") == {}


def test_typed_reader_handles_malformed_block_without_raising() -> None:
    # Unterminated block is not well-formed frontmatter -> empty mapping.
    assert read_frontmatter_typed("---\ntype: project\n") == {}


def test_existing_extract_frontmatter_behavior_is_unchanged() -> None:
    # The lossy reader still flattens block lists into a comma string.
    content = (
        "---\n"
        "people:\n"
        "  - \"[[Alex Rivera]]\"\n"
        "  - \"[[Sam Okafor]]\"\n"
        "---\n"
    )
    assert extract_frontmatter(content)["people"] == "[[Alex Rivera]], [[Sam Okafor]]"


def test_build_index_populates_typed_frontmatter(tmp_path: Path) -> None:
    note = tmp_path / "Notes" / "p.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "---\ntype: project\npeople:\n  - \"[[Alex Rivera]]\"\n---\n# P\n",
        encoding="utf-8",
    )
    record = build_index(tmp_path, "vault").indexed_records[0]
    assert record.frontmatter_typed["type"] == "project"
    assert record.frontmatter_typed["people"] == ["[[Alex Rivera]]"]
