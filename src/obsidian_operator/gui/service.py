"""Service layer for the operator GUI.

Pure functions over the operator index. No HTTP knowledge, no business rules:
every result is built from existing obsidian_operator services.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

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
from obsidian_operator.views import VIEWS


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
