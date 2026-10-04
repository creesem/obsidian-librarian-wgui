"""Validation rule tests for operational entities."""

from __future__ import annotations

from pathlib import Path

from obsidian_operator.models import Action, Project, Ticket
from obsidian_operator.repository import OperatorIndex
from obsidian_operator.validate import has_errors, validate_entity

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"


def _rules(issues) -> set[str]:
    return {issue.rule for issue in issues}


def test_valid_project_has_no_issues() -> None:
    project = Project(
        path="P.md",
        title="P",
        status="active",
        owner="[[Alex Rivera]]",
        priority="P1",
        health="green",
    )
    assert validate_entity(project) == []


def test_missing_status_is_required_error() -> None:
    project = Project(
        path="P.md", title="P", status="", owner="[[A]]", priority="P1", health="green"
    )
    issues = validate_entity(project)
    assert has_errors(issues)
    assert "required" in _rules(issues)


def test_invalid_health_is_enum_error() -> None:
    project = Project(
        path="P.md",
        title="P",
        status="active",
        owner="[[A]]",
        priority="P1",
        health="purple",
    )
    issues = validate_entity(project)
    assert any(issue.rule == "enum" and "health" in issue.message for issue in issues)


def test_reference_ticket_requires_external_id() -> None:
    ticket = Ticket(
        path="T.md",
        title="T",
        status="open",
        source_system="servicedesk-plus",
        sync_mode="reference",
    )
    issues = validate_entity(ticket)
    assert any(issue.rule == "conditional" and "external_id" in issue.message for issue in issues)


def test_waiting_action_requires_waiting_on() -> None:
    action = Action(path="A.md", title="A", status="waiting")
    issues = validate_entity(action)
    assert any(issue.rule == "conditional" and "waiting_on" in issue.message for issue in issues)


def test_done_action_requires_completed() -> None:
    action = Action(path="A.md", title="A", status="done")
    issues = validate_entity(action)
    assert any(issue.rule == "conditional" and "completed" in issue.message for issue in issues)


def test_next_review_before_last_reviewed_is_error() -> None:
    project = Project(
        path="P.md",
        title="P",
        status="active",
        owner="[[A]]",
        priority="P1",
        health="green",
        last_reviewed="2026-10-10",
        next_review="2026-10-01",
    )
    issues = validate_entity(project)
    assert any(issue.rule == "date_order" for issue in issues)


def test_malformed_note_does_not_abort_and_is_reported() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    malformed = [issue for issue in index.issues if issue.rule == "malformed"]
    assert len(malformed) == 1
    assert malformed[0].path == "Broken/Malformed.md"
    # Valid entities are still indexed alongside the malformed note.
    assert index.get("project", "CareLogic Automation") is not None


def test_unresolved_link_is_warning() -> None:
    index = OperatorIndex.from_vault(FIXTURE)
    warnings = [issue for issue in index.issues if issue.rule == "unresolved_link"]
    assert any("nobody here" in issue.message.casefold() for issue in warnings)
    assert all(issue.severity == "warning" for issue in warnings)
