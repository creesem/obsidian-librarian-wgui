# Tasks: GUI Management Workspace

**Feature**: `specs/004-gui-management-workspace` | **Branch**: `codex/work-management-phase-4`

A local, tokenized, stdlib-only operator workspace. The only write is confirmed
generated-view regeneration; no canonical note is written.

## Phase A — Service layer

- [ ] T001 Add `src/obsidian_operator/gui/__init__.py` and `service.py` with `overview`, `today`, `project_board`, `team_board`, `entity_detail`, `view_definitions`, `preview_view`.
- [ ] T002 Add `render_view(request)` to `service.py`: tier `staging-write`; unconfirmed returns `needs_confirmation` with `equivalent_cli`; confirmed calls `write_view(...)` and returns a `change_set`; refuses overwrite unless force.
- [ ] T003 [P] Add `tests/test_operator_gui_service.py`: each read function shape; preview writes nothing; unconfirmed render writes nothing; confirmed render writes only under `90_Staging/Views`; canonical fixture byte-unchanged; equivalent CLI present.

## Phase B — Server and endpoints

- [ ] T004 Add `src/obsidian_operator/gui/server.py`: tokenized `ThreadingHTTPServer`, `create_server`, `run_gui`, CLI (`--vault`, `--host`, `--port`, `--no-browser`), `X-Gui-Token` required on `/api/*`.
- [ ] T005 Implement routes: `GET /api/health|overview|today|projects|team|entity|views`; `POST /api/view/preview`; `POST /api/view/render`.
- [ ] T006 Add `obsidian-operator-gui` entry point to `pyproject.toml`.
- [ ] T007 [P] Add `tests/test_operator_gui_server.py`: 401 on missing/wrong token; health/overview/today/projects/team/entity/views; preview writes nothing; unconfirmed render needs_confirmation and writes nothing; confirmed render writes and reports change set.

## Phase C — Frontend

- [ ] T008 Add `src/obsidian_operator/gui/static/index.html`: self-contained shell, seven-section nav, read panels, Views section with preview + confirmed generate, change-set and equivalent-CLI display.
- [ ] T009 [P] Add `tests/test_operator_gui_static.py`: required nav labels present; no external assets (`<script src=`, `<link href=`, CDN forbidden).

## Phase D — Boundary and safety regression

- [ ] T010 Add `tests/test_operator_gui_import_boundary.py`: gui sources reference no forbidden package; importing `obsidian_operator.gui` loads neither `obsidian_librarian` nor `obsidian_patron`.
- [ ] T011 Extend `tests/test_operator_no_writes.py`: a full GUI read session (overview/today/projects/team/entity/views + preview) leaves the vault byte-unchanged.
- [ ] T012 Update `docs/72_operator_roadmap.md` Phase 4 to *(implemented)*; ensure `docs/74_gui_workspace.md` matches the shipped contract.

## Phase E — Gates

- [ ] T013 Run full gates: `pytest`, `ruff check src tests`, `obsidian-operator --help` and `obsidian-operator-gui --help`, `evals/run_evals.py`; confirm Phases 1–3 stay green.

## Dependencies

- B depends on A (service); C depends on B (endpoints); D depends on A–C; E depends on D.
- T003, T007, T009 are parallelizable within their phase.
