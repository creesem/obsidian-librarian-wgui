# 71 — Operational Note Schemas

Status: Proposed (Phase 1 foundation).

Defines the five core operational entities for `obsidian_operator`: **project**,
**person**, **ticket**, **meeting**, and **action**. Deliberately small; no
schema proliferation. Read `docs/70_work_management_architecture.md` first.

The `type:` frontmatter value selects the schema. A note whose `type` is absent
or not one of these five is **not** an operator entity and is skipped (not an
error).

---

## 1. Schema principles

- One required selector: `type`.
- Every entity carries a `status` from a closed enum.
- **State is separated** into four kinds (§2) so source evidence is never
  confused with the user's judgment or with external-system state.
- Frontmatter stays simple and machine-checkable; block lists are preserved by the
  typed reader (see `docs/70` §3).
- Unknown fields are ignored, not errors (forward-compatible).
- Unresolved wikilinks and malformed notes are **reported as warnings**, never
  guessed or silently dropped.
- No operator note is written by Phase 1 code.

---

## 2. State separation (applies to every schema)

| State kind | Meaning | Examples | Who owns it |
|---|---|---|---|
| **source_state** | Where the content came from; immutable evidence | `source_system`, `external_id`, `external_url`, `sync_mode`, `last_synced`, `source_path`, `ingest_run_id` | External / ingest |
| **management_state** | The user's current judgment and cadence | `status`, `priority`, `health`, `owner`, `manager_attention`, `next_action`, `last_reviewed`, `next_review` | The user |
| **external_state** | Fields mirrored from an external system, namespaced and non-authoritative | `external_status`, `external_assignee` | External (read-only here) |
| **derived_state** | Computed signals and rollups; never stored in canonical notes | attention flags, staleness, workload counts | Operator (generated) |

**Rule:** a canonical note may contain source_state and management_state. It must
**not** contain derived_state; that belongs in generated views. external_state may
be present but is clearly namespaced and never overrides management_state.

---

## 3. Shared conventions

### Common fields

- **Required (all types):** `type`, `status`.
- **Optional (all types):** `aliases`, `tags`, `owner` (wikilink), `created`,
  `updated`, `last_reviewed`, `next_review`, `source_system`, `external_id`,
  `external_url`, `sync_mode`, `last_synced`.

### Enums

| Field | Values |
|---|---|
| `type` | `project`, `person`, `ticket`, `meeting`, `action` |
| `priority` | `P1`, `P2`, `P3`, `P4` |
| `health` | `green`, `yellow`, `red` |
| `effort` | `S`, `M`, `L`, `XL` |
| `sync_mode` | `reference`, `snapshot`, `managed-locally`, `generated` |
| `manager_attention` | `true`, `false` |

Per-type `status` enums are listed with each schema.

### Timestamps

ISO 8601. Date-only (`2026-10-03`) is valid for review/cadence fields; full
timestamps (`2026-10-03T14:00:00+00:00`) are valid for lifecycle/freshness fields.

- `created`, `updated` — note lifecycle.
- `last_reviewed`, `next_review` — management cadence.
- `last_synced`, `last_checked` — external freshness.

### Link conventions

- Relationships use Obsidian wikilinks: `owner: "[[Alex Rivera]]"`,
  `people: ["[[Alex Rivera]]", "[[Sam Okafor]]"]`.
- Identity resolution matches a wikilink target against an entity's title or
  `aliases` using the shared normalizer (`normalize_wikilink_target`).
- An unresolved target produces a **warning** (`unresolved_link`), not an error.
- Multi-valued relationship fields are YAML block or flow lists; the typed reader
  preserves them.

### External identifiers

- Canonical external key is the pair `source_system` + `external_id`.
- `sync_mode` declares intent: `reference` (pointer only), `snapshot` (cached copy),
  `managed-locally` (no external authority), `generated` (produced by tooling).
- No synchronization is implemented in Phase 1; these fields are metadata only.

