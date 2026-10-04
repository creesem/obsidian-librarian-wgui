# Feature Specification: Work Management Operator Foundation

**Feature Branch**: `codex/work-management-phase-1`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Introduce `obsidian_operator` as a read-only work-management
domain layer over a separate Obsidian management vault: typed operational schemas
(project, person, ticket, meeting, action), schema recognition, validation, and
read-only list/show commands, reusing the shared inventory scanner. No writes, GUI,
MCP, adapters, or database in this phase."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - List and Inspect Operational Entities (Priority: P1)

A user points the operator at a management vault and lists its projects, people,
tickets, and actions, then shows a single entity's details.

**Why this priority**: This is the smallest useful management behavior — seeing
what exists without changing anything.

**Independent Test**: Run list/show against a fixture vault with known entities and
assert the returned entities, fields, and source paths; assert every fixture file is
byte-unchanged afterwards.

**Acceptance Scenarios**:

1. **Given** a management vault with valid project/person/ticket/action notes,
   **When** the user runs `project list`, **Then** each project's title, status,
   priority, health, and source path are listed in stable order.
2. **Given** a known entity, **When** the user runs `project show <name>`,
   **Then** its parsed fields, relationships, and validation warnings are shown.
3. **Given** a note whose `type` is absent or unknown, **When** listing, **Then**
   the note is skipped and does not appear as an entity.

---

### User Story 2 - Recognize and Validate Operational Schemas (Priority: P2)

A user runs validation and receives clear, deterministic errors for malformed
operational notes, while unrelated notes still process.

**Why this priority**: Trustworthy management output depends on schema discipline
and visible failure modes.

**Independent Test**: Validate a fixture set mixing valid notes, missing-status
notes, bad enum values, and malformed frontmatter; assert exact issues and that
processing continues.

**Acceptance Scenarios**:

1. **Given** a ticket with `sync_mode: reference` but no `external_id`, **When**
   validated, **Then** an error is reported naming the missing field.
2. **Given** an action with `status: waiting` but no `waiting_on`, **When**
   validated, **Then** an error is reported.
3. **Given** a note with malformed frontmatter, **When** validated, **Then** that
   note is reported and other notes are still processed.

---

### User Story 3 - Resolve Relationships Without Guessing (Priority: P3)

A user sees which entities a note links to, and unresolved links are reported as
warnings rather than invented.

**Why this priority**: Relationships are the system's core value; they must be
explicit and trustworthy.

**Independent Test**: Link an entity to a known person and to an unknown name;
assert the known link resolves and the unknown one is a warning.

**Acceptance Scenarios**:

1. **Given** a ticket assigned to `[[Venkat Rao]]` and a matching person note,
   **When** shown, **Then** the assignee resolves to that person.
2. **Given** a project referencing `[[Nobody Here]]`, **When** shown, **Then** the
   link is reported as `unresolved_link` and no entity is fabricated.

---

### Edge Cases

- Vault path does not exist.
- Vault contains no operational entities.
- Duplicate entity titles/aliases across different files.
- `people`/`systems` supplied as YAML block list, flow list, or scalar.
- Frontmatter present but not well-formed (`---` missing a close).
- Boolean-like `manager_attention` values (`true`, `True`, `"yes"`).
- External reference present without `sync_mode`.
- A note in the management vault that is not an operator entity (e.g. a daily note).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a new package `obsidian_operator` that depends only on `obsidian_inventory`.
- **FR-002**: System MUST define typed models and enums for `project`, `person`, `ticket`, `meeting`, and `action`.
- **FR-003**: System MUST detect an entity by its `type:` frontmatter value and skip notes that are not operator entities.
- **FR-004**: System MUST read frontmatter faithfully, preserving YAML lists and nested maps.
- **FR-005**: System MUST validate required fields, enum values, and conditional rules (ticket external refs, action `waiting`/`done`).
- **FR-006**: System MUST report malformed notes and unresolved wikilinks without aborting processing of other notes.
- **FR-007**: System MUST provide read-only `list` and `show` commands for projects, people, tickets, and actions.
- **FR-008**: System MUST preserve raw vault files unchanged; Phase 1 introduces no write path.
- **FR-009**: System MUST produce stable, deterministic output ordering and support machine-readable output.
- **FR-010**: System MUST NOT call external APIs, LLMs, embeddings, OCR, MCP tools, or Agents SDK runtime.
- **FR-011**: System MUST NOT mutate, promote, or create vault notes.
- **FR-012**: System MUST reuse the shared scanner rather than adding a second parser.

