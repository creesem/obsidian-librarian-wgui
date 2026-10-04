# Implementation Plan: Generated Management Views

**Branch**: `codex/work-management-phase-3` | **Date**: 2026-10-03 | **Spec**: `specs/003-generated-management-views/spec.md`

**Input**: Feature specification from `specs/003-generated-management-views/spec.md`

## Summary

Render the Phase 2 read-only reviews into six reproducible Markdown views under
`90_Staging/Views/`. Preview by default; `--write` is the first explicit operator
write path, confined to a contained views root, overwrite-protected, and stamped
with generated-provenance frontmatter. No canonical note is ever touched.

## Technical Context

**Language/Version**: Python ≥ 3.10 (CI: 3.11, 3.12)

**Primary Dependencies**: stdlib + `PyYAML` (already present). No new runtime dependency.

**Storage**: filesystem Markdown + YAML frontmatter; writes only under `90_Staging/Views/` (default).

**Testing**: `pytest` (repo root; `pythonpath=src`).

**Target Platform**: local CLI, Windows/Linux/macOS.

**Constraints**: read-only by default; deterministic with pinned date/timestamp; operator imports only `obsidian_inventory`; no network/LLM/DB.

## Constitution Check

*GATE: Must pass before Phase 3 tasks.*

- No destructive write path — PASS (new-file creation only; no delete; overwrite opt-in).
- No raw source mutation — PASS (canonical notes never written).
- All writes inside `90_Staging/` unless explicitly authorized — PASS (default views root; `--out` contained under vault).
- Provenance and uncertainty handling specified — PASS (generated frontmatter + `sources`).
- Review report behavior specified — PASS (created/overwritten change set printed).
- Schemas/validators updated for output contract — PASS (`docs/73`; `type: view` is not an operator entity).
- Tests/evals cover changed behavior — PASS (containment, no-write, determinism).
- New phase adding vault mutation specified as opt-in before implementation — PASS (this spec + explicit `--write`).

**Post-design re-check**: still compliant; the only new surface is a contained, opt-in view writer.

## Project Structure

### Documentation

```text
specs/003-generated-management-views/
├── spec.md
├── plan.md
└── tasks.md
docs/73_generated_views.md
```

### Source Code

```text
src/obsidian_operator/
├── views.py      # NEW: ViewDefinition, GeneratedView, six builders, frontmatter
├── writer.py     # NEW: ensure_under, write_view (operator-local containment)
├── render.py     # + render_view body helpers (reuse Phase 2 renderers)
├── cli.py        # + view list | view render
└── __init__.py   # + exports

tests/
├── test_operator_view_writer.py   # containment + overwrite
├── test_operator_views.py         # builders + frontmatter + determinism
├── test_operator_cli_views.py     # CLI list/render/write
└── test_operator_no_writes.py     # extended: render without --write writes nothing
```

**Structure Decision**: two new operator modules. `writer.py` carries a small
operator-local `ensure_under` mirroring `obsidian_patron.safety.ensure_under`,
so the package keeps its one-way dependency on `obsidian_inventory` and never
imports `obsidian_librarian`/`obsidian_patron`. Centralizing `ensure_under` into
`obsidian_inventory` is a noted future option, out of scope here.

## Design

### Views

| name | filename | body source |
|---|---|---|
| `today` | `Today.md` | `attention_items(index, today)` |
| `projects` | `Projects.md` | `build_project_review` over `active_projects` |
| `team` | `Team.md` | `build_person_workload` over `active_people` |
| `tickets` | `Tickets Needing Attention.md` | ticket attention items |
| `waiting` | `Waiting on Others.md` | waiting attention items |
| `manager-review` | `Manager Review.md` | high-severity attention items |

Bodies reuse the deterministic Phase 2 text renderers.

### Generated frontmatter

```yaml
---
type: view
generated: true
generator: obsidian-operator
view: today
generated_at: 2026-10-03T12:00:00+00:00
reference_date: 2026-10-10
source_count: 10
sources:
  - Projects/CareLogic Automation.md
  - Operations/Tickets/SD-31814.md
---
```

`type: view` is not an operator entity, so a generated view that ever falls inside
the scanned scope is skipped, not treated as malformed.

### Writer

- `ensure_under(root, target) -> Path` — resolves and rejects escapes.
- `write_view(views_root, vault_root, view, *, force=False) -> WriteResult` —
  double containment (vault + views root), refuse existing unless `force`, write
  atomically via `write_text`, return created/overwritten.

### CLI

```text
obsidian-operator view list
obsidian-operator view render <name> | --all
    [--write] [--force] [--out DIR] [--today YYYY-MM-DD]
    [--generated-at ISO8601] [--json]
```

Exit codes: `0` ok; `1` vault validation errors; `2` usage/IO/containment errors.

## Complexity Tracking

No constitution violations. No new dependencies. One new, contained, opt-in write surface.
