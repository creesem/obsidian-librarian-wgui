"""Service-layer tests for the operator GUI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from obsidian_operator.gui.service import (
    entity_detail,
    overview,
    project_board,
    team_board,
    today,
    view_definitions,
)

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"
TODAY = date(2026, 10, 10)


def test_overview_reports_counts_and_issues() -> None:
    payload = overview(FIXTURE, today=TODAY)
    assert payload["vault"].endswith("operator_vault")
    assert payload["counts"]["project"] == 3
    assert payload["error_count"] >= 1
    assert any(key == "issues" for key in payload)


def test_today_returns_attention_items() -> None:
    payload = today(FIXTURE, today=TODAY)
    assert payload["view"] == "today"
    assert payload["items"]
    assert {"kind", "severity", "title", "path"} <= set(payload["items"][0])


def test_project_board_lists_active_projects() -> None:
    payload = project_board(FIXTURE, today=TODAY)
    assert payload["view"] == "projects"
    titles = {project["project"]["title"] for project in payload["projects"]}
    assert "CareLogic Automation" in titles


def test_team_board_lists_active_people() -> None:
    payload = team_board(FIXTURE, today=TODAY)
    assert payload["view"] == "team"
    titles = {person["person"]["title"] for person in payload["people"]}
    assert {"Sam Okafor", "Alex Rivera", "Venkat Rao"} <= titles


def test_entity_detail_includes_relationships() -> None:
    payload = entity_detail(
        FIXTURE, entity_type="project", name="CareLogic Automation", today=TODAY
    )
    assert payload["entity"]["title"] == "CareLogic Automation"
    assert "tickets" in payload["relationships"]


def test_entity_detail_unknown_raises() -> None:
    with pytest.raises(ValueError, match="no project found"):
        entity_detail(FIXTURE, entity_type="project", name="Nope", today=TODAY)


def test_view_definitions_lists_six_views() -> None:
    definitions = view_definitions()
    assert {d["name"] for d in definitions} == {
        "today",
        "projects",
        "team",
        "tickets",
        "waiting",
        "manager-review",
    }
    assert all({"name", "filename", "title"} <= set(d) for d in definitions)