### Archival

- Terminal statuses: project `done`/`archived`; person `inactive`; ticket
  `resolved`/`closed`; action `done`/`cancelled`; meeting `held`/`cancelled`.
- Archived notes are **never deleted**; they are excluded from default active views.

---

## 4. `project`

**Purpose:** a body of work with a health, owner, cadence, and related people,
systems, tickets, and evidence.

**Required frontmatter**

- `type: project`
- `status` ∈ {`active`, `paused`, `blocked`, `done`, `archived`}
- `owner` (wikilink to a person)
- `priority` ∈ P1–P4
- `health` ∈ {`green`, `yellow`, `red`}

**Optional frontmatter**

- `portfolio`, `effort`, `people` (list of wikilinks), `systems` (list),
  `next_action`, `last_reviewed`, `next_review`, `source_*`, `tags`, `aliases`.

**Relationships**

- → people (`owner`, `people`)
- → tickets (ticket `project:` backlink)
- → meetings, decisions, actions, risks, source evidence (via links/sections)

**Validation rules**

- `status`, `priority`, `health` must be in enum.
- `owner` should resolve to a `person`; unresolved → warning.
- If both `last_reviewed` and `next_review` present, `next_review` ≥ `last_reviewed`.
- `health` is management_state (user-set), never computed into the note.

**Example**

```yaml
---
type: project
status: active
owner: "[[Alex Rivera]]"
priority: P1
health: yellow
portfolio: strategic-projects
effort: L
people:
  - "[[Sam Okafor]]"
  - "[[Dana Lee]]"
systems:
  - CareLogic
  - Snowflake
last_reviewed: 2026-10-03
next_review: 2026-10-06
---
# CareLogic Automation

## Summary
...

## Next action
Confirm interface scope with vendor.
```

**Lifecycle:** created (`active`) → reviewed on cadence (`last_reviewed`/`next_review`)
→ `paused`/`blocked` as needed → `done` → `archived`.

---

## 5. `person`

**Purpose:** canonical identity/profile note plus generated rollups. It is **not**
a manually maintained diary.

**Required frontmatter**

- `type: person`
- `status` ∈ {`active`, `inactive`}

**Optional frontmatter**

- `role`, `team`, `manager` (wikilink), `email`, `aliases`, `tags`.

**Relationships**

- ← projects (`owner`, `people`), tickets (`assignee`), actions (`owner`),
  meetings (`attendees`), 1:1 notes.
- Rollups (active assignments, open follow-ups, related tickets, recent 1:1s,
  coaching items, recent wins, manager-attention items) are **derived**, not stored.

**Validation rules**

- `status` in enum.
- Profile fields are optional; missing profile data is not an error.
- Storing rollups in the note is discouraged (they are derived_state).

**Example**

```yaml
---
type: person
status: active
role: Application Analyst
team: Clinical Systems
manager: "[[Alex Rivera]]"
aliases:
  - Venkat R.
---
# Venkat Rao

## Profile
...
```

**Lifecycle:** created (`active`) → `inactive` on departure. Never deleted.

---

## 6. `ticket`

**Purpose:** a manager-significant ticket, snapshot, escalation, project-linked
issue, or follow-up — **not** a full mirror of an external system.

**Required frontmatter**

- `type: ticket`
- `status` ∈ {`open`, `in_progress`, `waiting`, `blocked`, `escalated`, `resolved`, `closed`}
- If `sync_mode` ∈ {`reference`, `snapshot`}: also require `source_system` and `external_id`.

**Optional frontmatter**

- `priority`, `assignee` (wikilink), `application`, `project` (wikilink),
  `next_action`, `manager_attention`, `last_checked`, `external_url`, `sync_mode`,
  `external_status` (namespaced external_state), `tags`.

**Relationships**

- → person (`assignee`)
- → project (`project`)
- → application, meeting(s) where discussed, next action.

**Validation rules**

