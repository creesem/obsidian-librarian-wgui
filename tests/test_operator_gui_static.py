"""Static-shell tests for the operator GUI."""

from __future__ import annotations

from pathlib import Path

HTML = Path("src/obsidian_operator/gui/static/index.html").read_text(encoding="utf-8")


def test_static_shell_has_required_sections() -> None:
    for label in [
        "Today",
        "Projects",
        "Team",
        "Tickets",
        "Waiting",
        "Manager Review",
        "Views",
    ]:
        assert label in HTML
    for label in ["Preview", "Generate views", "Change Set", "Equivalent CLI"]:
        assert label in HTML
    assert "obsidian-operator" in HTML


def test_static_shell_has_no_external_assets() -> None:
    assert "<script src=" not in HTML
    assert "<link href=" not in HTML
    assert "fonts.googleapis" not in HTML
    assert "cdn" not in HTML.lower()
