"""Deterministic validation for operational entities.

Rules follow ``docs/71_operational_note_schemas.md`` section 9. Validation never
raises on a bad note: it returns issues and lets callers continue processing.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from obsidian_operator.dates import parse_iso_date
from obsidian_operator.models import (
    ENUM_FIELDS,
    LINK_FIELDS_BY_TYPE,
    STATUS_ENUM_BY_TYPE,
    EntityBase,
    EntityType,
)
from obsidian_operator.schema import link_targets

# Fields that must be present for a given type (beyond the universal ``status``).
REQUIRED_BY_TYPE: dict[str, tuple[str, ...]] = {
    EntityType.PROJECT.value: ("owner", "priority", "health"),
    EntityType.MEETING.value: ("date",),
}

EXTERNAL_SYNC_MODES = {"reference", "snapshot"}


@dataclass(frozen=True)
class ValidationIssue:
    """One validation finding for an operational note."""

    path: str
    message: str
    severity: str = "error"
    rule: str = ""


def validate_entity(entity: EntityBase) -> list[ValidationIssue]:
    """Validate one entity's fields, returning errors and warnings."""
    issues: list[ValidationIssue] = []
    entity_type = entity.entity_type.value

    if not entity.status:
        issues.append(_issue(entity, "Missing required frontmatter field: status", rule="required"))
    else:
        allowed = {member.value for member in STATUS_ENUM_BY_TYPE[entity_type]}
        if entity.status not in allowed:
            issues.append(
                _issue(entity, f"Invalid status '{entity.status}' for {entity_type}", rule="enum")
            )

    for field_name, enum in ENUM_FIELDS.items():
        value = _field_value(entity, field_name)
        if value is None:
            continue
        if str(value) not in {member.value for member in enum}:
            issues.append(_issue(entity, f"Invalid {field_name} '{value}'", rule="enum"))

    issues.extend(_validate_required(entity))
    issues.extend(_validate_conditionals(entity))
    issues.extend(_validate_date_order(entity))
    return issues


def validate_relationships(
    entity: EntityBase,
    known_targets: set[str],
) -> list[ValidationIssue]:
    """Warn about wikilink targets that do not resolve to a known entity."""
    issues: list[ValidationIssue] = []
    entity_type = entity.entity_type.value
    for field_name in LINK_FIELDS_BY_TYPE.get(entity_type, ()):
        value = getattr(entity, field_name, None)
        if field_name == "related_ticket" and isinstance(value, str) and "[[" not in value:
            # related_ticket may legitimately be a bare external id, not a wikilink.
            continue
        for target in link_targets(entity, field_name):
            if target and target not in known_targets:
                issues.append(
                    _issue(
                        entity,
                        f"Unresolved link in {field_name}: {target}",
                        severity="warning",
                        rule="unresolved_link",
                    )
                )
    return issues


def validate_all(
    entities: Iterable[EntityBase],
    known_targets: set[str],
) -> list[ValidationIssue]:
    """Validate every entity and return issues in stable order."""
    issues: list[ValidationIssue] = []
    for entity in entities:
        issues.extend(validate_entity(entity))
        issues.extend(validate_relationships(entity, known_targets))
    issues.sort(key=lambda issue: (issue.path, issue.severity, issue.message))
    return issues


def has_errors(issues: Iterable[ValidationIssue]) -> bool:
    """Return True when any issue has error severity."""
    return any(issue.severity == "error" for issue in issues)


def _validate_required(entity: EntityBase) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field_name in REQUIRED_BY_TYPE.get(entity.entity_type.value, ()):
        if not getattr(entity, field_name, None):
            issues.append(
                _issue(entity, f"Missing required frontmatter field: {field_name}", rule="required")
            )
    return issues


def _validate_conditionals(entity: EntityBase) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    entity_type = entity.entity_type.value

    if entity_type == EntityType.TICKET.value:
        sync_mode = getattr(entity, "sync_mode", None)
        if sync_mode in EXTERNAL_SYNC_MODES:
            for field_name in ("source_system", "external_id"):
                if not getattr(entity, field_name, None):
                    issues.append(
                        _issue(
                            entity,
                            f"sync_mode '{sync_mode}' requires frontmatter field: {field_name}",
                            rule="conditional",
                        )
                    )

    if entity_type == EntityType.ACTION.value:
        status = entity.status
        if status == "waiting" and not getattr(entity, "waiting_on", None):
            issues.append(
                _issue(
                    entity,
                    "status 'waiting' requires frontmatter field: waiting_on",
                    rule="conditional",
                )
            )
        if status == "done" and not getattr(entity, "completed", None):
            issues.append(
                _issue(
                    entity,
                    "status 'done' requires frontmatter field: completed",
                    rule="conditional",
                )
            )

    if entity_type == EntityType.MEETING.value and getattr(
        entity, "source_system", None
    ) and not getattr(entity, "sync_mode", None):
        issues.append(
            _issue(
                entity,
                "source_system present without sync_mode",
                severity="warning",
                rule="conditional",
            )
        )

    return issues


def _validate_date_order(entity: EntityBase) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if entity.entity_type is not EntityType.PROJECT:
        return issues

    last_reviewed = getattr(entity, "last_reviewed", None)
    next_review = getattr(entity, "next_review", None)
    if not last_reviewed or not next_review:
        return issues

    parsed_last = parse_iso_date(last_reviewed)
    parsed_next = parse_iso_date(next_review)
    if parsed_last is None or parsed_next is None:
        issues.append(
            _issue(entity, "Unparseable review date", severity="warning", rule="date_order")
        )
        return issues
    if parsed_next < parsed_last:
        issues.append(
            _issue(entity, "next_review is before last_reviewed", rule="date_order")
        )
    return issues


def _field_value(entity: EntityBase, field_name: str) -> object | None:
    """Return a modeled attribute when present, else fall back to raw frontmatter."""
    value = getattr(entity, field_name, None)
    if value is not None:
        return value
    return entity.raw.get(field_name)


def _issue(
    entity: EntityBase,
    message: str,
    severity: str = "error",
    rule: str = "",
) -> ValidationIssue:
    return ValidationIssue(path=entity.path, message=message, severity=severity, rule=rule)
