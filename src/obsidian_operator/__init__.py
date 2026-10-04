"""Work-management operator over an Obsidian vault.

Depends only on ``obsidian_inventory``. See ``docs/70_work_management_architecture.md``.
"""

from __future__ import annotations

from obsidian_operator.config import DEFAULT_CONFIG, OperatorConfig
from obsidian_operator.models import (
    Action,
    ActionStatus,
    Effort,
    EntityBase,
    EntityType,
    Health,
    Meeting,
    MeetingStatus,
    OperatorEntity,
    Person,
    PersonStatus,
    Priority,
    Project,
    ProjectStatus,
    SyncMode,
    Ticket,
    TicketStatus,
)
from obsidian_operator.relationships import Relationships, related_to
from obsidian_operator.repository import OperatorIndex
from obsidian_operator.review import (
    AttentionItem,
    AttentionKind,
    PersonWorkload,
    ProjectReview,
    active_people,
    active_projects,
    attention_items,
    build_person_workload,
    build_project_review,
)
from obsidian_operator.schema import detect_type, entity_from_record
from obsidian_operator.validate import (
    ValidationIssue,
    validate_entity,
    validate_relationships,
)
from obsidian_operator.views import (
    VIEWS,
    GeneratedView,
    ViewDefinition,
    build_view,
)
from obsidian_operator.writer import (
    ViewWriteError,
    WriteResult,
    ensure_under,
    write_view,
)

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_CONFIG",
    "VIEWS",
    "Action",
    "ActionStatus",
    "AttentionItem",
    "AttentionKind",
    "Effort",
    "EntityBase",
    "EntityType",
    "GeneratedView",
    "Health",
    "Meeting",
    "MeetingStatus",
    "OperatorConfig",
    "OperatorEntity",
    "OperatorIndex",
    "Person",
    "PersonStatus",
    "PersonWorkload",
    "Priority",
    "Project",
    "ProjectReview",
    "ProjectStatus",
    "Relationships",
    "SyncMode",
    "Ticket",
    "TicketStatus",
    "ValidationIssue",
    "ViewDefinition",
    "ViewWriteError",
    "WriteResult",
    "active_people",
    "active_projects",
    "attention_items",
    "build_person_workload",
    "build_project_review",
    "build_view",
    "detect_type",
    "ensure_under",
    "entity_from_record",
    "related_to",
    "validate_entity",
    "validate_relationships",
    "write_view",
]
