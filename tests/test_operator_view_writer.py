"""Containment and overwrite tests for the first operator write path."""

from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_operator.views import GeneratedView
from obsidian_operator.writer import ViewWriteError, ensure_under, write_view


def _view(name: str = "today", body: str = "# Today\n\n- items: 0") -> GeneratedView:
    return GeneratedView(
        name=name,
        filename="Today.md",
        title="Today",
        body=body,
        sources=(),
        generated_at="2026-10-03T12:00:00+00:00",
        reference_date="2026-10-10",
    )


def test_ensure_under_allows_descendant(tmp_path: Path) -> None:
    target = tmp_path / "90_Staging" / "Views" / "Today.md"
    assert ensure_under(tmp_path, target) == target.resolve(strict=False)


def test_ensure_under_refuses_outside(tmp_path: Path) -> None:
    with pytest.raises(ViewWriteError):
        ensure_under(tmp_path, tmp_path.parent / "outside.md")


def test_ensure_under_refuses_parent_traversal(tmp_path: Path) -> None:
    with pytest.raises(ViewWriteError):
        ensure_under(tmp_path, tmp_path / ".." / "outside.md")


def test_ensure_under_refuses_absolute_outside(tmp_path: Path) -> None:
    with pytest.raises(ViewWriteError):
        ensure_under(tmp_path / "vault", Path("C:/definitely/outside.md"))


def test_write_view_creates_under_root(tmp_path: Path) -> None:
    views_root = tmp_path / "90_Staging" / "Views"
    result = write_view(views_root, tmp_path, _view())

    expected = (views_root / "Today.md").resolve(strict=False)
    assert result.path == expected
    assert result.created is True
    assert result.overwritten is False
    assert expected.read_text(encoding="utf-8").startswith("---\n")


def test_write_view_refuses_views_root_equal_to_vault(tmp_path: Path) -> None:
    with pytest.raises(ViewWriteError):
        write_view(tmp_path, tmp_path, _view())


def test_write_view_refuses_out_of_vault_out(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside_views"
    with pytest.raises(ViewWriteError):
        write_view(outside, tmp_path, _view())
    assert not (outside / "Today.md").exists()


def test_write_view_refuses_overwrite_without_force(tmp_path: Path) -> None:
    views_root = tmp_path / "90_Staging" / "Views"
    write_view(views_root, tmp_path, _view(body="# first"))

    with pytest.raises(FileExistsError):
        write_view(views_root, tmp_path, _view(body="# second"))

    assert "# first" in (views_root / "Today.md").read_text(encoding="utf-8")


def test_write_view_overwrites_with_force(tmp_path: Path) -> None:
    views_root = tmp_path / "90_Staging" / "Views"
    write_view(views_root, tmp_path, _view(body="# first"))

    result = write_view(views_root, tmp_path, _view(body="# second"), force=True)

    assert result.created is False
    assert result.overwritten is True
    assert "# second" in (views_root / "Today.md").read_text(encoding="utf-8")


def test_write_view_creates_parent_dirs(tmp_path: Path) -> None:
    views_root = tmp_path / "90_Staging" / "Views" / "nested"
    write_view(views_root, tmp_path, _view())
    assert (views_root / "Today.md").exists()
