"""Deterministic text and JSON rendering for operator queries."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from typing import Any

from obsidian_operator.models import EntityBase
from obsidian_operator.repository import OperatorIndex
from obsidian_operator.review import AttentionItem, PersonWorkload, ProjectReview
from obsidian_operator.validate import ValidationIssue

_SKIP_FIELDS = {"path", "title", "status", "aliases", "tags", "raw"}
_EMPTY_VALUES = (None, (), "", False)


def to_dict(entity: EntityBase) -> dict[str, Any]:
    """Return a JSON-serializable mapping for one entity."""
    data: dict[str, Any] = {
        "type": entity.entity_type.value,
        "title": entity.title,
        "status": entity.status,
        "path": entity.path,
    }
    if entity.aliases:
        data["aliases"] = list(entity.aliases)
    if entity.tags:
        data["tags"] = list(entity.tags)
    for field_info in dataclasses.fields(entity):
        if field_info.name in _SKIP_FIELDS:
            continue
        value = getattr(entity, field_info.name)
        if value in _EMPTY_VALUES:
            continue
        data[field_info.name] = list(value) if isinstance(value, tuple) else value
    return data


def issue_to_dict(issue: ValidationIssue) -> dict[str, Any]:
    """Return a JSON-serializable mapping for one validation issue."""
    return {
        "path": issue.path,
        "message": issue.message,
        "severity": issue.severity,
        "rule": issue.rule,
    }


def render_entity(entity: EntityBase) -> str:
    """Render one entity as deterministic text."""
    lines = [
        f"# {entity.title}",
        f"- type: {entity.entity_type.value}",
        f"- status: {entity.status or '(missing)'}",
        f"- path: {entity.path}",
    ]
    if entity.aliases:
        lines.append(f"- aliases: {', '.join(entity.aliases)}")
    if entity.tags:
        lines.append(f"- tags: {', '.join(entity.tags)}")
    for field_info in dataclasses.fields(entity):
        if field_info.name in _SKIP_FIELDS:
            continue
        value = getattr(entity, field_info.name)
        if value in _EMPTY_VALUES:
            continue
        rendered = ", ".join(value) if isinstance(value, tuple) else value
        lines.append(f"- {field_info.name}: {rendered}")
    return "\n".join(lines)


def render_list(entity_type: str, entities: Iterable[EntityBase]) -> str:
    """Render a list of entities of one type."""
    items = list(entities)
    lines = [f"# {entity_type} list", f"- count: {len(items)}"]
    for entity in items:
        lines.append(f"- {entity.title} (status={entity.status or 'missing'}, path={entity.path})")
    if not items:
        lines.append("- (none)")
    return "\n".join(lines)


def render_issues(issues: Iterable[ValidationIssue]) -> str:
    """Render validation issues as deterministic text."""
    items = list(issues)
    lines = [f"- issues: {len(items)}"]
    for issue in items:
        location = f"{issue.path}: " if issue.path else ""
        lines.append(f"  - [{issue.severity}] {location}{issue.message}")
    return "\n".join(lines)


def render_index_summary(index: OperatorIndex) -> str:
    """Render a compact summary of the whole operator index."""
    counts = index.counts()
    lines = ["# obsidian-operator", f"- root: {index.root}"]
    lines.extend(f"- {key}: {value}" for key, value in counts.items())
    lines.append(f"- issues: {len(index.issues)} ({len(index.errors)} errors)")
    return "\n".join(lines)


def attention_to_dict(item: AttentionItem) -> dict[str, Any]:
    """Return a JSON-serializable mapping for one attention item."""
    return {
        "kind": item.kind,
        "severity": item.severity,
        "entity_type": item.entity_type,
        "title": item.title,
        "path": item.path,
        "detail": item.detail,
    }


def project_review_to_dict(review: ProjectReview) -> dict[str, Any]:
    """Return a JSON-serializable mapping for a project review."""
    return {
        "project": to_dict(review.project),
        "people": [entity.title for entity in review.people],
        "tickets": [entity.title for entity in review.tickets],
        "actions": [entity.title for entity in review.actions],
        "meetings": [entity.title for entity in review.meetings],
        "attention": [attention_to_dict(item) for item in review.attention],
        "blockers": [attention_to_dict(item) for item in review.blockers],
    }


def workload_to_dict(workload: PersonWorkload) -> dict[str, Any]:
    """Return a JSON-serializable mapping for a person workload."""
    return {
        "person": to_dict(workload.person),
        "projects": [entity.title for entity in workload.projects],
        "tickets": [entity.title for entity in workload.tickets],
        "actions": [entity.title for entity in workload.actions],
        "meetings": [entity.title for entity in workload.meetings],
        "attention": [attention_to_dict(item) for item in workload.attention],
        "overdue": [attention_to_dict(item) for item in workload.overdue],
    }


def render_attention(title: str, items: Iterable[AttentionItem]) -> str:
    """Render an attention queue."""
    rendered = list(items)
    lines = [f"# {title}", f"- items: {len(rendered)}"]
    for item in rendered:
        lines.append(
            f"- [{item.severity}] {item.kind}: {item.title} ({item.path}) — {item.detail}"
        )
    if not rendered:
        lines.append("- (none)")
    return "\n".join(lines)


def render_project_review(review: ProjectReview) -> str:
    """Render one project's management rollup."""
    project = review.project
    lines = [
        f"# Project review: {project.title}",
        f"- status: {project.status or '-'}",
        f"- priority: {getattr(project, 'priority', None) or '-'}",
        f"- health: {getattr(project, 'health', None) or '-'}",
        f"- owner: {getattr(project, 'owner', None) or '-'}",
        f"- next action: {getattr(project, 'next_action', None) or '-'}",
        f"- last reviewed: {getattr(project, 'last_reviewed', None) or '-'}",
        f"- next review: {getattr(project, 'next_review', None) or '-'}",
        f"- people: {_titles(review.people)}",
        f"- tickets: {_titles(review.tickets)}",
        f"- actions: {_titles(review.actions)}",
        f"- meetings: {_titles(review.meetings)}",
        f"- blockers: {len(review.blockers)}",
    ]
    for blocker in review.blockers:
        lines.append(f"  - [{blocker.severity}] {blocker.kind}: {blocker.title} — {blocker.detail}")
    return "\n".join(lines)


