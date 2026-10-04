"""Service-layer tests for the operator GUI."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from obsidian_operator.gui.service import (
    entity_detail,
    overview,
    preview_view,
    project_board,
    render_view,
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


def _copy_vault(tmp_path: Path) -> Path:
    target = tmp_path / "vault"
    shutil.copytree(FIXTURE, target)
    return target


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_preview_view_writes_nothing(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    before = _snapshot(vault)
    payload = preview_view(
        vault, name="today", today=TODAY, generated_at="2026-10-03T12:00:00+00:00"
    )
    assert payload["view"] == "today"
    assert payload["markdown"].startswith("---\n")
    assert "type: view" in payload["markdown"]
    assert _snapshot(vault) == before


def test_preview_unknown_view_raises(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    with pytest.raises(ValueError, match="unknown view"):
        preview_view(vault, name="nope", today=TODAY, generated_at="2026-10-03T12:00:00+00:00")


def test_render_unconfirmed_writes_nothing(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    before = _snapshot(vault)
    result = render_view(
        {"vault": str(vault), "all_views": True, "today": "2026-10-10", "confirmed": False}
    )
    assert result["status"] == "needs_confirmation"
    assert result["executed"] is False
    assert result["safety_tier"] == "staging-write"
    assert "obsidian-operator" in result["equivalent_cli"]
    assert _snapshot(vault) == before


def test_render_confirmed_writes_only_views(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    canonical_before = {
        path: content
        for path, content in _snapshot(vault).items()
        if not path.startswith("90_Staging")
    }
    result = render_view(
        {
            "vault": str(vault),
            "all_views": True,
            "today": "2026-10-10",
            "generated_at": "2026-10-03T12:00:00+00:00",
            "confirmed": True,
        }
    )
    assert result["status"] == "ok"
    assert len(result["change_set"]) == 6
    assert all(entry["created"] for entry in result["change_set"])
    assert (vault / "90_Staging" / "Views" / "Today.md").exists()
    canonical_after = {
        path: content
        for path, content in _snapshot(vault).items()
        if not path.startswith("90_Staging")
    }
    assert canonical_after == canonical_before


def test_render_second_run_without_force_errors(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    request = {
        "vault": str(vault),
        "name": "today",
        "today": "2026-10-10",
        "generated_at": "2026-10-03T12:00:00+00:00",
        "confirmed": True,
    }
    render_view(request)
    second = render_view(request)
    assert second["status"] == "error"
    assert "already exists" in second["message"]


def test_render_force_overwrites(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    render_view(
        {
            "vault": str(vault),
            "name": "today",
            "today": "2026-10-10",
            "generated_at": "2026-10-03T12:00:00+00:00",
            "confirmed": True,
        }
    )
    second = render_view(
        {
            "vault": str(vault),
            "name": "today",
            "today": "2026-10-10",
            "generated_at": "2026-10-03T12:00:00+00:00",
            "confirmed": True,
            "force": True,
        }
    )
    assert second["status"] == "ok"
    assert second["change_set"][0]["overwritten"] is True


def test_render_out_escape_is_error(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    result = render_view(
        {
            "vault": str(vault),
            "name": "today",
            "out": "../escape",
            "today": "2026-10-10",
            "confirmed": True,
        }
    )
    assert result["status"] == "error"
    assert not (tmp_path / "escape").exists()
