# Feature Specification: GUI Management Workspace

**Feature Branch**: `codex/work-management-phase-4`

**Created**: 2026-10-04

**Status**: Implemented

**Input**: User description: "A local, tokenized, stdlib-only browser workspace over
the operator's read-only services, with a gated path to regenerate the generated
views under `90_Staging/Views/`. No canonical note is ever created, moved,
modified, or deleted."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Management Views Read-Only (Priority: P1)

A user opens the operator GUI and reads the management picture — attention
queues, project and team rollups — without anything being written.

**Why this priority**: The workspace's core value is reading operator state; it
must be safe to open and explore with zero writes.

**Independent Test**: Start a server against a fixture vault, request
`/api/overview`, `/api/today`, `/api/projects`, `/api/team`, `/api/entity`, assert
the expected shapes are returned and every vault file is byte-unchanged.

**Acceptance Scenarios**:

1. **Given** a fixture vault, **When** the user opens the workspace, **Then**
   Today, Projects, Team, Tickets, Waiting, Manager Review, and Views sections are
   available and render their data.
2. **Given** any read-only request, **Then** no file under the vault is created,
   modified, or deleted.

---

### User Story 2 - Preview and Generate Views Safely (Priority: P2)

A user previews a generated view, then regenerates the views through a
confirmation gate, seeing the change set and the equivalent CLI command.

**Why this priority**: This is the only write in the phase; containment,
confirmation, and a visible change set are the whole point.

**Independent Test**: POST `/api/view/render` without `confirmed`, assert
`needs_confirmation` and no file written; POST with `confirmed`, assert each view
exists under the views root with generated frontmatter and canonical files are
byte-unchanged.

**Acceptance Scenarios**:

1. **Given** an unconfirmed render request, **When** submitted, **Then** the
   response is `needs_confirmation`, carries the equivalent CLI command, and no
   file is written.
2. **Given** a confirmed render request, **When** submitted, **Then** each view is
   written under `90_Staging/Views/` and the response carries the created change
   set.
3. **Given** an existing view and no force, **When** rendering, **Then** the write
   is refused and the existing file is unchanged.

---

### User Story 3 - Tokenized Local Access (Priority: P3)

A user's workspace is protected by a per-run token; requests without it are
refused.

**Why this priority**: The server is local but must not be drive-by reachable
from another local process or page.

**Independent Test**: Request any `/api/*` route without the token and with a
wrong token; assert 401 both times.

**Acceptance Scenarios**:

1. **Given** a running server, **When** a request omits `X-Gui-Token`, **Then**
   the response is 401 and no data or write occurs.
2. **Given** a running server, **When** a request presents the correct token,
   **Then** the route responds normally.

---

### Edge Cases

- Empty vault (no entities): sections render zero items, not an error.
- Vault path does not exist: server startup reports the error; requests error
  cleanly.
- Unknown entity name or view name: reported as an error, no write.
- Render `--out`/target resolves outside the vault: refused.
- Existing view file without force: refused.
- Static shell: no external assets (no `<script src=`, `<link href=`, CDN).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a local HTTP workspace served by a per-run
  token; every `/api/*` route MUST require `X-Gui-Token` and return 401 otherwise.
- **FR-002**: The workspace MUST expose read-only navigation: Today, Projects,
  Team, Tickets, Waiting, Manager Review, Views.
- **FR-003**: Read-only endpoints (`/api/health`, `/api/overview`, `/api/today`,
  `/api/projects`, `/api/team`, `/api/entity`, `/api/views`) MUST write nothing.
- **FR-004**: `POST /api/view/preview` MUST return rendered view markdown and
  write nothing.
- **FR-005**: `POST /api/view/render` MUST write nothing unless `confirmed` is
  true; unconfirmed requests MUST return `needs_confirmation`.
- **FR-006**: Writes MUST be confined to `<vault>/90_Staging/Views/` (or a
  contained `--out`) via the existing `write_view`; absolute paths and `..` MUST
  be refused.
- **FR-007**: Existing view files MUST be refused unless force is set explicitly;
  the GUI MUST set force only through an explicit, separately confirmed overwrite
  action, never as a silent default.
- **FR-008**: Every render result MUST carry the exact equivalent
  `obsidian-operator view render` CLI command.
- **FR-009**: A confirmed render MUST report the created/overwritten change set.
- **FR-010**: The system MUST NOT create, move, modify, or delete any canonical/
  trusted note.
- **FR-011**: The system MUST NOT call external APIs, LLMs, embeddings, OCR, MCP
  tools, or Agents SDK runtime, and MUST add no runtime dependency beyond stdlib.
- **FR-012**: `obsidian_operator.gui` MUST import only `obsidian_operator` and the
  standard library; `obsidian_operator` MUST continue to import only
  `obsidian_inventory`.
- **FR-013**: The static shell MUST be self-contained (no external assets).
- **FR-014**: Content MUST derive only from existing operator services
  (`attention_items`, `build_project_review`, `build_person_workload`,
  `build_view`); no new business rules.
- **FR-015**: The GUI MUST be launchable via an `obsidian-operator-gui` entry point
  with `--vault`, `--host`, `--port`, `--no-browser`.

### Key Entities

- **Workspace server**: tokenized HTTP server exposing read endpoints and the
  gated view-render endpoint.
- **Service function**: a pure operator query or the gated render seam; no HTTP
  knowledge.
- **Render result**: status, change set (paths, created/overwritten), and
  equivalent CLI command.

### Safety and Provenance Requirements *(mandatory for this repository)*

- **Write boundary**: generated views only, under the contained views root. No
  canonical folder is ever a write target.
- **Overwrite policy**: refused by default; force is explicit, confirmed, and
  reported.
- **Source provenance**: written views carry the generated frontmatter from
  `docs/73`, including `sources`/`source_count`.
- **Uncertainty handling**: validation issues and unresolved links surface in the
  overview and entity detail; the GUI invents no data.
- **Review report**: the render response reports the change set and equivalent
  CLI command.
- **Constitution gate (Phase VI)**: this is a vault-mutation surface, so it is
  specified before implementation and covered by containment/no-write tests.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Read-only endpoints leave the fixture vault byte-unchanged.
- **SC-002**: Correct-token requests succeed; missing/wrong token returns 401.
- **SC-003**: An unconfirmed render writes nothing and returns `needs_confirmation`.
- **SC-004**: A confirmed render writes only under `90_Staging/Views/`; canonical
  files are byte-unchanged.
- **SC-005**: The gui import-boundary test passes (gui imports only operator;
  importing it loads neither librarian nor patron).
- **SC-006**: The static shell contains no external assets.
- **SC-007**: `pytest`, `ruff check src tests`, both CLI `--help`, and
  `evals/run_evals.py` are green; phases 1–3 stay green.

## Assumptions

- The workspace is a leaf consumer; operator core never imports the GUI.
- Generated views are derived state and never canonical.
- The existing Librarian GUI's server/confirmation pattern is the reference for
  containment and gating.
- No database; Markdown remains the format.
