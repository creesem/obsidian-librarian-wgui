# Tasks: Work Management Operator Foundation

**Feature**: `specs/002-work-management-operator` | **Branch**: `codex/work-management-phase-1`

Read-only foundation. No writes, GUI, MCP, adapters, or database.

## Phase A — Inventory extension (shared foundation)

- [ ] T001 Add `read_frontmatter_typed(content) -> dict[str, Any]` to `src/obsidian_inventory/scanner.py` using `yaml.safe_load`; return `{}` for missing/malformed frontmatter without raising.
- [ ] T002 Add optional defaulted `frontmatter_typed: dict[str, Any]` field to `IndexRecord`; populate it in `build_index`.
- [ ] T003 Export `read_frontmatter_typed` from `src/obsidian_inventory/__init__.py`.
- [ ] T004 [P] Add `tests/test_scanner_typed_frontmatter.py`: scalar, block list, flow list, nested map, missing block, malformed block; assert existing `extract_frontmatter` output is unchanged.

## Phase B — Operator models and schema detection (US2)

- [ ] T005 Create `src/obsidian_operator/__init__.py` with `__version__` and public exports.
- [ ] T006 [P] Define enums and frozen dataclasses for the five entities in `src/obsidian_operator/models.py` (state kinds separated).
- [ ] T007 Implement `OPERATOR_TYPES`, `detect_type(frontmatter)`, and `entity_from_record(record)` in `src/obsidian_operator/schema.py`; unknown/absent `type` → skip.
- [ ] T008 [P] Add `tests/test_operator_schema.py`: type detection, skip non-entities, list/nested field preservation, scalar-vs-list coercion rules.

## Phase C — Validation (US2)

- [ ] T009 Implement `ValidationIssue`, `validate_entity`, and `validate_vault` in `src/obsidian_operator/validate.py` per `docs/71` §9 (required fields, enums, ticket external refs, action waiting/done, review-date ordering, unresolved-link warnings).
- [ ] T010 [P] Add `tests/test_operator_validate.py`: valid note passes; missing status; bad enum; malformed frontmatter does not abort; ticket reference/snapshot missing external id; action waiting missing `waiting_on`; action done missing `completed`; `next_review` before `last_reviewed`.

## Phase D — Read-only repository and relationships (US1, US3)

- [ ] T011 Implement `OperatorIndex` in `src/obsidian_operator/repository.py`: build from `build_index(vault, "vault")`, filter by `type`, index by title/alias, expose lookups and relationship resolution using `normalize_wikilink_target`.
- [ ] T012 Implement `src/obsidian_operator/render.py`: deterministic text and JSON rendering for list/show, including counts, skipped notes, warnings, errors.
- [ ] T013 [P] Add `tests/test_operator_repository.py`: entity counts; resolved assignee; unresolved link warning; duplicate title handling; stable ordering.

## Phase E — CLI (US1)

- [ ] T014 Implement `src/obsidian_operator/cli.py` (`obsidian-operator`): `project list|show`, `person show`, `ticket list|show`, `action list`; global `--vault`, `--json`; exit codes `0` ok / `1` validation errors / `2` usage/IO.
- [ ] T015 Register `obsidian-operator = "obsidian_operator.cli:main"` in `pyproject.toml` `[project.scripts]`.
- [ ] T016 [P] Add `tests/test_operator_cli.py`: list/show output, `--json`, missing vault path, empty vault, exit codes.

## Phase F — Safety, boundary, fixtures

- [ ] T017 Add `tests/fixtures/operator_vault/` with valid project/person/ticket/meeting/action notes plus malformed, bad-enum, unknown-link, and non-entity notes.
- [ ] T018 [P] Add `tests/test_operator_no_writes.py`: capture file bytes/mtimes before and after list/show and assert unchanged.
- [ ] T019 [P] Add `tests/test_operator_import_boundary.py`: assert `obsidian_operator` does not import `obsidian_librarian` or `obsidian_patron`.

## Phase G — Gates and report

- [ ] T020 Run `pytest`, `ruff check src tests`, `python -m obsidian_operator.cli --help`, `evals/run_evals.py`; confirm Librarian/Patron regression-green.
- [ ] T021 Document the result and next phase (Phase 2, `docs/72`).

## Phase H — Phase 2 review and relationships (implemented)

- [ ] T022 Add `dates.py` (shared ISO parsing) and `config.py` (`OperatorConfig` thresholds).
- [ ] T023 Add `Ticket.last_checked`; refactor `validate.py` to reuse `parse_iso_date`.
- [ ] T024 Add `OperatorIndex.from_entities` for synthetic/test indexes; `from_vault` delegates.
- [ ] T025 Add `relationships.py`: `Relationships`, `related_to` for projects and people.
- [ ] T026 Add `review.py`: `AttentionKind`, `AttentionItem`, `attention_items`, `build_project_review`, `build_person_workload`, `active_projects`, `active_people`.
- [ ] T027 Extend `render.py` with attention/review/workload renderers and JSON mappings.
- [ ] T028 Extend `cli.py`: `review today|team|projects`, `project review`, `person workload`, `--today`.
- [ ] T029 [P] Add `tests/test_operator_relationships.py`, `tests/test_operator_review.py`, `tests/test_operator_cli_review.py`.
- [ ] T030 Run full gates and confirm prior phases stay green.

## Dependencies

- Phase B–F depend on Phase A (typed frontmatter).
- Phase D depends on B; Phase E depends on D; Phase F depends on E.
- Phase H depends on B–E (models, repository, render, CLI).
- T004, T006, T008, T010, T013, T016, T018, T019, T029 are parallelizable within their phase.
