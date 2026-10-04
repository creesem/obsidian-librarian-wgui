# 74 — GUI Management Workspace

Status: Implemented (Phase 4).

Defines the `obsidian_operator` GUI workspace: a local, tokenized, stdlib-only
browser view over the operator's read-only services, plus a gated path to
regenerate the generated views. Read `docs/70_work_management_architecture.md`
and `docs/72_operator_roadmap.md` (Phase 4) first.

---

## 1. What the workspace is

A **thin controller** (docs/70 §5): navigation, dashboards, entity detail, and
confirmation gates. It reuses the operator's existing services and adds **no**
business rules. Every panel is either a deterministic read (a query the CLI
already exposes) or the existing `view render --write` seam behind a
confirmation gate.

The workspace never reads or writes a canonical note on its own authority; it
renders operator index data and, when the user confirms, regenerates derived
views under `90_Staging/Views/`.

---

## 2. Package and dependency shape

```text
src/obsidian_operator/gui/
├── __init__.py
├── service.py          # read-only queries + gated view-render seam
├── server.py           # tokenized ThreadingHTTPServer + JSON endpoints + static shell
└── static/index.html   # self-contained, no external assets
```

Entry point: `obsidian-operator-gui = "obsidian_operator.gui.server:main"`.

**Dependency rule (enforced):** `obsidian_operator.gui` imports only
`obsidian_operator` and the standard library. It must not import
`obsidian_librarian`, `obsidian_patron`, or their GUI. Operator core still
imports only `obsidian_inventory`; the GUI is a leaf consumer, as
`docs/70` §4 specifies. A boundary test extends the existing import-discipline
check to the `gui` subpackage.

---

## 3. Navigation

| section | source |
|---|---|
| Today | `attention_items` |
| Projects | `build_project_review` over `active_projects` |
| Team | `build_person_workload` over `active_people` |
| Tickets | ticket attention items |
| Waiting | waiting attention items |
| Manager Review | high-severity attention items |
| Views | the six generated views (`VIEWS`) |

Inbox, Search, and Settings are deliberately excluded: they belong to
Librarian/inventory, not Operator.

---

## 4. Service layer

Pure functions over `OperatorIndex`; no HTTP knowledge; deterministic; reusing
existing operator services.

| function | returns |
|---|---|
| `overview(vault, today)` | index counts + validation issues |
| `today(vault, today)` | attention items |
| `project_board(vault, today)` | per active project rollups |
| `team_board(vault, today)` | per active person rollups |
| `entity_detail(vault, type, name, today)` | one entity + relationships + issues |
| `view_definitions()` | view names/filenames from `VIEWS` |
| `preview_view(vault, name, today, generated_at)` | rendered view, no write |
| `render_view(request)` | gated write; change set or `needs_confirmation` |

Safety tiers use the existing GUI vocabulary (`read-only`, `staging-write`).
`render_view` is `staging-write` and refuses to write unless `confirmed=True`.
Every render result carries the exact `obsidian-operator view render ...`
command as `equivalent_cli`, satisfying the roadmap exit criterion that GUI
actions show their equivalent CLI command.

---

## 5. Endpoints

Same pattern as the existing Librarian GUI: `ThreadingHTTPServer`, random port,
per-run token, `X-Gui-Token` required on every `/api/*` route (401 otherwise),
quiet logging, `create_server(...) -> (httpd, token, url)` for tests.

| method | path | purpose |
|---|---|---|
| GET | `/` | static shell with injected bootstrap |
| GET | `/api/health` | status, vault, host/port |
| GET | `/api/overview` | counts + issues |
| GET | `/api/today` | attention items |
| GET | `/api/projects` | project board |
| GET | `/api/team` | team board |
| GET | `/api/entity` | one entity detail (`type`, `name`) |
| GET | `/api/views` | view definitions |
| POST | `/api/view/preview` | rendered markdown; nothing written |
| POST | `/api/view/render` | gated write (`confirmed`); returns change set |

CLI: `--vault`, `--host`, `--port`, `--no-browser`.

---

## 6. Frontend

Single self-contained `static/index.html`. No external assets: `<script src=`,
`<link href=`, font CDNs, and generic CDNs are all forbidden (matching the
existing static test).

Nav renders the seven sections. Read sections display the corresponding
endpoint's data deterministically. The Views section lists the six views,
previews any view, and offers "Generate views", which routes through the
confirmation modal and then shows the returned change set and equivalent CLI.
Tickets, Waiting, and Manager Review each fetch their own endpoint
(`/api/tickets`, `/api/waiting`, `/api/manager-review`); the frontend filters
nothing itself.

---

## 7. Write policy

- The only write is view regeneration through `render_view` →
  `obsidian_operator.writer.write_view`.
- Target: `<vault>/90_Staging/Views/` (or a contained `--out`).
- Confirmation is mandatory: an unconfirmed render writes nothing.
- No canonical note is created, moved, modified, or deleted.
- Existing files are refused unless `force=True`. The GUI never sets `force`: it
  always sends `confirmed:true` with no `force`, so a second "Generate views"
  returns `error: already exists`. Regeneration after the first run is done via
  the CLI `--force`. `force` is set only by the CLI, never by the UI.

---

## 8. Safety and provenance

- **Write boundary:** generated views only, under the contained views root.
- **Provenance:** written views carry the generated frontmatter from `docs/73`;
  `sources`/`source_count` come straight from the operator builders.
- **Uncertainty:** validation issues and unresolved links surface in the
  overview and entity detail; the GUI invents no data.
- **Review report:** the render response prints the created/overwritten change
  set and the equivalent CLI command.
- **Constitution (Phase VI):** this phase adds a vault-mutation surface, so it is
  specified before implementation and covered by containment and no-write tests.

---

## 9. Reproducibility

Read endpoints are deterministic given a reference date. Rendered trial content
is deterministic when `generated_at` is pinned; the UI passes the current time by
default, exactly as the CLI does.

---

## 10. Validation rules

| rule | severity |
|---|---|
| Missing/invalid `X-Gui-Token` on `/api/*` | 401 (refuse) |
| Unknown section/entity/view name | error (reported) |
| Render without confirmation | `needs_confirmation` (no write) |
| Render target escapes the vault/views root | error (refuse) |
| Existing view without force | error (refuse) |
| Empty vault | not an error (renders zero items) |
