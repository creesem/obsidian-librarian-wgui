"""Attention and rollup rule tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from obsidian_operator.models import Action, Person, Project, Ticket
from obsidian_operator.repository import OperatorIndex
from obsidian_operator.review import (
    AttentionKind,
    attention_items,
    build_person_workload,
    build_project_review,
)

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"
TODAY = date(2026, 10, 10)


def _index(*entities) -> OperatorIndex:
    return OperatorIndex.from_entities(entities)


def _kinds(items) -> set[str]:
    return {item.kind for item in items}


def test_blocked_project_is_high_attention() -> None:
    index = _index(Project(path="p.md", title="P", status="blocked"))
    items = attention_items(index, TODAY)
    assert AttentionKind.BLOCKED.value in _kinds(items)
    assert items[0].severity == "high"


def test_project_review_due() -> None:
    project = Project(
        path="p.md",
        title="P",
        status="active",
        next_review="2026-10-06",
        last_reviewed="2026-10-03",
    )
    items = attention_items(_index(project), TODAY)
    assert AttentionKind.REVIEW_DUE.value in _kinds(items)


def test_project_never_reviewed_is_stale() -> None:
    project = Project(path="p.md", title="P", status="active")
    items = attention_items(_index(project), TODAY)
    assert AttentionKind.STALE_REVIEW.value in _kinds(items)


def test_recently_reviewed_project_is_not_stale() -> None:
    project = Project(path="p.md", title="P", status="active", last_reviewed="2026-10-09")
    items = attention_items(_index(project), TODAY)
    assert AttentionKind.STALE_REVIEW.value not in _kinds(items)


def test_manager_attention_ticket() -> None:
    ticket = Ticket(path="t.md", title="T", status="open", manager_attention=True)
    items = attention_items(_index(ticket), TODAY)
    assert AttentionKind.MANAGER_ATTENTION.value in _kinds(items)


def test_resolved_ticket_ignores_manager_attention_flag() -> None:
    ticket = Ticket(path="t.md", title="T", status="resolved", manager_attention=True)
    items = attention_items(_index(ticket), TODAY)
    assert AttentionKind.MANAGER_ATTENTION.value not in _kinds(items)


def test_waiting_ticket() -> None:
    ticket = Ticket(path="t.md", title="T", status="waiting", assignee="[[A]]")
    items = attention_items(_index(ticket), TODAY)
    assert AttentionKind.WAITING.value in _kinds(items)


def test_unassigned_open_ticket() -> None:
    ticket = Ticket(path="t.md", title="T", status="open")
    items = attention_items(_index(ticket), TODAY)
    assert AttentionKind.UNASSIGNED_TICKET.value in _kinds(items)


def test_overdue_action() -> None:
    action = Action(path="a.md", title="A", status="open", due="2026-10-01")
    items = attention_items(_index(action), TODAY)
    assert AttentionKind.OVERDUE_ACTION.value in _kinds(items)
    assert items[0].severity == "high"


def test_completed_action_has_no_attention() -> None:
    action = Action(path="a.md", title="A", status="done", due="2026-10-01", completed="2026-10-02")
    assert attention_items(_index(action), TODAY) == ()


def test_attention_sorted_by_severity() -> None:
    blocked = Project(path="a.md", title="A", status="blocked")
    stale = Project(path="b.md", title="B", status="active")
    unassigned = Ticket(path="c.md", title="C", status="open")
    items = attention_items(_index(blocked, stale, unassigned), TODAY)
    severities = [item.severity for item in items]
    rank = {"high": 0, "medium": 1, "low": 2}
    assert severities == sorted(severities, key=lambda value: rank[value])


def test_project_review_blockers_from_related_items() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    project = index.get("project", "CareLogic Automation")
    assert project is not None
    review = build_project_review(index, project, TODAY)
    blocker_kinds = {item.kind for item in review.blockers}
    assert AttentionKind.MANAGER_ATTENTION.value in blocker_kinds
    assert AttentionKind.OVERDUE_ACTION.value in blocker_kinds


def test_person_workload_overdue() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    person = index.get("person", "Sam Okafor")
    assert person is not None
    workload = build_person_workload(index, person, TODAY)
    assert {item.kind for item in workload.overdue} == {AttentionKind.OVERDUE_ACTION.value}


def test_fixture_today_queue_has_expected_kinds() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    kinds = _kinds(attention_items(index, TODAY))
    assert {
        AttentionKind.REVIEW_DUE.value,
        AttentionKind.MANAGER_ATTENTION.value,
        AttentionKind.WAITING.value,
        AttentionKind.OVERDUE_ACTION.value,
        AttentionKind.UNASSIGNED_TICKET.value,
        AttentionKind.STALE_REVIEW.value,
    } <= kinds


def test_person_entity_used_in_index_is_typed() -> None:
    person = Person(path="p.md", title="P", status="active")
    index = _index(person)
    assert index.get("person", "P") is person
