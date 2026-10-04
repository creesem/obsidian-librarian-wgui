"""CLI tests for `obsidian-operator view`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from obsidian_operator.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"
TODAY = ["--today", "2026-10-10"]
GENERATED_AT = ["--generated-at", "2026-10-03T12:00:00+00:00"]


def _copy_vault(tmp_path: Path) -> Path:
    import shutil

    target = tmp_path / "vault"
    shutil.copytree(FIXTURE, target)
    return target


def test_view_list(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["view", "list", "--vault", str(FIXTURE)])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert out.splitlines() == [
        "today",
        "projects",
        "team",
        "tickets",
        "waiting",
        "manager-review",
    ]


def test_view_render_one_prints_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        ["view", "render", "today", "--vault", str(FIXTURE), *TODAY, *GENERATED_AT]
    )
    out = capsys.readouterr().out
    assert exit_code == 1
    assert out.startswith("---\n")
    assert "type: view" in out
    assert "# Today" in out


def test_view_render_stdout_writes_nothing(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    vault = _copy_vault(tmp_path)
    main(["view", "render", "--all", "--vault", str(vault), *TODAY, *GENERATED_AT])
    capsys.readouterr()
    assert not (vault / "90_Staging").exists()


def test_view_render_write_creates_files(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    vault = _copy_vault(tmp_path)
    exit_code = main(
        ["view", "render", "--all", "--write", "--vault", str(vault), *TODAY, *GENERATED_AT]
    )
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "created: " in out
    views_root = vault / "90_Staging" / "Views"
    assert (views_root / "Today.md").exists()
    assert (views_root / "Manager Review.md").exists()


def test_view_render_refuses_overwrite_without_force(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    vault = _copy_vault(tmp_path)
    main(["view", "render", "today", "--write", "--vault", str(vault), *TODAY, *GENERATED_AT])
    capsys.readouterr()

    exit_code = main(
        ["view", "render", "today", "--write", "--vault", str(vault), *TODAY, *GENERATED_AT]
    )
    assert exit_code == 2
    assert "already exists" in capsys.readouterr().out


def test_view_render_force_overwrites(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    main(["view", "render", "today", "--write", "--vault", str(vault), *TODAY, *GENERATED_AT])
    capsys.readouterr()

    exit_code = main(
        [
            "view",
            "render",
            "today",
            "--write",
            "--force",
            "--vault",
            str(vault),
            *TODAY,
            *GENERATED_AT,
        ]
    )
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "overwritten: " in out


def test_view_render_out_escape_is_refused(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    vault = _copy_vault(tmp_path)
    exit_code = main(
        [
            "view",
            "render",
            "today",
            "--write",
            "--out",
            "../escape",
            "--vault",
            str(vault),
            *TODAY,
            *GENERATED_AT,
        ]
    )
    assert exit_code == 2
    assert "escapes the vault" in capsys.readouterr().out


def test_view_render_unknown_view_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["view", "render", "nope", "--vault", str(FIXTURE), *TODAY, *GENERATED_AT])
    assert exit_code == 2
    assert "unknown view" in capsys.readouterr().out


def test_view_render_all_with_name_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        ["view", "render", "today", "--all", "--vault", str(FIXTURE), *TODAY, *GENERATED_AT]
    )
    assert exit_code == 2
    assert "cannot combine" in capsys.readouterr().out


def test_view_render_invalid_today_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        ["view", "render", "today", "--vault", str(FIXTURE), "--today", "not-a-date"]
    )
    assert exit_code == 2
    assert "invalid --today" in capsys.readouterr().out


def test_view_render_invalid_generated_at_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "view",
            "render",
            "today",
            "--vault",
            str(FIXTURE),
            *TODAY,
            "--generated-at",
            "nope",
        ]
    )
    assert exit_code == 2
    assert "invalid --generated-at" in capsys.readouterr().out


def test_view_render_json_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        ["view", "render", "--all", "--vault", str(FIXTURE), *TODAY, *GENERATED_AT, "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["write"] is False
    assert {view["view"] for view in payload["views"]} == {
        "today",
        "projects",
        "team",
        "tickets",
        "waiting",
        "manager-review",
    }


def test_view_render_write_json_reports_change_set(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    vault = _copy_vault(tmp_path)
    exit_code = main(
        [
            "view",
            "render",
            "--all",
            "--write",
            "--vault",
            str(vault),
            *TODAY,
            *GENERATED_AT,
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["write"] is True
    assert all(entry["created"] for entry in payload["change_set"])
    assert len(payload["change_set"]) == 6


def test_view_without_subcommand_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["view"]) == 0
    assert "view" in capsys.readouterr().out