def render_projects_review(reviews: Iterable[ProjectReview]) -> str:
    """Render the active-project review board."""
    rendered = list(reviews)
    lines = ["# Projects review", f"- projects: {len(rendered)}"]
    for review in rendered:
        project = review.project
        lines.append(
            f"## {project.title} "
            f"(health={getattr(project, 'health', None) or '-'}, "
            f"priority={getattr(project, 'priority', None) or '-'}, "
            f"owner={getattr(project, 'owner', None) or '-'})"
        )
        lines.append(
            f"- tickets: {_titles(review.tickets)} | actions: {_titles(review.actions)} "
            f"| blockers: {len(review.blockers)}"
        )
        for blocker in review.blockers:
            lines.append(
                f"  - [{blocker.severity}] {blocker.kind}: {blocker.title} — {blocker.detail}"
            )
    if not rendered:
        lines.append("- (none)")
    return "\n".join(lines)


def render_workload(workload: PersonWorkload) -> str:
    """Render one person's workload."""
    person = workload.person
    lines = [
        f"# Workload: {person.title}",
        f"- status: {person.status or '-'}",
        f"- role: {getattr(person, 'role', None) or '-'}",
        f"- projects: {_titles(workload.projects)}",
        f"- tickets: {_titles(workload.tickets)}",
        f"- actions: {_titles(workload.actions)}",
        f"- meetings: {_titles(workload.meetings)}",
        f"- overdue: {len(workload.overdue)}",
        f"- attention: {len(workload.attention)}",
    ]
    for item in workload.attention:
        lines.append(f"  - [{item.severity}] {item.kind}: {item.title} — {item.detail}")
    return "\n".join(lines)


def render_team_review(workloads: Iterable[PersonWorkload]) -> str:
    """Render the team workload board."""
    rendered = list(workloads)
    lines = ["# Team review", f"- people: {len(rendered)}"]
    for workload in rendered:
        person = workload.person
        lines.append(f"## {person.title} (role={getattr(person, 'role', None) or '-'})")
        lines.append(
            f"- projects: {_titles(workload.projects)} | tickets: {_titles(workload.tickets)} "
            f"| actions: {_titles(workload.actions)} | attention: {len(workload.attention)}"
        )
        for item in workload.attention:
            lines.append(f"  - [{item.severity}] {item.kind}: {item.title} — {item.detail}")
    if not rendered:
        lines.append("- (none)")
    return "\n".join(lines)


def _titles(entities: Iterable[EntityBase]) -> str:
    names = [entity.title for entity in entities]
    return ", ".join(names) if names else "-"
