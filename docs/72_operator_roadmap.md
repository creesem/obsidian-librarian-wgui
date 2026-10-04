# 72 — `obsidian_operator` Roadmap

Status: Proposed.

Phased path from the current Librarian/Patron toolchain to a local-first
work-management layer. Each phase is independently reviewable, keeps prior tests
green, and adds no autonomous trusted-vault mutation. Read
`docs/70_work_management_architecture.md` and `docs/71_operational_note_schemas.md`
first.

**Global non-goals (all phases):** no deletion, no overwrite by default, no raw
source mutation, no database, no network/LLM/embeddings in the deterministic path,
no external-system synchronization until Phase 5, no GUI-only business rules.

---

## Phase 0 — Repository assessment *(complete in this pass)*

**Deliverable:** a concise assessment of the existing architecture, extension
points, and risks.

**Outcome:** captured in `docs/70` §2–§3 and the SpecKit spec
`specs/002-work-management-operator/spec.md`.

**Exit criteria:** baseline gates run and recorded (`pytest`, `ruff`, CLI help,
`evals/run_evals.py`).

---

## Phase 1 — Foundation *(this pass)*

**Scope:** prove the architecture with the smallest read-only vertical slice.

**Deliverables**

1. `obsidian_inventory`: typed frontmatter reader preserving lists/nested maps,
   exposed on `IndexRecord` (optional, defaulted). Existing callers unchanged.
2. `obsidian_operator` package: typed models + enums for project/person/ticket/
   meeting/action.
3. Schema detection (`type:` recognition) and validation with clear errors.
4. Read-only repository built from `build_index(vault, "vault")`, filtered by type.
5. Read-only CLI: `project list|show`, `person show`, `ticket list|show`,
   `action list` (`--vault`, `--json`).
6. Representative fixtures (valid, malformed, unknown-link, external-ref notes).
7. Tests: schema recognition, valid/invalid frontmatter, relationships, unknown
   links, external IDs, status enums, list/show, **no writes during read-only ops**.

**Non-goals:** writes, GUI, MCP, adapters, DB, review/attention logic.

**Exit criteria:** new tests pass; existing Librarian/Patron/Inventory tests stay
green; `ruff` clean for `src`/`tests`; deterministic output.

---

## Phase 2 — Operator CLI and relationship logic *(implemented)*

**Scope:** turn the read-only repository into useful management queries.

**Deliverables**

- Relationship queries: person → assignments/tickets/actions; project → people/
  meetings/decisions/actions/tickets.
- Stale/attention detection (not reviewed recently, waiting too long, manager
  attention, blocked).
- `review today|team|projects` read-only output, plus `project review <name>` and
  `person workload <name>`.
- Deterministic ordering, injectable `--today`, and machine-readable (`--json`) output.

**Non-goals:** writing state, generating vault files.

**Exit criteria:** attention/staleness rules covered by tests; output stable
across repeated runs.

**Delivered:** `relationships.py`, `review.py`, `config.py`, `dates.py`;
`review today|team|projects`, `project review`, `person workload`; threshold
config; tests in `tests/test_operator_relationships.py`,
`tests/test_operator_review.py`, `tests/test_operator_cli_review.py`.

---

## Phase 3 — Generated management views *(implemented)*

**Deliverables**

- Generated `Views/` artifacts: Today, Projects, Team, Tickets Needing Attention,
  Waiting on Others, Manager Review.
- Each view is reproducible, cites its source notes, and is marked generated
  (never hand-edited). Writing these views is the **first** operator write path
  and must be staging-first with a containment test (constitution Principle VI).

**Non-goals:** no GUI, no external adapters.

**Exit criteria:** views regenerate deterministically; no canonical note mutated;
containment test proves writes stay in the views/staging boundary.

**Delivered:** `views.py`, `writer.py`; CLI `view list` and
`view render <name>|--all [--write] [--force] [--out] [--today] [--generated-at]
[--json]`; generated-provenance frontmatter; contained, overwrite-protected,
staging-first writer under `<vault>/90_Staging/Views/`; tests in
`tests/test_operator_views.py`, `tests/test_operator_view_writer.py`,
`tests/test_operator_cli_views.py`, and extended `tests/test_operator_no_writes.py`.

---

## Phase 4 — GUI management workspace *(implemented)*

**Deliverables**

- Navigation: Today / Projects / Team / Tickets / Inbox / Search / Review / Settings.
- Dashboards, entity detail, safe state updates with visible change sets and
  confirmation gates.
- Thin controllers reusing Operator services; no duplicated business logic.

**Non-goals:** no new business rules in the GUI.

**Exit criteria:** GUI actions show their equivalent CLI command; write actions
require explicit confirmation; read-only actions run directly.

**Delivered:** `obsidian_operator/gui/{service,server}.py` and the self-contained
`static/index.html`; a tokenized `ThreadingHTTPServer` exposing read endpoints
(`/api/health`, `/api/overview`, `/api/today`, `/api/projects`, `/api/team`,
`/api/entity`, `/api/views`), a no-write `/api/view/preview`, and a gated
`/api/view/render` behind explicit confirmation; boundary and no-write coverage
in `tests/test_operator_gui_import_boundary.py` and
`tests/test_operator_no_writes.py`.

---

## Phase 5 — External system adapters

**Deliverables**

- Adapters for ServiceDesk Plus, meeting/transcript sources, Planner/Wrike.
- Adapters translate external payloads into operator schemas at the edge; they do
  not own vault models. `sync_mode` (reference/snapshot/managed-locally/generated)
  governs how much is cached.
- Explicit, opt-in synchronization only; no background daemon.

**Non-goals:** making Obsidian authoritative for external state.

**Exit criteria:** each adapter is isolated, network-optional, and degrades to a
deterministic result when unavailable.

---

## Phase 6 — Agent/MCP actions

**Deliverables**

- Read-only-first MCP tools: `project_list`, `project_read`, `project_health`,
  `person_read`, `person_workload`, `ticket_read`, `ticket_search`, `action_list`,
  `review_today`, `review_team`, `review_projects`, `review_waiting`.
- Any mutating tool requires an explicit, spec'd mutation policy with
  confirmation and audit.

**Non-goals:** autonomous trusted-vault mutation.

**Exit criteria:** MCP tools call the same retrieval layer as the CLI; mutation
policy documented and tested before any write tool ships.

---

## Deferred by design

- Vector retrieval / embeddings.
- Agents SDK runtime inside the deterministic core.
- Full external-system mirroring.
- A database.

## Sequencing note

Phases 3–6 each introduce new write or integration surfaces. Per the repository
constitution, each must be specified as opt-in work with its own spec, plan,
tasks, and containment tests **before** implementation. Phase 1 introduces none.