- `status` in enum; `priority` in enum if present.
- Conditional external requirement above (reference/snapshot without
  `source_system`+`external_id` → error).
- `sync_mode` in enum if present.
- `manager_attention` must parse as boolean.

**Example**

```yaml
---
type: ticket
status: waiting
priority: P2
source_system: servicedesk-plus
external_id: "31814"
sync_mode: reference
assignee: "[[Venkat Rao]]"
application: SureMobile
project: "[[CareLogic Automation]]"
next_action: Follow up with vendor
manager_attention: true
last_checked: 2026-10-03
---
# SD-31814 — SureMobile sync failure

## Context
...
```

**Lifecycle:** `open` → `in_progress` → (`waiting`/`blocked`/`escalated`) →
`resolved` → `closed`. External state may change independently; local
management_state (`next_action`, `manager_attention`) is user-owned.

---

## 7. `meeting`

**Purpose:** a structured meeting record carrying deterministic sections for
decisions, actions, and risks.

**Required frontmatter**

- `type: meeting`
- `status` ∈ {`scheduled`, `held`, `cancelled`}
- `date` (ISO 8601)

**Optional frontmatter**

- `attendees` (list of wikilinks), `project` (wikilink), `source_system`,
  `external_id`, `sync_mode`, `tags`.

**Relationships**

- → people (`attendees`), project, decisions, actions, source transcript/evidence.

**Validation rules**

- `status` in enum; `date` parses as ISO 8601.
- `attendees` that do not resolve → warning.
- If `source_system` present, `sync_mode` should be declared (warning if absent).

**Example**

```yaml
---
type: meeting
status: held
date: 2026-10-02
attendees:
  - "[[Alex Rivera]]"
  - "[[Dana Lee]]"
project: "[[CareLogic Automation]]"
---
# CareLogic vendor sync — 2026-10-02

## Decisions
- ...

## Actions
- ...

## Risks and blockers
- ...
```

**Lifecycle:** `scheduled` → `held` (record decisions/actions/risks) or `cancelled`.

---

## 8. `action`

**Purpose:** a follow-up or delegated work item created by hand, from a claim, or
by extraction.

**Required frontmatter**

- `type: action`
- `status` ∈ {`open`, `in_progress`, `waiting`, `done`, `cancelled`}

**Optional frontmatter**

- `owner` (wikilink), `due` (ISO 8601), `project` (wikilink),
  `related_ticket` (wikilink or external id), `waiting_on`, `next_action`,
  `completed` (timestamp), `tags`.

**Relationships**

- → person (`owner`), project, ticket, meeting where created.

**Validation rules**

- `status` in enum.
- If `status: waiting` → `waiting_on` required.
- If `status: done` → `completed` required.
- `due`/`completed` parse as ISO 8601.

**Example**

```yaml
---
type: action
status: waiting
owner: "[[Sam Okafor]]"
due: 2026-10-07
project: "[[CareLogic Automation]]"
related_ticket: "[[SD-31814]]"
waiting_on: Vendor response
---
# Chase vendor on interface scope
```

**Lifecycle:** `open` → `in_progress` → (`waiting`) → `done`/`cancelled`.

---

## 9. Validation rule summary

| Rule | Severity |
|---|---|
| Missing `type` | skip (not an operator entity) |
| Unknown `type` | skip (not an operator entity) |
| Missing `status` | error |
| `status`/`priority`/`health`/`effort`/`sync_mode` outside enum | error |
| Malformed frontmatter block | error (note reported, others continue) |
| ticket reference/snapshot without `source_system`+`external_id` | error |
| action `waiting` without `waiting_on` | error |
| action `done` without `completed` | error |
| `next_review` before `last_reviewed` | error |
| Unresolved wikilink target | warning |
| `source_system` without `sync_mode` (meeting) | warning |
| Unknown frontmatter fields | ignored |

A malformed note must never abort processing of unrelated notes.
