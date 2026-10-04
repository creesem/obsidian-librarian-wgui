# Tasks: Generated Management Views

**Feature**: `specs/003-generated-management-views` | **Branch**: `codex/work-management-phase-3`

First operator write path: contained, opt-in, overwrite-protected. No canonical note is written.

## Phase A — Contained writer

- [ ] T001 Add `src/obsidian_operator/writer.py`: `ensure_under(root, target)`, `WriteResult`, `write_view(...)` with double containment (vault + views root).
- [ ] T002 `write_view` refuses an existing target unless `force=True`; never deletes; creates parent dirs.
- [ ] T003 [P] Add `tests/test_operator_view_writer.py`: create under root; refuse absolute; refuse `..`; refuse out-of-vault `--out`; refuse overwrite without `--force`; overwrite with `--force`.

## Phase B — View definitions and builders

- [ ] T004 Add `src/obsidian_operator/views.py`: `ViewDefinition`, `GeneratedView`, `VIEWS` (today, projects, team, tickets, waiting, manager-review).
- [ ] T005 Implement body builders reusing Phase 2 renderers; collect `sources` (contributing entity paths) and `source_count`.
- [ ] T006 Implement generated-frontmatter rendering (`type: view`, `generated`, `generator`, `view`, `generated_at`, `reference_date`, `source_count`, `sources`).
- [ ] T007 [P] Add `tests/test_operator_views.py`: each view builds; empty vault renders zero items; frontmatter fields present; `sources` reference real entities; byte-identical across two builds with pinned `today`/`generated_at`.

## Phase C — CLI

- [ ] T008 Extend `src/obsidian_operator/cli.py`: `view list` and `view render <name>|--all` with `--write`, `--force`, `--out`, `--today`, `--generated-at`, `--json`.
- [ ] T009 Default render writes nothing; `--write` prints created/overwritten change set.
- [ ] T010 [P] Add `tests/test_operator_cli_views.py`: list; render stdout; render `--write`; overwrite refusal; `--force`; unknown view; unparseable `--today`; `--json`.

## Phase D — Safety regression and docs

- [ ] T011 Extend `tests/test_operator_no_writes.py`: `view render --all` (no `--write`) leaves the vault byte-unchanged; canonical entities unchanged after `--write`.
- [ ] T012 Confirm generated views under `90_Staging` are not indexed as operator entities (`vault` scope).
- [ ] T013 Update `docs/72_operator_roadmap.md` Phase 3 to *(implemented)*; ensure `docs/73_generated_views.md` matches the shipped contract.
- [ ] T014 Run full gates: `pytest`, `ruff check src tests`, all CLI `--help`, `evals/run_evals.py`; confirm Phases 1–2 green.

## Dependencies

- Phase B depends on A (writer) and on Phase 2 review functions.
- Phase C depends on B; Phase D depends on C.
- T003, T007, T010 are parallelizable within their phase.
