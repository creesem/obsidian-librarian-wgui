"""Deterministic relationship queries over the operator index.

Relationships are derived from wikilink fields; nothing is stored or invented.
Unresolved links never produce a relationship.
"""

from __future__ import annotations

from dataclasses import dataclass

from obsidian_operator.models import EntityBase, EntityType
from obsidian_operator.repository import OperatorIndex


@dataclass(frozen=True)
class Relationships:
    """Entities related to one entity, each tuple sorted deterministically."""

    people: tuple[EntityBase, ...] = ()
    projects: tuple[EntityBase, ...] = ()
    tickets: tuple[EntityBase, ...] = ()
    actions: tuple[EntityBase, ...] = ()
    meetings: tuple[EntityBase, ...] = ()


def related_to(index: OperatorIndex, entity: EntityBase) -> Relationships:
    """Return the entities related to ``entity`` via its wikilink fields."""
    if entity.entity_type is EntityType.PROJECT:
        return _project_relationships(index, entity)
    if entity.entity_type is EntityType.PERSON:
        return _person_relationships(index, entity)
    return Relationships()


def _project_relationships(index: OperatorIndex, project: EntityBase) -> Relationships:
    links = (getattr(project, "owner", None), *getattr(project, "people", ()))
    people = _resolve_targets(index, links)
    tickets = _matching(index.list_type(EntityType.TICKET.value), index, "project", project)
    actions = _matching(index.list_type(EntityType.ACTION.value), index, "project", project)
    meetings = _matching(index.list_type(EntityType.MEETING.value), index, "project", project)
    return Relationships(people=people, tickets=tickets, actions=actions, meetings=meetings)


def _person_relationships(index: OperatorIndex, person: EntityBase) -> Relationships:
    projects = tuple(
        project
        for project in index.list_type(EntityType.PROJECT.value)
        if _link_matches(index, getattr(project, "owner", None), person)
        or any(_link_matches(index, member, person) for member in getattr(project, "people", ()))
    )
    tickets = _matching(index.list_type(EntityType.TICKET.value), index, "assignee", person)
    actions = _matching(index.list_type(EntityType.ACTION.value), index, "owner", person)
    meetings = tuple(
        meeting
        for meeting in index.list_type(EntityType.MEETING.value)
        if any(
            _link_matches(index, attendee, person)
            for attendee in getattr(meeting, "attendees", ())
        )
    )
    manager = _resolve_targets(index, (getattr(person, "manager", None),))
    return Relationships(
        people=manager,
        projects=projects,
        tickets=tickets,
        actions=actions,
        meetings=meetings,
    )


def _matching(
    candidates: tuple[EntityBase, ...],
    index: OperatorIndex,
    field_name: str,
    target: EntityBase,
) -> tuple[EntityBase, ...]:
    return tuple(
        candidate
        for candidate in candidates
        if _link_matches(index, getattr(candidate, field_name, None), target)
    )


def _link_matches(index: OperatorIndex, link: object | None, target: EntityBase) -> bool:
    if not link:
        return False
    resolved = index.resolve(str(link))
    return resolved is not None and resolved.path == target.path


def _resolve_targets(
    index: OperatorIndex,
    links: tuple[object | None, ...],
) -> tuple[EntityBase, ...]:
    resolved: dict[str, EntityBase] = {}
    for link in links:
        if not link:
            continue
        entity = index.resolve(str(link))
        if entity is not None:
            resolved.setdefault(entity.path, entity)
    return tuple(
        sorted(resolved.values(), key=lambda entity: (entity.title.casefold(), entity.path))
    )
