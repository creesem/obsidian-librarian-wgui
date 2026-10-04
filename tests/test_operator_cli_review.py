"""CLI tests for the Phase 2 review and rollup commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from obsidian_operator.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"
TODAY_ARGS = ["--today", "2026-10-10"]


def test_review_today(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["review", "today", "--vault", str(FIXTURE), *TODAY_ARGS])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "# Today" in out
    assert "manager_attention" in out


def test_review_today_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["review", "today", "--vault", str(FIXTURE), *TODAY_ARGS, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["view"] == "today"
    assert payload["items"]
    assert {"kind", "severity", "title", "path"} <= set(payload["items"][0])


def test_review_projects(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["review", "projects", "--vault", str(FIXTURE), *TODAY_ARGS])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "# Projects review" in out
    assert "CareLogic Automation" in out


def test_review_team(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["review", "team", "--vault", str(FIXTURE), *TODAY_ARGS])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "# Team review" in out
    assert "Sam Okafor" in out


def test_project_review(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        ["project", "review", "CareLogic Automation", "--vault", str(FIXTURE), *TODAY_ARGS]
    )
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "# Project review: CareLogic Automation" in out
    assert "blockers:" in out


def test_project_review_json(capsys: pytest.CaptureFixture[str]) -> None:
    main(
        [
            "project",
            "review",
            "CareLogic Automation",
            "--vault",
            str(FIXTURE),
            *TODAY_ARGS,
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["project"]["title"] == "CareLogic Automation"
    assert payload["blockers"]


def test_person_workload(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["person", "workload", "Sam Okafor", "--vault", str(FIXTURE), *TODAY_ARGS])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "# Workload: Sam Okafor" in out
    assert "overdue: 1" in out


def test_project_review_unknown_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["project", "review", "Nope", "--vault", str(FIXTURE)]) == 2
    assert "no project found" in capsys.readouterr().out


def test_invalid_today_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["review", "today", "--vault", str(FIXTURE), "--today", "not-a-date"])
    assert exit_code == 2
    assert "invalid --today" in capsys.readouterr().out


def test_review_without_view_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["review"]) == 0
    assert "review" in capsys.readouterr().out
