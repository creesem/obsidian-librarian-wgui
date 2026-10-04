"""CLI tests for obsidian-operator (read-only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from obsidian_operator.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"


def test_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "obsidian-operator" in capsys.readouterr().out


def test_project_list_reports_entities(capsys: pytest.CaptureFixture[str]) -> None:
    # Fixture contains validation errors, so the command exits 1 but still lists.
    exit_code = main(["project", "list", "--vault", str(FIXTURE)])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "count: 3" in out
    assert "CareLogic Automation" in out


def test_show_project_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["project", "show", "CareLogic Automation", "--vault", str(FIXTURE)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "owner: [[Alex Rivera]]" in out


def test_show_unknown_entity_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["project", "show", "Does Not Exist", "--vault", str(FIXTURE)]) == 2
    assert "no project found" in capsys.readouterr().out


def test_missing_vault_returns_2(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    assert main(["project", "list", "--vault", str(missing)]) == 2
    assert "Error:" in capsys.readouterr().out


def test_json_output_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["ticket", "list", "--vault", str(FIXTURE), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["type"] == "ticket"
    assert payload["count"] == 2
    assert {entity["title"] for entity in payload["entities"]} == {
        "SD-31814 — SureMobile sync failure",
        "Bad Ticket",
    }


def test_empty_vault_lists_nothing(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["project", "list", "--vault", str(tmp_path)]) == 0
    assert "count: 0" in capsys.readouterr().out
