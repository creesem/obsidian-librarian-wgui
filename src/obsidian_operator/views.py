"""Generated management views.

A generated view is a reproducible Markdown document computed from the operator
index on demand. It is derived state: never canonical, never hand-edited, and
safe to regenerate. Bodies reuse the deterministic Phase 2 renderers; no new
business rules are introduced here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date

import yaml

from obsidian_operator.render import (
    render_attention,
    render_projects_review,
    render_team_review,
)
from obsidian_operator.repository import OperatorIndex
from obsidian_operator.review import (
    AttentionItem,
    AttentionKind,
    active_people,
    active_projects,
    attention_items,
    build_person_workload,
    build_project_review,
)

GENERATOR = "obsidian-operator"


@dataclass(frozen=True)
class ViewBody:
    """The rendered text of a view plus the entity paths it was derived from."""

    text: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class ViewDefinition:
    """A stable view name, its output filename, and its body builder."""

    name: str
    filename: str
    title: str
    build: Callable[[OperatorIndex, date], ViewBody]


@dataclass(frozen=True)
class GeneratedView:
    """A rendered view ready to print or write."""

    name: str
    filename: str
    title: str
    body: str
    sources: tuple[str, ...]
    generated_at: str
    reference_date: str

    @property
    def source_count(self) -> int:
        """Number of contributing entity paths."""
        return len(self.sources)

    def frontmatter(self) -> dict[str, object]:
        """Return the generated-provenance frontmatter as an ordered mapping."""
        return {
            "type": "view",
            "generated": True,
            "generator": GENERATOR,
            "view": self.name,
            "generated_at": self.generated_at,
            "reference_date": self.reference_date,
            "source_count": self.source_count,
            "sources": list(self.sources),
        }

    def to_markdown(self) -> str:
        """Render the full document (frontmatter + body) deterministically."""
        header = yaml.safe_dump(self.frontmatter(), sort_keys=False, default_flow_style=False)
        return f"---\n{header}---\n\n{self.body}\n"


def _unique(paths: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({path for path in paths if path}))


def _attention_sources(items: Iterable[AttentionItem]) -> tuple[str, ...]:
    return _unique(item.path for item in items)


def _build_today(index: OperatorIndex, today: date) -> ViewBody:
    items = attention_items(index, today)
    return ViewBody(render_attention("Today", items), _attention_sources(items))


def _build_projects(index: OperatorIndex, today: date) -> ViewBody:
    reviews = [build_project_review(index, project, today) for project in active_projects(index)]
    paths: list[str] = []
    for review in reviews:
        paths.append(review.project.path)
        paths.extend(entity.path for entity in review.people)
        paths.extend(entity.path for entity in review.tickets)
        paths.extend(entity.path for entity in review.actions)
        paths.extend(entity.path for entity in review.meetings)
        paths.extend(item.path for item in review.attention)
    return ViewBody(render_projects_review(reviews), _unique(paths))


def _build_team(index: OperatorIndex, today: date) -> ViewBody:
    workloads = [build_person_workload(index, person, today) for person in active_people(index)]
    paths: list[str] = []
    for workload in workloads:
        paths.append(workload.person.path)
        paths.extend(entity.path for entity in workload.projects)
        paths.extend(entity.path for entity in workload.tickets)
        paths.extend(entity.path for entity in workload.actions)
        paths.extend(entity.path for entity in workload.meetings)
        paths.extend(item.path for item in workload.attention)
    return ViewBody(render_team_review(workloads), _unique(paths))


def ticket_attention_items(index: OperatorIndex, today: date) -> tuple[AttentionItem, ...]:
    """Return ticket attention items, shared by the tickets view and the GUI."""
    return tuple(item for item in attention_items(index, today) if item.entity_type == "ticket")


def waiting_attention_items(index: OperatorIndex, today: date) -> tuple[AttentionItem, ...]:
    """Return waiting attention items, shared by the waiting view and the GUI."""
    return tuple(
        item for item in attention_items(index, today) if item.kind == AttentionKind.WAITING.value
    )


def high_severity_attention_items(index: OperatorIndex, today: date) -> tuple[AttentionItem, ...]:
    """Return high-severity attention items, shared by the manager view and the GUI."""
    return tuple(item for item in attention_items(index, today) if item.severity == "high")


def _build_tickets(index: OperatorIndex, today: date) -> ViewBody:
    items = ticket_attention_items(index, today)
    return ViewBody(render_attention("Tickets Needing Attention", items), _attention_sources(items))


def _build_waiting(index: OperatorIndex, today: date) -> ViewBody:
    items = waiting_attention_items(index, today)
    return ViewBody(render_attention("Waiting on Others", items), _attention_sources(items))


def _build_manager_review(index: OperatorIndex, today: date) -> ViewBody:
    items = high_severity_attention_items(index, today)
    return ViewBody(render_attention("Manager Review", items), _attention_sources(items))


VIEWS: dict[str, ViewDefinition] = {
    "today": ViewDefinition("today", "Today.md", "Today", _build_today),
    "projects": ViewDefinition("projects", "Projects.md", "Projects", _build_projects),
    "team": ViewDefinition("team", "Team.md", "Team", _build_team),
    "tickets": ViewDefinition(
        "tickets", "Tickets Needing Attention.md", "Tickets Needing Attention", _build_tickets
    ),
    "waiting": ViewDefinition(
        "waiting", "Waiting on Others.md", "Waiting on Others", _build_waiting
    ),
    "manager-review": ViewDefinition(
        "manager-review", "Manager Review.md", "Manager Review", _build_manager_review
    ),
}


def build_view(
    name: str,
    index: OperatorIndex,
    *,
    today: date,
    generated_at: str,
) -> GeneratedView:
    """Build one named view from the index, or raise ``KeyError`` if unknown."""
    definition = VIEWS[name]
    body = definition.build(index, today)
    return GeneratedView(
        name=definition.name,
        filename=definition.filename,
        title=definition.title,
        body=body.text,
        sources=body.sources,
        generated_at=generated_at,
        reference_date=today.isoformat(),
    )
