"""Service layer for the operator GUI.

Pure functions over the operator index. No HTTP knowledge, no business rules:
every result is built from existing obsidian_operator services.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from obsidian_operator.dates import parse_iso_date
from obsidian_operator.relationships import related_to
from obsidian_operator.render import (
    attention_to_dict,
    issue_to_dict,
    project_review_to_dict,
    to_dict,
    workload_to_dict,
)
from obsidian_operator.repository import OperatorIndex
from obsidian_operator.review import (
    active_people,
    active_projects,
    attention_items,
    build_person_workload,
    build_project_review,
)
from obsidian_operator.views import VIEWS, GeneratedView, build_view
from obsidian_operator.writer import ViewWriteError, write_view


def _load_index(vault: str | Path) -> OperatorIndex:
    return OperatorIndex.from_vault(vault)


def overview(vault: str | Path, *, today: date) -> dict[str, Any]:
    """Return index counts and validation issues for the vault."""
    index = _load_index(vault)
    return {
        "vault": str(index.root),
        "counts": index.counts(),
        "issue_count": len(index.issues),
        "error_count": len(index.errors),
        "issues": [issue_to_dict(issue) for issue in index.issues],
    }


def today(vault: str | Path, *, today: date) -> dict[str, Any]:
    """Return the attention queue."""
    index = _load_index(vault)
    items = attention_items(index, today)
    return {"view": "today", "items": [attention_to_dict(item) for item in items]}


def project_board(vault: str | Path, *, today: date) -> dict[str, Any]:
    """Return per-active-project rollups."""
    index = _load_index(vault)
    reviews = [build_project_review(index, project, today) for project in active_projects(index)]
    return {"view": "projects", "projects": [project_review_to_dict(r) for r in reviews]}


def team_board(vault: str | Path, *, today: date) -> dict[str, Any]:
    """Return per-active-person rollups."""
    index = _load_index(vault)
    workloads = [build_person_workload(index, person, today) for person in active_people(index)]
    return {"view": "team", "people": [workload_to_dict(w) for w in workloads]}


def entity_detail(
    vault: str | Path,
    *,
    entity_type: str,
    name: str,
    today: date,
) -> dict[str, Any]:
    """Return one entity with its relationships and issues."""
    index = _load_index(vault)
    entity = index.get(entity_type, name)
    if entity is None:
        raise ValueError(f"no {entity_type} found matching '{name}'")
    relationships = related_to(index, entity)
    related = [issue for issue in index.issues if issue.path == entity.path]
    return {
        "entity": to_dict(entity),
        "relationships": {
            "people": [e.title for e in relationships.people],
            "projects": [e.title for e in relationships.projects],
            "tickets": [e.title for e in relationships.tickets],
            "actions": [e.title for e in relationships.actions],
            "meetings": [e.title for e in relationships.meetings],
        },
        "issues": [issue_to_dict(issue) for issue in related],
    }


def view_definitions() -> list[dict[str, Any]]:
    """Return the generated-view definitions."""
    return [
        {"name": definition.name, "filename": definition.filename, "title": definition.title}
        for definition in VIEWS.values()
    ]


STAGING_WRITE = "staging-write"


def _view_names(name: str | None, all_views: bool) -> list[str]:
    if all_views:
        return list(VIEWS)
    if name is None or name not in VIEWS:
        raise ValueError(f"unknown view: {name if name is not None else '(none)'}")
    return [name]


def _resolve_today(value: str | None) -> date:
    if value is None:
        return date.today()
    parsed = parse_iso_date(value)
    if parsed is None:
        raise ValueError(f"invalid today date: {value}")
    return parsed.date()


def _resolve_generated_at(value: str | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    if parse_iso_date(value) is None:
        raise ValueError(f"invalid generated_at timestamp: {value}")
    return value


def _resolve_views_root(vault: Path, out: str | None) -> Path:
    resolved_vault = vault.expanduser().resolve(strict=False)
    if out is None:
        return resolved_vault / "90_Staging" / "Views"
    candidate = Path(out)
    if candidate.is_absolute():
        raise ValueError(f"out must be relative to the vault: {out}")
    resolved = (resolved_vault / candidate).expanduser().resolve(strict=False)
    if not resolved.is_relative_to(resolved_vault):
        raise ValueError(f"out escapes the vault: {out}")
    return resolved


def _equivalent_cli(names: list[str], vault: str, out: str | None, force: bool) -> str:
    argv = ["obsidian-operator", "view", "render"]
    if len(names) == len(VIEWS):
        argv.append("--all")
    else:
        argv.append(names[0])
    argv.extend(["--write", "--vault", vault])
    if out:
        argv.extend(["--out", out])
    if force:
        argv.append("--force")
    return subprocess.list2cmdline(argv)


def _view_to_buildable(name: str, index: OperatorIndex, today: date, generated_at: str):
    return build_view(name, index, today=today, generated_at=generated_at)


def preview_view(
    vault: str | Path,
    *,
    name: str,
    today: date,
    generated_at: str,
) -> dict[str, Any]:
    """Render one view for preview without writing anything."""
    if name not in VIEWS:
        raise ValueError(f"unknown view: {name}")
    index = _load_index(vault)
    view = build_view(name, index, today=today, generated_at=generated_at)
    return {"view": name, "markdown": view.to_markdown()}


def render_view(request: dict[str, Any]) -> dict[str, Any]:
    """Write views through the contained writer, gated by confirmation."""
    vault_value = str(request.get("vault") or ".")
    vault = Path(vault_value).expanduser()
    out = request.get("out")
    force = bool(request.get("force"))
    confirmed = bool(request.get("confirmed"))

    try:
        names = _view_names(request.get("name"), bool(request.get("all_views")))
        command = _equivalent_cli(names, str(vault), out if isinstance(out, str) else None, force)
    except ValueError as exc:
        return {
            "status": "error",
            "executed": False,
            "safety_tier": STAGING_WRITE,
            "equivalent_cli": "",
            "message": str(exc),
            "change_set": [],
        }

    if not confirmed:
        return {
            "status": "needs_confirmation",
            "executed": False,
            "safety_tier": STAGING_WRITE,
            "equivalent_cli": command,
            "change_set": [],
        }

    try:
        today = _resolve_today(request.get("today"))
        generated_at = _resolve_generated_at(request.get("generated_at"))
        views_root = _resolve_views_root(vault, out if isinstance(out, str) else None)
        index = _load_index(vault)
        views: list[GeneratedView] = [
            build_view(name, index, today=today, generated_at=generated_at) for name in names
        ]
    except (ValueError, FileNotFoundError, NotADirectoryError, OSError) as exc:
        return {
            "status": "error",
            "executed": False,
            "safety_tier": STAGING_WRITE,
            "equivalent_cli": command,
            "message": str(exc),
            "change_set": [],
        }

    change_set: list[dict[str, Any]] = []
    for view in views:
        try:
            result = write_view(views_root, vault, view, force=force)
        except (ViewWriteError, FileExistsError, OSError) as exc:
            return {
                "status": "error",
                "executed": False,
                "safety_tier": STAGING_WRITE,
                "equivalent_cli": command,
                "message": str(exc),
                "change_set": change_set,
            }
        change_set.append(
            {
                "view": view.name,
                "path": result.path.as_posix(),
                "created": result.created,
                "overwritten": result.overwritten,
            }
        )

    return {
        "status": "ok",
        "executed": True,
        "safety_tier": STAGING_WRITE,
        "equivalent_cli": command,
        "change_set": change_set,
    }
