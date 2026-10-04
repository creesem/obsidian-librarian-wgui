"""Read-only operational index for a management vault.

Builds a typed entity view from the shared inventory scanner and resolves
relationships. This module never writes to the vault.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from obsidian_inventory import build_index, normalize_wikilink_target
from obsidian_operator.models import EntityBase
from obsidian_operator.schema import (
    entity_from_record,
    is_malformed_operator_note,
    link_target,
)
from obsidian_operator.validate import ValidationIssue, validate_all


@dataclass
class OperatorIndex:
    """A read-only view of all operational entities in a vault."""

    root: Path
    entities: tuple[EntityBase, ...] = ()
    issues: tuple[ValidationIssue, ...] = ()
    _by_type: dict[str, tuple[EntityBase, ...]] = field(default_factory=dict)
    _lookup: dict[str, EntityBase] = field(default_factory=dict)
    _duplicate_keys: tuple[str, ...] = ()

    @classmethod
    def from_vault(cls, vault_root: str | Path) -> OperatorIndex:
        """Build an index by scanning ``vault_root`` with the shared inventory scanner."""
        root = Path(vault_root).expanduser().resolve(strict=False)
        summary = build_index(root, "vault")

        entities: list[EntityBase] = []
        malformed: list[ValidationIssue] = []
        for record in summary.indexed_records:
            entity = entity_from_record(record)
            if entity is None:
                if is_malformed_operator_note(record):
                    malformed.append(
                        ValidationIssue(
                            path=record.path,
                            message="Malformed frontmatter for operator note",
                            severity="error",
                            rule="malformed",
                        )
                    )
                continue
            entities.append(entity)

        index = cls.from_entities(entities, root=root)
        if malformed:
            issues = list(index.issues) + malformed
            issues.sort(key=lambda issue: (issue.path, issue.severity, issue.message))
            index.issues = tuple(issues)
        return index

    @classmethod
    def from_entities(
        cls,
        entities: Iterable[EntityBase],
        *,
        root: str | Path | None = None,
    ) -> OperatorIndex:
        """Assemble an index from typed entities (used by tests and callers)."""
        root_path = Path(root) if root is not None else Path(".")
        ordered = sorted(
            entities,
            key=lambda entity: (entity.entity_type.value, entity.title.casefold(), entity.path),
        )

        lookup, duplicates = _build_lookup(ordered)
        issues: list[ValidationIssue] = [
            ValidationIssue(
                path="",
                message=f"Duplicate entity key: {key}",
                severity="warning",
                rule="duplicate",
            )
            for key in duplicates
        ]
        issues.extend(validate_all(ordered, set(lookup)))
        issues.sort(key=lambda issue: (issue.path, issue.severity, issue.message))

        by_type: dict[str, list[EntityBase]] = {}
        for entity in ordered:
            by_type.setdefault(entity.entity_type.value, []).append(entity)

        return cls(
            root=root_path,
            entities=tuple(ordered),
            issues=tuple(issues),
            _by_type={key: tuple(value) for key, value in by_type.items()},
            _lookup=lookup,
            _duplicate_keys=duplicates,
        )

    def list_type(self, entity_type: str) -> tuple[EntityBase, ...]:
        """Return all entities of a type, in stable order."""
        return self._by_type.get(entity_type, ())

    def get(self, entity_type: str, name: str) -> EntityBase | None:
        """Resolve a name to an entity of the requested type, or ``None``."""
        entity = self._lookup.get(link_target(name))
        if entity is not None and entity.entity_type.value == entity_type:
            return entity
        return None

    def resolve(self, target: str) -> EntityBase | None:
        """Resolve any wikilink/name target to an entity, or ``None``."""
        return self._lookup.get(link_target(target))

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    def counts(self) -> dict[str, int]:
        """Return entity counts per type, including zero-count types."""
        return {key: len(value) for key, value in sorted(self._by_type.items())}


def _build_lookup(
    entities: list[EntityBase],
) -> tuple[dict[str, EntityBase], tuple[str, ...]]:
    lookup: dict[str, EntityBase] = {}
    duplicates: set[str] = set()
    for entity in entities:
        keys = {normalize_wikilink_target(entity.title)}
        keys.update(normalize_wikilink_target(alias) for alias in entity.aliases)
        for key in keys:
            if not key:
                continue
            if key in lookup:
                duplicates.add(key)
            else:
                lookup[key] = entity
    for key in duplicates:
        lookup.pop(key, None)
    return lookup, tuple(sorted(duplicates))