### Key Entities

- **Operational entity**: a note carrying `type` ∈ {project, person, ticket, meeting, action} with parsed typed fields and source path.
- **Relationship link**: a wikilink field resolved against known entities, or reported as `unresolved_link`.
- **Validation issue**: a path, message, severity (`error`/`warning`), and rule identifier.
- **Operator index**: the read-only view of all operational entities in a vault, built from the shared inventory index.

### Safety and Provenance Requirements *(mandatory for this repository)*

- **Write boundary**: Phase 1 writes no vault or source files. There is no new write path.
- **Overwrite policy**: not applicable (no writes).
- **Source provenance**: every entity exposes its vault-relative source path; derived output cites it.
- **Uncertainty handling**: malformed notes, unknown enum values, and unresolved links are surfaced, never guessed.
- **Review report**: list/show output names counts, skipped notes, warnings, and errors.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Fixture tests list the expected entities with zero source file modifications.
- **SC-002**: Fixture tests report the exact expected validation issues for invalid notes and still process valid ones.
- **SC-003**: Unknown wikilink targets produce warnings and never create entities.
- **SC-004**: Repeated runs over unchanged fixtures produce identical ordering and fields.
- **SC-005**: `obsidian_operator` imports `obsidian_inventory` only — verified by an import-boundary test.
- **SC-006**: Existing Librarian/Patron/Inventory tests remain green.

## Assumptions

- Operator targets a separate management vault; folder layout is convention and `type:` is canonical.
- Phase 1 filters the existing `vault` scope by frontmatter type rather than adding new scopes.
- Frontmatter is parsed with the project's existing YAML dependency (PyYAML), reused through the inventory package.
- No database; filesystem Markdown remains the data format.

## Phase 2 Addendum — Review and Relationships *(implemented)*

### User Story 4 - Management Review Queues (Priority: P4)

A manager runs read-only review commands to see what needs attention: overdue
actions, blocked work, waiting items, manager-flagged tickets, stale projects,
and per-person/project rollups.

**Independent Test**: Run `review today|team|projects`, `project review`, and
`person workload` against a fixture vault with an explicit `--today`; assert the
expected attention kinds and rollups, and that files are unchanged.

**Acceptance Scenarios**:

1. **Given** an action past its due date, **When** `review today` runs, **Then** an
   `overdue_action` high-severity item is reported.
2. **Given** a project whose `next_review` has passed, **When** reviewing, **Then**
   a `review_due` item is reported; a project never reviewed is `stale_review`.
3. **Given** a ticket flagged `manager_attention`, **When** reviewing, **Then** a
   high-severity `manager_attention` item is reported unless the ticket is closed.
4. **Given** a project and its related tickets/actions/meetings, **When**
   `project review` runs, **Then** the rollup lists related entities and blockers.
5. **Given** an explicit `--today`, **When** any review command runs twice, **Then**
   output is byte-identical.

### Additional Functional Requirements

- **FR-013**: System MUST provide relationship queries for projects and people derived only from resolved wikilinks.
- **FR-014**: System MUST compute attention signals (blocked, overdue, manager attention, waiting, review due, stale review, stale ticket, unassigned ticket) deterministically from an injected reference date.
- **FR-015**: System MUST provide read-only `review today|team|projects`, `project review`, and `person workload` commands with text and JSON output.
- **FR-016**: System MUST NOT write or generate vault files in these commands.

### Additional Success Criteria

- **SC-007**: Attention kinds are covered by unit tests over synthetic entities and by fixture integration tests.
- **SC-008**: Review output is stable across repeated runs with the same `--today`.
- **SC-009**: Relationship resolution never fabricates an entity for an unresolved link.
