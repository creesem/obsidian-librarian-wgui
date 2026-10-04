"""Read-only repository and relationship resolution tests."""

from __future__ import annotations

from pathlib import Path

from obsidian_operator.repository import OperatorIndex

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"


def test_counts_by_type() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    assert index.counts() == {
        "action": 2,
        "meeting": 1,
        "person": 3,
        "project": 3,
        "ticket": 2,
    }


def test_get_resolves_by_title() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    entity = index.get("project", "CareLogic Automation")
    assert entity is not None
    assert entity.entity_type.value == "project"


def test_get_resolves_by_alias() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    entity = index.get("person", "Venkat R.")
    assert entity is not None
    assert entity.title == "Venkat Rao"


def test_get_rejects_wrong_type() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    assert index.get("ticket", "CareLogic Automation") is None


def test_resolve_unresolved_target_is_none() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    assert index.resolve("Nobody Here") is None


def test_stable_ordering_across_builds() -> None:
    first = OperatorIndex.from_vault(FIXTURE)
    second = OperatorIndex.from_vault(FIXTURE)
    assert [e.path for e in first.entities] == [e.path for e in second.entities]
    assert first.issues == second.issues


def test_duplicate_title_excluded_from_lookup(tmp_path: Path) -> None:
    notes = tmp_path / "Notes"
    notes.mkdir(parents=True)
    body = "---\ntype: person\nstatus: active\n---\n# Alex Rivera\n"
    (notes / "a.md").write_text(body, encoding="utf-8")
    (notes / "b.md").write_text(body, encoding="utf-8")

    index = OperatorIndex.from_vault(tmp_path)
    duplicates = [issue for issue in index.issues if issue.rule == "duplicate"]
    assert len(duplicates) == 1
    assert index.resolve("Alex Rivera") is None
