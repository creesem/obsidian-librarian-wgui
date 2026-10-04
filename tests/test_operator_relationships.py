"""Relationship query tests over the fixture vault."""

from __future__ import annotations

from pathlib import Path

from obsidian_operator.relationships import Relationships, related_to
from obsidian_operator.repository import OperatorIndex

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"


def _titles(entities) -> set[str]:
    return {entity.title for entity in entities}


def test_project_relationships() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    project = index.get("project", "CareLogic Automation")
    assert project is not None

    relationships = related_to(index, project)
    assert _titles(relationships.people) == {"Alex Rivera", "Sam Okafor"}
    assert _titles(relationships.tickets) == {"SD-31814 — SureMobile sync failure"}
    assert _titles(relationships.actions) == {"Chase vendor on interface scope"}
    assert _titles(relationships.meetings) == {"CareLogic vendor sync — 2026-10-02"}


def test_person_relationships_for_owner_of_action() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    person = index.get("person", "Sam Okafor")
    assert person is not None

    relationships = related_to(index, person)
    assert _titles(relationships.projects) == {"CareLogic Automation"}
    assert _titles(relationships.actions) == {
        "Chase vendor on interface scope",
        "Waiting Action",
    }
    assert _titles(relationships.meetings) == {"CareLogic vendor sync — 2026-10-02"}


def test_person_relationships_for_assignee() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    person = index.get("person", "Venkat Rao")
    assert person is not None

    relationships = related_to(index, person)
    assert _titles(relationships.tickets) == {"SD-31814 — SureMobile sync failure"}


def test_unresolved_person_link_is_not_a_relationship() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    project = index.get("project", "Unresolved Project")
    assert project is not None

    relationships = related_to(index, project)
    # owner resolves; the dangling "[[Nobody Here]]" person does not.
    assert _titles(relationships.people) == {"Alex Rivera"}


def test_ticket_has_no_direct_relationships() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    ticket = index.get("ticket", "SD-31814 — SureMobile sync failure")
    assert ticket is not None
    assert related_to(index, ticket) == Relationships()
