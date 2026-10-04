# 73 — Generated Management Views

Status: Implemented (Phase 3).

Defines the generated view contract for `obsidian_operator`: how Phase 2 reviews
become reproducible Markdown documents, where they are written, and why they are
never canonical. Read `docs/70_work_management_architecture.md` and
`docs/72_operator_roadmap.md` (Phase 3) first.

---

## 1. What a generated view is

A **generated view** is a Markdown document computed from the operator index on
demand. It is *derived state* (`docs/70` §7): reproducible, replaceable, and never
the source of truth. If a view disagrees with a canonical note, the canonical note
wins.

Views are produced by `obsidian-operator view render`. Rendering prints to stdout
by default; writing requires an explicit `--write`.

---

## 2. View set

| name | output file | body source |
|---|---|---|
| `today` | `Today.md` | all attention items (`attention_items`) |
| `projects` | `Projects.md` | per active project (`build_project_review`) |
| `team` | `Team.md` | per active person (`build_person_workload`) |
| `tickets` | `Tickets Needing Attention.md` | ticket attention items |
| `waiting` | `Waiting on Others.md` | waiting attention items |
| `manager-review` | `Manager Review.md` | high-severity attention items |

Bodies reuse the deterministic Phase 2 text renderers. No new business rules are
introduced by views.

---

## 3. Generated frontmatter contract

Every written view carries this frontmatter:

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

| field | meaning |
|---|---|
| `type` | Always `view`. Not an operator entity; `obsidian_operator` skips it. |
| `generated` | Always `true`; marks the file as machine-produced. |
| `generator` | Producing tool, for provenance. |
| `view` | View name from §2. |
| `generated_at` | ISO 8601 UTC timestamp; the only non-deterministic field unless pinned. |
| `reference_date` | The `--today` value the attention rules ran against. |
| `source_count` | Number of contributing entity paths. |
| `sources` | Vault-relative paths of the entities the view was derived from. |

`type: view` is deliberately outside the five operator entity types, so a generated
view that lands inside the scanned scope is skipped rather than reported malformed.

---

## 4. Write policy (staging-first)

- **Default views root**: `<vault>/90_Staging/Views/`.
- **`--out DIR`**: relocates the root, but the resolved path MUST remain under the vault.
- **Containment**: every write is checked against both the vault root and the views
  root (`ensure_under`); absolute paths and `..` are refused.
- **Overwrite**: refused by default. `--force` overwrites explicitly and the change
  set is reported. Views are regenerated, not renamed.
- **No canonical writes**: the writer only creates files under the views root. It
  never creates, moves, modifies, or deletes a canonical or trusted note.

### Why `90_Staging`

`scanner.scope_for_path` maps `90_Staging/` to the `staging` scope, and Operator
indexes only the `vault` scope. Generated views therefore never appear in
Operator's own entity index, and they sit in the repository's established review
zone rather than beside canonical notes.

---

## 5. Reproducibility

- Content is deterministic given fixed `--today` and `--generated-at`.
- Without `--generated-at`, the current UTC time is used and only that field varies.
- `--json` emits the same content plus the change set, for tooling.

---

## 6. Command surface

```text
obsidian-operator view list
obsidian-operator view render <name> | --all
    [--write] [--force] [--out DIR]
    [--today YYYY-MM-DD] [--generated-at ISO8601] [--json]
```

Exit codes: `0` ok; `1` vault validation errors; `2` usage/IO/containment errors.

---

## 7. Validation rules

| Rule | Severity |
|---|---|
| Target resolves outside the vault or views root | error (refuse) |
| Absolute path or `..` in target | error (refuse) |
| Existing target without `--force` | error (refuse) |
| Unknown view name | error |
| Unparseable `--today` / `--generated-at` | error |
| Empty vault | not an error (renders zero items) |
