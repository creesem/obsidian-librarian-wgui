"""Schema detection and entity construction for obsidian_operator.

Turns a shared ``IndexRecord`` into a typed operational entity. Notes whose
``type`` is absent or unknown are not operator entities and are skipped.
"""

from __future__ import annotations

from typing import Any

from obsidian_inventory import IndexRecord, normalize_wikilink_target
from obsidian_operator.models import (
    ENTITY_CLASS_BY_TYPE,
    Action,
    EntityBase,
    EntityType,
    Meeting,
    Person,
    Project,
    Ticket,
)

OPERATOR_TYPE_VALUES: tuple[str, ...] = tuple(member.value for member in EntityType)


def detect_type(frontmatter: dict[str, Any]) -> str | None:
    """Return the operator type named by ``frontmatter['type']``, or ``None``."""
    value = frontmatter.get("type")
    if isinstance(value, str) and value in OPERATOR_TYPE_VALUES:
        return value
    return None


def is_malformed_operator_note(record: IndexRecord) -> bool:
    """Return True when a note looks like an operator note but its YAML did not parse.

    The lossy line reader can still recover ``type: ticket`` from a block that the
    YAML parser rejects. That mismatch means the note is malformed rather than
    simply not an operator entity.
    """
    lossy_type = record.frontmatter.get("type")
    typed_type = record.frontmatter_typed.get("type") if isinstance(
        record.frontmatter_typed, dict
    ) else None
    return lossy_type in OPERATOR_TYPE_VALUES and typed_type != lossy_type


def entity_from_record(record: IndexRecord) -> EntityBase | None:
    """Build a typed entity from an index record, or return ``None`` to skip it."""
    frontmatter = record.frontmatter_typed
    if not isinstance(frontmatter, dict):
        return None
    entity_type = detect_type(frontmatter)
    if entity_type is None:
        return None

    common = {
        "path": record.path,
        "title": record.title,
        "status": _as_str(frontmatter.get("status")) or "",
        "aliases": tuple(record.aliases),
        "tags": tuple(record.tags),
        "raw": dict(frontmatter),
    }

    if entity_type == EntityType.PROJECT.value:
        return Project(
            **common,
            owner=_as_str(frontmatter.get("owner")),
            priority=_as_str(frontmatter.get("priority")),
            health=_as_str(frontmatter.get("health")),
            effort=_as_str(frontmatter.get("effort")),
            people=_as_str_tuple(frontmatter.get("people")),
            systems=_as_str_tuple(frontmatter.get("systems")),
            next_action=_as_str(frontmatter.get("next_action")),
            last_reviewed=_as_str(frontmatter.get("last_reviewed")),
            next_review=_as_str(frontmatter.get("next_review")),
        )
    if entity_type == EntityType.PERSON.value:
        return Person(
            **common,
            role=_as_str(frontmatter.get("role")),
            team=_as_str(frontmatter.get("team")),
            manager=_as_str(frontmatter.get("manager")),
            email=_as_str(frontmatter.get("email")),
        )
    if entity_type == EntityType.TICKET.value:
        return Ticket(
            **common,
            assignee=_as_str(frontmatter.get("assignee")),
            priority=_as_str(frontmatter.get("priority")),
            application=_as_str(frontmatter.get("application")),
            project=_as_str(frontmatter.get("project")),
            source_system=_as_str(frontmatter.get("source_system")),
            external_id=_as_str(frontmatter.get("external_id")),
            sync_mode=_as_str(frontmatter.get("sync_mode")),
            next_action=_as_str(frontmatter.get("next_action")),
            manager_attention=_as_bool(frontmatter.get("manager_attention")),
            last_checked=_as_str(frontmatter.get("last_checked")),
        )
    if entity_type == EntityType.MEETING.value:
        return Meeting(
            **common,
            date=_as_str(frontmatter.get("date")),
            attendees=_as_str_tuple(frontmatter.get("attendees")),
            project=_as_str(frontmatter.get("project")),
            source_system=_as_str(frontmatter.get("source_system")),
            external_id=_as_str(frontmatter.get("external_id")),
            sync_mode=_as_str(frontmatter.get("sync_mode")),
        )
    if entity_type == EntityType.ACTION.value:
        return Action(
            **common,
            owner=_as_str(frontmatter.get("owner")),
            due=_as_str(frontmatter.get("due")),
            project=_as_str(frontmatter.get("project")),
            related_ticket=_as_str(frontmatter.get("related_ticket")),
            waiting_on=_as_str(frontmatter.get("waiting_on")),
            completed=_as_str(frontmatter.get("completed")),
        )
    return None


def link_target(value: str) -> str:
    """Normalize a wikilink-valued frontmatter string to a lookup key."""
    text = value.strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2]
    text = text.split("|", 1)[0].split("#", 1)[0]
    return normalize_wikilink_target(text)


def link_targets(entity: EntityBase, field_name: str) -> tuple[str, ...]:
    """Return normalized targets for one relationship field of an entity."""
    value = getattr(entity, field_name, None)
    if value is None:
        return ()
    values = value if isinstance(value, tuple) else (value,)
    targets = []
    for item in values:
        text = str(item).strip()
        if not text:
            continue
        targets.append(link_target(text))
    return tuple(targets)


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).strip()
    return text or None


def _as_str_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        items = (str(item).strip() for item in value)
        return tuple(item for item in items if item)
    text = str(value).strip()
    return (text,) if text else ()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() in {"true", "yes", "1"}
    return bool(value)


__all__ = [
    "ENTITY_CLASS_BY_TYPE",
    "OPERATOR_TYPE_VALUES",
    "detect_type",
    "entity_from_record",
    "is_malformed_operator_note",
    "link_target",
    "link_targets",
]
