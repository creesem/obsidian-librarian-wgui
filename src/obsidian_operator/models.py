"""Typed operational models for obsidian_operator.

Five entities: project, person, ticket, meeting, action. State kinds are kept
separate per ``docs/71_operational_note_schemas.md``: ``raw`` carries the typed
frontmatter (source/management/external state); derived state is never stored here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


class EntityType(str, Enum):
    """The five operational note types selected by the ``type`` frontmatter value."""

    PROJECT = "project"
    PERSON = "person"
    TICKET = "ticket"
    MEETING = "meeting"
    ACTION = "action"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    DONE = "done"
    ARCHIVED = "archived"


class PersonStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class MeetingStatus(str, Enum):
    SCHEDULED = "scheduled"
    HELD = "held"
    CANCELLED = "cancelled"


class ActionStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    DONE = "done"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class Health(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class Effort(str, Enum):
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"


class SyncMode(str, Enum):
    REFERENCE = "reference"
    SNAPSHOT = "snapshot"
    MANAGED_LOCALLY = "managed-locally"
    GENERATED = "generated"


STATUS_ENUM_BY_TYPE: dict[str, type[Enum]] = {
    EntityType.PROJECT.value: ProjectStatus,
    EntityType.PERSON.value: PersonStatus,
    EntityType.TICKET.value: TicketStatus,
    EntityType.MEETING.value: MeetingStatus,
    EntityType.ACTION.value: ActionStatus,
}

# Frontmatter fields validated against a closed enum, for every entity type.
ENUM_FIELDS: dict[str, type[Enum]] = {
    "priority": Priority,
    "health": Health,
    "effort": Effort,
    "sync_mode": SyncMode,
}

# Wikilink-valued fields per type, used for relationship resolution.
LINK_FIELDS_BY_TYPE: dict[str, tuple[str, ...]] = {
    EntityType.PROJECT.value: ("owner", "people"),
    EntityType.PERSON.value: ("manager",),
    EntityType.TICKET.value: ("assignee", "project"),
    EntityType.MEETING.value: ("attendees", "project"),
    EntityType.ACTION.value: ("owner", "project", "related_ticket"),
}


@dataclass(frozen=True)
class EntityBase:
    """Fields shared by every operational entity."""

    path: str
    title: str
    status: str
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def entity_type(self) -> EntityType:
        """Return the entity's type. Overridden by each subclass."""
        raise NotImplementedError


@dataclass(frozen=True)
class Project(EntityBase):
    entity_type: ClassVar[EntityType] = EntityType.PROJECT

    owner: str | None = None
    priority: str | None = None
    health: str | None = None
    effort: str | None = None
    people: tuple[str, ...] = ()
    systems: tuple[str, ...] = ()
    next_action: str | None = None
    last_reviewed: str | None = None
    next_review: str | None = None


@dataclass(frozen=True)
class Person(EntityBase):
    entity_type: ClassVar[EntityType] = EntityType.PERSON

    role: str | None = None
    team: str | None = None
    manager: str | None = None
    email: str | None = None


@dataclass(frozen=True)
class Ticket(EntityBase):
    entity_type: ClassVar[EntityType] = EntityType.TICKET

    assignee: str | None = None
    priority: str | None = None
    application: str | None = None
    project: str | None = None
    source_system: str | None = None
    external_id: str | None = None
    sync_mode: str | None = None
    next_action: str | None = None
    manager_attention: bool = False
    last_checked: str | None = None


@dataclass(frozen=True)
class Meeting(EntityBase):
    entity_type: ClassVar[EntityType] = EntityType.MEETING

    date: str | None = None
    attendees: tuple[str, ...] = ()
    project: str | None = None
    source_system: str | None = None
    external_id: str | None = None
    sync_mode: str | None = None


@dataclass(frozen=True)
class Action(EntityBase):
    entity_type: ClassVar[EntityType] = EntityType.ACTION

    owner: str | None = None
    due: str | None = None
    project: str | None = None
    related_ticket: str | None = None
    waiting_on: str | None = None
    completed: str | None = None


OperatorEntity = Project | Person | Ticket | Meeting | Action

# Backwards-friendly alias for the union used across the package.
ENTITY_CLASS_BY_TYPE: dict[str, type[EntityBase]] = {
    EntityType.PROJECT.value: Project,
    EntityType.PERSON.value: Person,
    EntityType.TICKET.value: Ticket,
    EntityType.MEETING.value: Meeting,
    EntityType.ACTION.value: Action,
}
