"""Prove operator commands do not modify the vault except through the contained view writer."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from obsidian_operator.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"
TODAY = ["--today", "2026-10-10"]
GENERATED_AT = ["--generated-at", "2026-10-03T12:00:00+00:00"]


def _snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_read_only_commands_leave_vault_unchanged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = _snapshot(FIXTURE)

    commands = [
        ["project", "list", "--vault", str(FIXTURE)],
        ["person", "list", "--vault", str(FIXTURE)],
        ["ticket", "list", "--vault", str(FIXTURE), "--json"],
        ["action", "list", "--vault", str(FIXTURE)],
        ["project", "show", "CareLogic Automation", "--vault", str(FIXTURE)],
        ["ticket", "show", "SD-31814", "--vault", str(FIXTURE)],
    ]
    for argv in commands:
        main(argv)
        capsys.readouterr()

    assert _snapshot(FIXTURE) == before


def test_view_render_without_write_leaves_vault_unchanged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = _snapshot(FIXTURE)

    exit_code = main(["view", "render", "--all", "--vault", str(FIXTURE), *TODAY, *GENERATED_AT])
    capsys.readouterr()

    assert exit_code == 1
    assert _snapshot(FIXTURE) == before


def test_view_write_does_not_touch_canonical_notes(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURE, vault)
    canonical_before = _snapshot(vault)

    exit_code = main(
        ["view", "render", "--all", "--write", "--vault", str(vault), *TODAY, *GENERATED_AT]
    )
    capsys.readouterr()

    assert exit_code == 1
    canonical_after = _snapshot(vault)
    assert set(canonical_after) - set(canonical_before) == {
        "90_Staging/Views/Manager Review.md",
        "90_Staging/Views/Projects.md",
        "90_Staging/Views/Team.md",
        "90_Staging/Views/Tickets Needing Attention.md",
        "90_Staging/Views/Today.md",
        "90_Staging/Views/Waiting on Others.md",
    }
    for path, value in canonical_before.items():
        assert canonical_after[path] == value
