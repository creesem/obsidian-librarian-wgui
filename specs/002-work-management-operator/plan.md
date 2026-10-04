# Implementation Plan: Work Management Operator Foundation

**Branch**: `codex/work-management-phase-1` | **Date**: 2026-10-03 | **Spec**: `specs/002-work-management-operator/spec.md`

**Input**: Feature specification from `specs/002-work-management-operator/spec.md`

## Summary

Add a read-only `obsidian_operator` package that recognizes, validates, and lists
operational entities (project, person, ticket, meeting, action) over a separate
management vault. Reuse `obsidian_inventory` for scanning, extending it with a
typed frontmatter reader that preserves YAML lists/nested maps. No writes, GUI,
MCP, adapters, or database.

## Technical Context

**Language/Version**: Python ≥ 3.10 (CI: 3.11, 3.12)

**Primary Dependencies**: stdlib + `PyYAML` (already a project dependency). No new runtime dependency.

**Storage**: filesystem Markdown + YAML frontmatter only. No database.

**Testing**: `pytest` (from repo root; `pyproject.toml` sets `pythonpath=src`).

**Target Platform**: local CLI on Windows/Linux/macOS.

**Project Type**: single Python project, `src/` layout, three existing packages plus the new one.

**Performance Goals**: deterministic scan of a local vault; no large-vault tuning in this phase.

**Constraints**: read-only; deterministic; no network/LLM/embeddings; reuse the single scanner (Golden Rule 8).

**Scale/Scope**: five entity schemas; four read-only command groups.

## Constitution Check

*GATE: Must pass before Phase 1 tasks.*

- No destructive write path is introduced — PASS (read-only).
- No raw source mutation — PASS.
- All writes inside `90_Staging/` unless authorized — N/A (no writes).
- Provenance and uncertainty handling specified — PASS (`docs/70`, `docs/71`; warnings for unresolved links/malformed notes).
- Review report behavior specified — PASS (list/show names counts, skipped, warnings, errors).
- Schemas and validators updated for output-contract changes — PASS (`docs/71`; `obsidian_operator/validate.py`).
- Tests/evals cover the changed behavior — PASS (see `tasks.md`).
- New phase adding LLM/embeddings/vault-mutation/MCP specified as opt-in first — PASS (none introduced; deferred in `docs/72`).

**Post-design re-check**: still compliant — Phase 1 introduces no write or integration surface.

## Project Structure

### Documentation (this feature)

```text
specs/002-work-management-operator/
├── spec.md
├── plan.md
└── tasks.md
docs/
├── 70_work_management_architecture.md
├── 71_operational_note_schemas.md
└── 72_operator_roadmap.md
```

### Source Code

```text
src/obsidian_inventory/
├── scanner.py          # + read_frontmatter_typed; + IndexRecord.frontmatter_typed
└── __init__.py         # + export read_frontmatter_typed

src/obsidian_operator/  # NEW
├── __init__.py         # public API + __version__
├── models.py           # frozen dataclasses + str enums for the five entities
├── schema.py           # OPERATOR_TYPES, detect_type, entity_from_record
├── validate.py         # ValidationIssue, validate_entity, validate_vault
├── repository.py       # OperatorIndex: build from build_index(vault,"vault")
├── render.py           # deterministic text/JSON rendering for list/show
└── cli.py              # obsidian-operator entrypoint

tests/
├── test_operator_schema.py
├── test_operator_validate.py
├── test_operator_repository.py
├── test_operator_cli.py
├── test_operator_no_writes.py
├── test_operator_import_boundary.py
└── fixtures/operator_vault/...
```

**Structure Decision**: new sibling package under `src/`, depending only on
`obsidian_inventory`. Mirrors the existing `obsidian_librarian`/`obsidian_patron`
conventions (argparse CLI, frozen dataclasses, `__version__`).

## Complexity Tracking

No constitution violations. No added dependencies. No new write surface.
