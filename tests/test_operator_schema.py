"""Schema detection and entity construction tests."""

from __future__ import annotations

from pathlib import Path

from obsidian_inventory import build_index
from obsidian_operator.models import EntityType, Project
from obsidian_operator.schema import (
    detect_type,
    entity_from_record,
    is_malformed_operator_note,
)

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"


def _records():
    return {record.path: record for record in build_index(FIXTURE, "vault").indexed_records}


def test_detect_type_accepts_known_types() -> None:
    assert detect_type({"type": "project"}) == "project"
    assert detect_type({"type": "action"}) == "action"


def test_detect_type_rejects_missing_or_unknown() -> None:
    assert detect_type({}) is None
    assert detect_type({"type": "daily"}) is None
    assert detect_type({"type": 7}) is None


def test_entity_from_record_builds_typed_project() -> None:
    record = _records()["Projects/CareLogic Automation.md"]
    entity = entity_from_record(record)
    assert isinstance(entity, Project)
    assert entity.entity_type is EntityType.PROJECT
    assert entity.owner == "[[Alex Rivera]]"
    assert entity.people == ("[[Sam Okafor]]", "[[Dana Lee]]")
    assert entity.systems == ("CareLogic", "Snowflake")
    assert entity.priority == "P1"
    assert entity.health == "yellow"


def test_non_entity_note_is_skipped() -> None:
    record = _records()["Notes/Daily.md"]
    assert entity_from_record(record) is None
    assert is_malformed_operator_note(record) is False


def test_malformed_operator_note_is_detected() -> None:
    record = _records()["Broken/Malformed.md"]
    assert entity_from_record(record) is None
    assert is_malformed_operator_note(record) is True


def test_ticket_external_id_coerced_to_string() -> None:
    record = _records()["Operations/Tickets/SD-31814.md"]
    entity = entity_from_record(record)
    assert entity is not None
    assert entity.external_id == "31814"
    assert entity.manager_attention is True
