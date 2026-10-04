"""Guard the GUI boundary: gui imports only operator + stdlib."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import obsidian_operator.gui

_FORBIDDEN = ("obsidian_librarian", "obsidian_patron")


def test_gui_sources_do_not_reference_binary_packages() -> None:
    package_dir = Path(obsidian_operator.gui.__file__).parent
    for source in package_dir.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN:
            assert forbidden not in text, f"{source.name} references {forbidden}"


def test_importing_gui_does_not_load_binaries() -> None:
    code = (
        "import sys, obsidian_operator.gui.server; "
        "assert 'obsidian_librarian' not in sys.modules, 'librarian imported'; "
        "assert 'obsidian_patron' not in sys.modules, 'patron imported'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
