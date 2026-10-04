"""Builder, frontmatter, and determinism tests for generated views."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from obsidian_operator.repository import OperatorIndex
from obsidian_operator.views import VIEWS, build_view

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"
TODAY = date(2026, 10, 10)
GENERATED_AT = "2026-10-03T12:00:00+00:00"


def _view(name: str, index: OperatorIndex):
    return build_view(name, index, today=TODAY, generated_at=GENERATED_AT)


def test_view_set_is_exactly_expected() -> None:
    assert set(VIEWS) == {"today", "projects", "team", "tickets", "waiting", "manager-review"}


def test_each_view_builds_from_fixture() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    for name in VIEWS:
        view = _view(name, index)
        assert view.body
        assert view.name == name
        assert view.filename.endswith(".md")


def test_empty_vault_renders_zero_items(tmp_path: Path) -> None:
    index = OperatorIndex.from_vault(tmp_path)
    for name in VIEWS:
        view = _view(name, index)
        assert view.source_count == 0
        assert view.body


def test_frontmatter_fields_present() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    frontmatter = _view("today", index).frontmatter()
    assert frontmatter["type"] == "view"
    assert frontmatter["generated"] is True
    assert frontmatter["generator"] == "obsidian-operator"
    assert frontmatter["view"] == "today"
    assert frontmatter["generated_at"] == GENERATED_AT
    assert frontmatter["reference_date"] == TODAY.isoformat()
    assert frontmatter["source_count"] == len(frontmatter["sources"])


def test_sources_reference_real_entities() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    known = {entity.path for entity in index.entities}
    for name in ("today", "projects", "team", "tickets", "waiting", "manager-review"):
        view = _view(name, index)
        for source in view.sources:
            assert source in known, f"{name} cites unknown source {source}"


def test_today_view_matches_review_content() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    view = _view("today", index)
    assert "# Today" in view.body
    assert "manager_attention" in view.body


def test_manager_review_only_high_severity() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    view = _view("manager-review", index)
    assert "[high]" in view.body
    assert "[medium]" not in view.body
    assert "[low]" not in view.body


def test_reproducible_with_pinned_inputs() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    first = {name: _view(name, index).to_markdown() for name in VIEWS}
    second = {name: _view(name, index).to_markdown() for name in VIEWS}
    assert first == second
