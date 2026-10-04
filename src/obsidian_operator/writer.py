"""Contained, opt-in writer for generated management views.

The operator's first write path. Writes are confined to a views root that must
itself sit strictly under the vault, existing targets are refused unless forced,
and no canonical note is ever touched. ``ensure_under`` is a small operator-local
containment helper, so the package keeps its one-way dependency on
``obsidian_inventory``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from obsidian_operator.views import GeneratedView


class ViewWriteError(ValueError):
    """Raised when a view write would escape its allowed root."""


@dataclass(frozen=True)
class WriteResult:
    """The outcome of one view write."""

    path: Path
    created: bool
    overwritten: bool


def ensure_under(root: Path, target: Path) -> Path:
    """Resolve ``target`` and refuse it when it escapes ``root``.

    Absolute paths outside the root and paths that traverse out via ``..`` are
    refused after resolution. The resolved path is returned.
    """
    root_resolved = Path(root).expanduser().resolve(strict=False)
    target_resolved = Path(target).expanduser().resolve(strict=False)
    if not target_resolved.is_relative_to(root_resolved):
        raise ViewWriteError(f"Refusing write outside allowed root: {target_resolved}")
    return target_resolved


def write_view(
    views_root: Path,
    vault_root: Path,
    view: GeneratedView,
    *,
    force: bool = False,
) -> WriteResult:
    """Write one generated view under ``views_root`` (itself under ``vault_root``).

    Double containment is enforced: the views root must sit strictly under the
    vault, and the target file must sit under the views root. An existing target
    is refused unless ``force`` is true. Parent directories are created; nothing
    is ever deleted.
    """
    vault = Path(vault_root).expanduser().resolve(strict=False)
    views = Path(views_root).expanduser().resolve(strict=False)
    if views == vault:
        raise ViewWriteError("Refusing to use the vault root as the views root")
    root = ensure_under(vault, views)
    target = ensure_under(root, root / view.filename)

    exists = target.exists()
    if exists and not force:
        raise FileExistsError(f"View already exists (use --force to overwrite): {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(view.to_markdown(), encoding="utf-8")
    return WriteResult(path=target, created=not exists, overwritten=exists)
