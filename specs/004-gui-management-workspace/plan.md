# GUI Management Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local, tokenized, stdlib-only browser workspace over the operator's read-only services, with a gated path to regenerate the six generated views under `90_Staging/Views/`.

**Architecture:** A new `obsidian_operator.gui` subpackage contains a pure service layer (queries + one gated render seam), a tokenized `ThreadingHTTPServer`, and a self-contained `static/index.html`. The GUI imports only `obsidian_operator` and stdlib; the only write is view regeneration via `obsidian_operator.writer.write_view`, behind a mandatory confirmation gate. No canonical note is ever touched.

**Tech Stack:** Python ≥ 3.10 stdlib (`http.server`, `json`, `secrets`, `webbrowser`, `urllib.parse`), existing `obsidian_operator` services, `pytest`, `ruff`.

**Spec:** `specs/004-gui-management-workspace/spec.md` (companion docs: `docs/74_gui_workspace.md`, `docs/73_generated_views.md`)

## Global Constraints

- Python `>=3.10`; no new runtime dependency (stdlib only).
- `obsidian_operator` imports only `obsidian_inventory` (enforced by `tests/test_operator_import_boundary.py`).
- `obsidian_operator.gui` imports only `obsidian_operator` + stdlib; must not import `obsidian_librarian` or `obsidian_patron` (or their GUI).
- Writes confined to `<vault>/90_Staging/Views/` (or a contained `--out`); absolute paths and `..` refused.
- Overwrite refused unless `force=True`, set only through an explicit, separately confirmed overwrite (`confirmed=True`).
- No canonical/trusted note is created, moved, modified, or deleted.
- No network, LLM, embeddings, OCR, MCP, or Agents SDK runtime.
- Deterministic read output; the only non-deterministic field is `generated_at`.
- `X-Gui-Token` required on every `/api/*` route (401 otherwise).
- Static shell: no external assets (`<script src=`, `<link href=`, CDN forbidden).
- Gates before done: `pytest`, `ruff check src tests`, `obsidian-operator --help`, `obsidian-operator-gui --help`, `evals/run_evals.py`.

---

### Task 1: Service layer — read-only queries

**Files:**
- Create: `src/obsidian_operator/gui/__init__.py`
- Create: `src/obsidian_operator/gui/service.py`
- Test: `tests/test_operator_gui_service.py`

**Interfaces:**
- Consumes (existing):
  - `obsidian_operator.repository.OperatorIndex.from_vault(vault_root) -> OperatorIndex`; `.entities`, `.issues`, `.errors`, `.counts()`, `.list_type(type: str)`, `.get(type: str, name: str)`
  - `obsidian_operator.review.attention_items(index, today) -> tuple[AttentionItem, ...]`
  - `obsidian_operator.review.active_projects(index) -> tuple[EntityBase, ...]`
  - `obsidian_operator.review.active_people(index) -> tuple[EntityBase, ...]`
  - `obsidian_operator.review.build_project_review(index, project, today) -> ProjectReview`
  - `obsidian_operator.review.build_person_workload(index, person, today) -> PersonWorkload`
  - `obsidian_operator.relationships.related_to(index, entity) -> Relationships`
  - `obsidian_operator.render.attention_to_dict(item)`, `project_review_to_dict(review)`, `workload_to_dict(w)`, `issue_to_dict(issue)`, `to_dict(entity)`
  - `obsidian_operator.views.VIEWS: dict[str, ViewDefinition]` (`.name`, `.filename`, `.title`)
- Produces (this task, used by Tasks 2–5):
  - `overview(vault: str | Path, *, today: date) -> dict[str, Any]` → `{"vault": str, "counts": dict[str, int], "issue_count": int, "error_count": int, "issues": list[dict]}`
  - `today(vault: str | Path, *, today: date) -> dict[str, Any]` → `{"view": "today", "items": list[dict]}`
  - `project_board(vault: str | Path, *, today: date) -> dict[str, Any]` → `{"view": "projects", "projects": list[dict]}`
  - `team_board(vault: str | Path, *, today: date) -> dict[str, Any]` → `{"view": "team", "people": list[dict]}`
  - `entity_detail(vault: str | Path, *, entity_type: str, name: str, today: date) -> dict[str, Any]` → `{"entity": dict, "relationships": dict[str, list[str]], "issues": list[dict]}`; raises `ValueError(f"no {entity_type} found matching '{name}'")` when missing
  - `view_definitions() -> list[dict[str, Any]]` → `[{"name": str, "filename": str, "title": str}, ...]`
  - `_load_index(vault) -> OperatorIndex` helper (module-private)

- [ ] **Step 1: Write the failing test**

Create `tests/test_operator_gui_service.py`:

```python
"""Service-layer tests for the operator GUI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from obsidian_operator.gui.service import (
    entity_detail,
    overview,
    project_board,
    team_board,
    today,
    view_definitions,
)

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"
TODAY = date(2026, 10, 10)


def test_overview_reports_counts_and_issues() -> None:
    payload = overview(FIXTURE, today=TODAY)
    assert payload["vault"].endswith("operator_vault")
    assert payload["counts"]["project"] == 3
    assert payload["error_count"] >= 1
    assert any("issues" == key for key in payload)


def test_today_returns_attention_items() -> None:
    payload = today(FIXTURE, today=TODAY)
    assert payload["view"] == "today"
    assert payload["items"]
    assert {"kind", "severity", "title", "path"} <= set(payload["items"][0])


def test_project_board_lists_active_projects() -> None:
    payload = project_board(FIXTURE, today=TODAY)
    assert payload["view"] == "projects"
    titles = {project["project"]["title"] for project in payload["projects"]}
    assert "CareLogic Automation" in titles


def test_team_board_lists_active_people() -> None:
    payload = team_board(FIXTURE, today=TODAY)
    assert payload["view"] == "team"
    titles = {person["person"]["title"] for person in payload["people"]}
    assert {"Sam Okafor", "Alex Rivera", "Venkat Rao"} <= titles


def test_entity_detail_includes_relationships() -> None:
    payload = entity_detail(
        FIXTURE, entity_type="project", name="CareLogic Automation", today=TODAY
    )
    assert payload["entity"]["title"] == "CareLogic Automation"
    assert "tickets" in payload["relationships"]


def test_entity_detail_unknown_raises() -> None:
    with pytest.raises(ValueError, match="no project found"):
        entity_detail(FIXTURE, entity_type="project", name="Nope", today=TODAY)


def test_view_definitions_lists_six_views() -> None:
    definitions = view_definitions()
    assert {d["name"] for d in definitions} == {
        "today",
        "projects",
        "team",
        "tickets",
        "waiting",
        "manager-review",
    }
    assert all({"name", "filename", "title"} <= set(d) for d in definitions)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_operator_gui_service.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'obsidian_operator.gui'`

- [ ] **Step 3: Write minimal implementation**

Create `src/obsidian_operator/gui/__init__.py`:

```python
"""Local browser workspace for obsidian_operator."""
```

Create `src/obsidian_operator/gui/service.py`:

```python
"""Service layer for the operator GUI.

Pure functions over the operator index. No HTTP knowledge, no business rules:
every result is built from existing obsidian_operator services.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from obsidian_operator.render import (
    attention_to_dict,
    issue_to_dict,
    project_review_to_dict,
    to_dict,
    workload_to_dict,
)
from obsidian_operator.repository import OperatorIndex
from obsidian_operator.review import (
    active_people,
    active_projects,
    attention_items,
    build_person_workload,
    build_project_review,
)
from obsidian_operator.relationships import related_to
from obsidian_operator.views import VIEWS


def _load_index(vault: str | Path) -> OperatorIndex:
    return OperatorIndex.from_vault(vault)


def overview(vault: str | Path, *, today: date) -> dict[str, Any]:
    """Return index counts and validation issues for the vault."""
    index = _load_index(vault)
    return {
        "vault": str(index.root),
        "counts": index.counts(),
        "issue_count": len(index.issues),
        "error_count": len(index.errors),
        "issues": [issue_to_dict(issue) for issue in index.issues],
    }


def today(vault: str | Path, *, today: date) -> dict[str, Any]:
    """Return the attention queue."""
    index = _load_index(vault)
    items = attention_items(index, today)
    return {"view": "today", "items": [attention_to_dict(item) for item in items]}


def project_board(vault: str | Path, *, today: date) -> dict[str, Any]:
    """Return per-active-project rollups."""
    index = _load_index(vault)
    reviews = [build_project_review(index, project, today) for project in active_projects(index)]
    return {"view": "projects", "projects": [project_review_to_dict(r) for r in reviews]}


def team_board(vault: str | Path, *, today: date) -> dict[str, Any]:
    """Return per-active-person rollups."""
    index = _load_index(vault)
    workloads = [build_person_workload(index, person, today) for person in active_people(index)]
    return {"view": "team", "people": [workload_to_dict(w) for w in workloads]}


def entity_detail(
    vault: str | Path,
    *,
    entity_type: str,
    name: str,
    today: date,
) -> dict[str, Any]:
    """Return one entity with its relationships and issues."""
    index = _load_index(vault)
    entity = index.get(entity_type, name)
    if entity is None:
        raise ValueError(f"no {entity_type} found matching '{name}'")
    relationships = related_to(index, entity)
    related = [issue for issue in index.issues if issue.path == entity.path]
    return {
        "entity": to_dict(entity),
        "relationships": {
            "people": [e.title for e in relationships.people],
            "projects": [e.title for e in relationships.projects],
            "tickets": [e.title for e in relationships.tickets],
            "actions": [e.title for e in relationships.actions],
            "meetings": [e.title for e in relationships.meetings],
        },
        "issues": [issue_to_dict(issue) for issue in related],
    }


def view_definitions() -> list[dict[str, Any]]:
    """Return the generated-view definitions."""
    return [
        {"name": definition.name, "filename": definition.filename, "title": definition.title}
        for definition in VIEWS.values()
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_operator_gui_service.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_operator/gui/__init__.py src/obsidian_operator/gui/service.py tests/test_operator_gui_service.py
git commit -m "feat: add operator gui read-only service layer"
```

---

### Task 2: Service layer — preview and gated render

**Files:**
- Modify: `src/obsidian_operator/gui/service.py`
- Test: `tests/test_operator_gui_service.py` (append)

**Interfaces:**
- Consumes:
  - `obsidian_operator.views.build_view(name, index, *, today, generated_at) -> GeneratedView` (`.to_markdown()`)
  - `obsidian_operator.writer.write_view(views_root, vault_root, view, *, force=False) -> WriteResult` (`.path: Path`, `.created: bool`, `.overwritten: bool`)
  - `obsidian_operator.writer.ViewWriteError`
  - `obsidian_operator.views.VIEWS`
- Produces (used by Tasks 4–5):
  - `preview_view(vault, *, name: str, today: date, generated_at: str) -> dict[str, Any]` → `{"view": name, "markdown": str}`; raises `ValueError(f"unknown view: {name}")`
  - `render_view(request: dict[str, Any]) -> dict[str, Any]`
    - request keys: `vault` (str), `name` (str) or `all_views` (bool), `today` (str `YYYY-MM-DD`, optional → `date.today()`), `generated_at` (str, optional → now UTC), `confirmed` (bool), `force` (bool), `out` (str | None, vault-relative)
    - unconfirmed → `{"status": "needs_confirmation", "executed": False, "safety_tier": "staging-write", "equivalent_cli": command, "change_set": []}`
    - confirmed → `{"status": "ok", "executed": True, "safety_tier": "staging-write", "equivalent_cli": command, "change_set": [{"view", "path", "created", "overwritten"}]}`
    - error → `{"status": "error", "executed": False, "safety_tier": "staging-write", "equivalent_cli": command, "message": str, "change_set": []}`
  - `_resolve_views_root(vault: Path, out: str | None) -> Path`
  - `_view_names(name: str | None, all_views: bool) -> list[str]`
  - `_equivalent_cli(names: list[str], vault: str, out: str | None, force: bool) -> str` (uses `subprocess.list2cmdline`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_operator_gui_service.py`:

```python
import shutil

from obsidian_operator.gui.service import preview_view, render_view


def _copy_vault(tmp_path: Path) -> Path:
    target = tmp_path / "vault"
    shutil.copytree(FIXTURE, target)
    return target


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_preview_view_writes_nothing(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    before = _snapshot(vault)
    payload = preview_view(
        vault, name="today", today=TODAY, generated_at="2026-10-03T12:00:00+00:00"
    )
    assert payload["view"] == "today"
    assert payload["markdown"].startswith("---\n")
    assert "type: view" in payload["markdown"]
    assert _snapshot(vault) == before


def test_preview_unknown_view_raises(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    with pytest.raises(ValueError, match="unknown view"):
        preview_view(vault, name="nope", today=TODAY, generated_at="2026-10-03T12:00:00+00:00")


def test_render_unconfirmed_writes_nothing(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    before = _snapshot(vault)
    result = render_view(
        {"vault": str(vault), "all_views": True, "today": "2026-10-10", "confirmed": False}
    )
    assert result["status"] == "needs_confirmation"
    assert result["executed"] is False
    assert result["safety_tier"] == "staging-write"
    assert "obsidian-operator" in result["equivalent_cli"]
    assert _snapshot(vault) == before


def test_render_confirmed_writes_only_views(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    canonical_before = {
        path: content
        for path, content in _snapshot(vault).items()
        if not path.startswith("90_Staging")
    }
    result = render_view(
        {
            "vault": str(vault),
            "all_views": True,
            "today": "2026-10-10",
            "generated_at": "2026-10-03T12:00:00+00:00",
            "confirmed": True,
        }
    )
    assert result["status"] == "ok"
    assert len(result["change_set"]) == 6
    assert all(entry["created"] for entry in result["change_set"])
    assert (vault / "90_Staging" / "Views" / "Today.md").exists()
    canonical_after = {
        path: content
        for path, content in _snapshot(vault).items()
        if not path.startswith("90_Staging")
    }
    assert canonical_after == canonical_before


def test_render_second_run_without_force_errors(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    request = {
        "vault": str(vault),
        "name": "today",
        "today": "2026-10-10",
        "generated_at": "2026-10-03T12:00:00+00:00",
        "confirmed": True,
    }
    render_view(request)
    second = render_view(request)
    assert second["status"] == "error"
    assert "already exists" in second["message"]


def test_render_force_overwrites(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    render_view(
        {
            "vault": str(vault),
            "name": "today",
            "today": "2026-10-10",
            "generated_at": "2026-10-03T12:00:00+00:00",
            "confirmed": True,
        }
    )
    second = render_view(
        {
            "vault": str(vault),
            "name": "today",
            "today": "2026-10-10",
            "generated_at": "2026-10-03T12:00:00+00:00",
            "confirmed": True,
            "force": True,
        }
    )
    assert second["status"] == "ok"
    assert second["change_set"][0]["overwritten"] is True


def test_render_out_escape_is_error(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    result = render_view(
        {
            "vault": str(vault),
            "name": "today",
            "out": "../escape",
            "today": "2026-10-10",
            "confirmed": True,
        }
    )
    assert result["status"] == "error"
    assert not (tmp_path / "escape").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_operator_gui_service.py -q`
Expected: FAIL with `ImportError: cannot import name 'preview_view'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/obsidian_operator/gui/service.py`:

```python
import subprocess
from datetime import UTC, datetime

from obsidian_operator.dates import parse_iso_date
from obsidian_operator.views import GeneratedView, build_view
from obsidian_operator.writer import ViewWriteError, write_view

STAGING_WRITE = "staging-write"


def _view_names(name: str | None, all_views: bool) -> list[str]:
    if all_views:
        return list(VIEWS)
    if name is None or name not in VIEWS:
        raise ValueError(f"unknown view: {name if name is not None else '(none)'}")
    return [name]


def _resolve_today(value: str | None) -> date:
    if value is None:
        return date.today()
    parsed = parse_iso_date(value)
    if parsed is None:
        raise ValueError(f"invalid today date: {value}")
    return parsed.date()


def _resolve_generated_at(value: str | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    if parse_iso_date(value) is None:
        raise ValueError(f"invalid generated_at timestamp: {value}")
    return value


def _resolve_views_root(vault: Path, out: str | None) -> Path:
    resolved_vault = vault.expanduser().resolve(strict=False)
    if out is None:
        return resolved_vault / "90_Staging" / "Views"
    candidate = Path(out)
    if candidate.is_absolute():
        raise ValueError(f"out must be relative to the vault: {out}")
    resolved = (resolved_vault / candidate).expanduser().resolve(strict=False)
    if not resolved.is_relative_to(resolved_vault):
        raise ValueError(f"out escapes the vault: {out}")
    return resolved


def _equivalent_cli(names: list[str], vault: str, out: str | None, force: bool) -> str:
    argv = ["obsidian-operator", "view", "render"]
    if len(names) == len(VIEWS):
        argv.append("--all")
    else:
        argv.append(names[0])
    argv.extend(["--write", "--vault", vault])
    if out:
        argv.extend(["--out", out])
    if force:
        argv.append("--force")
    return subprocess.list2cmdline(argv)


def _view_to_buildable(name: str, index: OperatorIndex, today: date, generated_at: str):
    return build_view(name, index, today=today, generated_at=generated_at)


def preview_view(
    vault: str | Path,
    *,
    name: str,
    today: date,
    generated_at: str,
) -> dict[str, Any]:
    """Render one view for preview without writing anything."""
    if name not in VIEWS:
        raise ValueError(f"unknown view: {name}")
    index = _load_index(vault)
    view = build_view(name, index, today=today, generated_at=generated_at)
    return {"view": name, "markdown": view.to_markdown()}


def render_view(request: dict[str, Any]) -> dict[str, Any]:
    """Write views through the contained writer, gated by confirmation."""
    vault_value = str(request.get("vault") or ".")
    vault = Path(vault_value).expanduser()
    out = request.get("out")
    force = bool(request.get("force"))
    confirmed = bool(request.get("confirmed"))

    try:
        names = _view_names(request.get("name"), bool(request.get("all_views")))
        command = _equivalent_cli(names, str(vault), out if isinstance(out, str) else None, force)
    except ValueError as exc:
        return {
            "status": "error",
            "executed": False,
            "safety_tier": STAGING_WRITE,
            "equivalent_cli": "",
            "message": str(exc),
            "change_set": [],
        }

    if not confirmed:
        return {
            "status": "needs_confirmation",
            "executed": False,
            "safety_tier": STAGING_WRITE,
            "equivalent_cli": command,
            "change_set": [],
        }

    try:
        today = _resolve_today(request.get("today"))
        generated_at = _resolve_generated_at(request.get("generated_at"))
        views_root = _resolve_views_root(vault, out if isinstance(out, str) else None)
        index = _load_index(vault)
        views: list[GeneratedView] = [
            build_view(name, index, today=today, generated_at=generated_at) for name in names
        ]
    except (ValueError, FileNotFoundError, NotADirectoryError, OSError) as exc:
        return {
            "status": "error",
            "executed": False,
            "safety_tier": STAGING_WRITE,
            "equivalent_cli": command,
            "message": str(exc),
            "change_set": [],
        }

    change_set: list[dict[str, Any]] = []
    for view in views:
        try:
            result = write_view(views_root, vault, view, force=force)
        except (ViewWriteError, FileExistsError, OSError) as exc:
            return {
                "status": "error",
                "executed": False,
                "safety_tier": STAGING_WRITE,
                "equivalent_cli": command,
                "message": str(exc),
                "change_set": change_set,
            }
        change_set.append(
            {
                "view": view.name,
                "path": result.path.as_posix(),
                "created": result.created,
                "overwritten": result.overwritten,
            }
        )

    return {
        "status": "ok",
        "executed": True,
        "safety_tier": STAGING_WRITE,
        "equivalent_cli": command,
        "change_set": change_set,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_operator_gui_service.py -q`
Expected: PASS (14 passed)

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_operator/gui/service.py tests/test_operator_gui_service.py
git commit -m "feat: add operator gui preview and gated view render"
```

---

### Task 3: HTTP server and endpoints

**Files:**
- Create: `src/obsidian_operator/gui/server.py`
- Modify: `pyproject.toml` (add entry point under `[project.scripts]`)
- Test: `tests/test_operator_gui_server.py`

**Interfaces:**
- Consumes: Task 1 + Task 2 service functions; `obsidian_operator.__version__`.
- Produces (used by Task 4/5):
  - `create_server(host="127.0.0.1", port=0, vault=".", token=None) -> tuple[GuiHTTPServer, str, str]`
  - `run_gui(*, vault=".", host="127.0.0.1", port=0, no_browser=False) -> int`
  - `main(argv=None) -> int`
  - `GuiHTTPServer` with attributes `.token: str`, `.vault: Path`
  - Routes: `GET /`, `/api/health`, `/api/overview`, `/api/today`, `/api/projects`, `/api/team`, `/api/entity?type=&name=`, `/api/views`; `POST /api/view/preview`, `/api/view/render`

- [ ] **Step 1: Write the failing test**

Create `tests/test_operator_gui_server.py`:

```python
"""Server tests for the operator GUI."""

from __future__ import annotations

import json
import shutil
import threading
import urllib.error
import urllib.request
from pathlib import Path

from obsidian_operator.gui.server import create_server

FIXTURE = Path(__file__).parent / "fixtures" / "operator_vault"


def _copy_vault(tmp_path: Path) -> Path:
    target = tmp_path / "vault"
    shutil.copytree(FIXTURE, target)
    return target


def _request(
    url: str, token: str | None = None, payload: dict | None = None
) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    if token is not None:
        request.add_header("X-Gui-Token", token)
    if payload is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _serve(vault: Path):
    httpd, token, url = create_server("127.0.0.1", 0, vault)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, token, url, thread


def test_token_gate_and_read_routes(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    httpd, token, url, thread = _serve(vault)
    try:
        status, body = _request(f"{url}/api/health", token)
        assert status == 200 and body["status"] == "ok"

        status, _ = _request(f"{url}/api/health")
        assert status == 401
        status, _ = _request(f"{url}/api/health", "bad-token")
        assert status == 401

        today = "2026-10-10"
        status, body = _request(f"{url}/api/overview?today={today}", token)
        assert status == 200 and body["counts"]["project"] == 3

        status, body = _request(f"{url}/api/today?today={today}", token)
        assert status == 200 and body["items"]

        status, body = _request(f"{url}/api/projects?today={today}", token)
        assert status == 200 and body["projects"]

        status, body = _request(f"{url}/api/team?today={today}", token)
        assert status == 200 and body["people"]

        status, body = _request(
            f"{url}/api/entity?type=project&name=CareLogic+Automation&today={today}", token
        )
        assert status == 200 and body["entity"]["title"] == "CareLogic Automation"

        status, body = _request(f"{url}/api/views", token)
        assert status == 200 and len(body["views"]) == 6
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_preview_and_gated_render_routes(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    httpd, token, url, thread = _serve(vault)
    try:
        status, body = _request(
            f"{url}/api/view/preview",
            token,
            {"name": "today", "today": "2026-10-10", "generated_at": "2026-10-03T12:00:00+00:00"},
        )
        assert status == 200
        assert body["markdown"].startswith("---\n")
        assert not (vault / "90_Staging").exists()

        status, body = _request(
            f"{url}/api/view/render",
            token,
            {"all_views": True, "today": "2026-10-10", "confirmed": False},
        )
        assert status == 200
        assert body["status"] == "needs_confirmation"
        assert not (vault / "90_Staging").exists()

        status, body = _request(
            f"{url}/api/view/render",
            token,
            {
                "all_views": True,
                "today": "2026-10-10",
                "generated_at": "2026-10-03T12:00:00+00:00",
                "confirmed": True,
            },
        )
        assert status == 200
        assert body["status"] == "ok"
        assert len(body["change_set"]) == 6
        assert (vault / "90_Staging" / "Views" / "Today.md").exists()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_index_html_served(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    httpd, token, url, thread = _serve(vault)
    try:
        with urllib.request.urlopen(f"{url}/", timeout=5) as response:
            html = response.read().decode("utf-8")
        assert "obsidian-operator" in html
        assert "__GUI_BOOTSTRAP__" not in html
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_operator_gui_server.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'obsidian_operator.gui.server'`

- [ ] **Step 3: Write minimal implementation**

Create `src/obsidian_operator/gui/server.py`:

```python
"""Local stdlib HTTP server for the operator GUI."""

from __future__ import annotations

import argparse
import json
import secrets
import webbrowser
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from obsidian_operator import __version__
from obsidian_operator.dates import parse_iso_date
from obsidian_operator.gui.service import (
    entity_detail,
    overview,
    preview_view,
    project_board,
    render_view,
    team_board,
    today as today_view,
    view_definitions,
)

STATIC_DIR = Path(__file__).parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


class GuiHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying GUI runtime state."""

    token: str
    vault: Path


class GuiRequestHandler(BaseHTTPRequestHandler):
    """Request handler for the local operator GUI API."""

    server: GuiHTTPServer

    def log_message(self, _format: str, *_args: object) -> None:
        """Keep test and CLI output quiet."""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._send_html(self._render_index())
            return
        if not path.startswith("/api/"):
            self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        if not self._authorized():
            self._send_json({"status": "error", "message": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return
        query = parse_qs(parsed.query)
        try:
            reference = _reference_date(query)
            if path == "/api/health":
                self._send_json(
                    {
                        "status": "ok",
                        "vault": str(self.server.vault.resolve(strict=False)),
                        "version": __version__,
                        "host": self.server.server_address[0],
                        "port": self.server.server_address[1],
                    }
                )
                return
            if path == "/api/overview":
                self._send_json({"status": "ok", **overview(self.server.vault, today=reference)})
                return
            if path == "/api/today":
                self._send_json({"status": "ok", **today_view(self.server.vault, today=reference)})
                return
            if path == "/api/projects":
                self._send_json(
                    {"status": "ok", **project_board(self.server.vault, today=reference)}
                )
                return
            if path == "/api/team":
                self._send_json({"status": "ok", **team_board(self.server.vault, today=reference)})
                return
            if path == "/api/views":
                self._send_json({"status": "ok", "views": view_definitions()})
                return
            if path == "/api/entity":
                entity_type = _first(query, "type")
                name = _first(query, "name")
                detail = entity_detail(
                    self.server.vault, entity_type=entity_type, name=name, today=reference
                )
                self._send_json({"status": "ok", **detail})
                return
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            self._send_json({"status": "error", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        if not self._authorized():
            self._send_json({"status": "error", "message": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return
        try:
            payload = self._read_json()
            if path == "/api/view/preview":
                reference = _reference_date_from_payload(payload)
                generated_at = _generated_at(payload)
                result = preview_view(
                    self.server.vault,
                    name=str(payload.get("name") or ""),
                    today=reference,
                    generated_at=generated_at,
                )
                self._send_json({"status": "ok", **result})
                return
            if path == "/api/view/render":
                request = dict(payload)
                request.setdefault("vault", str(self.server.vault))
                self._send_json(render_view(request))
                return
        except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
            self._send_json({"status": "error", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)

    def _authorized(self) -> bool:
        return self.headers.get("X-Gui-Token") == self.server.token

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length == 0:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object")
        return payload

    def _render_index(self) -> str:
        html = INDEX_FILE.read_text(encoding="utf-8")
        bootstrap = {
            "token": self.server.token,
            "defaultVault": str(self.server.vault.resolve(strict=False)),
            "serverUrl": f"http://{self.server.server_address[0]}:{self.server.server_address[1]}",
        }
        return html.replace("__GUI_BOOTSTRAP__", json.dumps(bootstrap))

    def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _first(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or [""]
    return values[0]


def _reference_date(query: dict[str, list[str]]) -> date:
    value = _first(query, "today")
    if not value:
        return date.today()
    parsed = parse_iso_date(value)
    if parsed is None:
        raise ValueError(f"invalid today date: {value}")
    return parsed.date()


def _reference_date_from_payload(payload: dict[str, Any]) -> date:
    value = payload.get("today")
    if not value:
        return date.today()
    parsed = parse_iso_date(str(value))
    if parsed is None:
        raise ValueError(f"invalid today date: {value}")
    return parsed.date()


def _generated_at(payload: dict[str, Any]) -> str:
    from datetime import UTC, datetime

    value = payload.get("generated_at")
    if not value:
        return datetime.now(UTC).isoformat()
    if parse_iso_date(str(value)) is None:
        raise ValueError(f"invalid generated_at timestamp: {value}")
    return str(value)


def create_server(
    host: str = "127.0.0.1",
    port: int = 0,
    vault: str | Path = ".",
    token: str | None = None,
) -> tuple[GuiHTTPServer, str, str]:
    """Create but do not start a tokenized operator GUI server."""
    httpd = GuiHTTPServer((host, port), GuiRequestHandler)
    httpd.token = token or secrets.token_urlsafe(24)
    httpd.vault = Path(vault).expanduser().resolve(strict=False)
    bound_host, bound_port = httpd.server_address
    return httpd, httpd.token, f"http://{bound_host}:{bound_port}"


def run_gui(
    *,
    vault: str | Path = ".",
    host: str = "127.0.0.1",
    port: int = 0,
    no_browser: bool = False,
) -> int:
    """Start the operator GUI server and block until interrupted."""
    httpd, token, url = create_server(host, port, vault)
    print(f"Obsidian Operator GUI: {url}")
    print(f"Token: {token}")
    try:
        if not no_browser:
            webbrowser.open(url)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Obsidian Operator GUI.")
    finally:
        httpd.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsidian-operator-gui",
        description="Local browser workspace for obsidian_operator.",
    )
    parser.add_argument("--vault", default=".", help="Vault root path.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=0, help="Bind port. 0 for a random port.")
    parser.add_argument("--no-browser", action="store_true", help="Print URL without opening a browser.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_gui(vault=args.vault, host=args.host, port=args.port, no_browser=args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
```

Add to `pyproject.toml` under `[project.scripts]` (after the `obsidian-operator` line):

```toml
obsidian-operator-gui = "obsidian_operator.gui.server:main"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_operator_gui_server.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_operator/gui/server.py pyproject.toml tests/test_operator_gui_server.py
git commit -m "feat: add operator gui tokenized server and endpoints"
```

---

### Task 4: Static shell

**Files:**
- Create: `src/obsidian_operator/gui/static/index.html`
- Test: `tests/test_operator_gui_static.py`

**Interfaces:**
- Consumes: the endpoints from Task 3, the token from the injected `__GUI_BOOTSTRAP__` JSON (`{token, defaultVault, serverUrl}`).
- Produces: a self-contained HTML page (no external assets) with nav labels `Today`, `Projects`, `Team`, `Tickets`, `Waiting`, `Manager Review`, `Views`, plus `Preview`, `Generate views`, `Change Set`, `Equivalent CLI`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_operator_gui_static.py`:

```python
"""Static-shell tests for the operator GUI."""

from __future__ import annotations

from pathlib import Path

HTML = Path("src/obsidian_operator/gui/static/index.html").read_text(encoding="utf-8")


def test_static_shell_has_required_sections() -> None:
    for label in [
        "Today",
        "Projects",
        "Team",
        "Tickets",
        "Waiting",
        "Manager Review",
        "Views",
    ]:
        assert label in HTML
    for label in ["Preview", "Generate views", "Change Set", "Equivalent CLI"]:
        assert label in HTML
    assert "obsidian-operator" in HTML


def test_static_shell_has_no_external_assets() -> None:
    assert "<script src=" not in HTML
    assert "<link href=" not in HTML
    assert "fonts.googleapis" not in HTML
    assert "cdn" not in HTML.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_operator_gui_static.py -q`
Expected: FAIL with `FileNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `src/obsidian_operator/gui/static/index.html` (self-contained; the full file):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Obsidian Operator</title>
<style>
  :root { --bg:#12141a; --panel:#1b1e27; --line:#2b3140; --ink:#e6e9f0; --muted:#9aa3b2; --accent:#6ea8fe; --warn:#f2b34b; --err:#f27e7e; }
  * { box-sizing: border-box; }
  body { margin:0; font:14px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:var(--bg); color:var(--ink); }
  header { padding:12px 16px; border-bottom:1px solid var(--line); display:flex; gap:16px; align-items:center; }
  header h1 { font-size:15px; margin:0; }
  header .meta { color:var(--muted); font-size:12px; }
  main { display:grid; grid-template-columns: 200px 1fr; min-height: calc(100vh - 49px); }
  nav { border-right:1px solid var(--line); padding:12px; }
  nav button { display:block; width:100%; text-align:left; background:none; border:1px solid transparent; color:var(--ink); padding:7px 9px; border-radius:6px; cursor:pointer; font:inherit; }
  nav button.active, nav button:hover { background:var(--panel); border-color:var(--line); }
  section#workspace { padding:16px; }
  h2 { font-size:14px; margin:0 0 12px; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; margin-bottom:12px; }
  pre { background:#0e1015; border:1px solid var(--line); border-radius:6px; padding:10px; overflow:auto; max-height:340px; }
  .issues .error { color:var(--err); }
  .issues .warning { color:var(--warn); }
  button.action { background:var(--accent); color:#0b0d12; border:0; border-radius:6px; padding:7px 12px; cursor:pointer; font:inherit; }
  .muted { color:var(--muted); }
  #confirm { position:fixed; inset:0; background:rgba(0,0,0,.6); display:none; align-items:center; justify-content:center; }
  #confirm.open { display:flex; }
  #confirm .box { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; width:min(560px, 90vw); }
  #confirm-command { font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>Obsidian Operator</h1>
  <span class="meta" id="vault-display"></span>
</header>
<main>
  <nav id="nav"></nav>
  <section id="workspace"></section>
</main>
<div id="confirm">
  <div class="box">
    <h2 id="confirm-title">Confirm</h2>
    <p id="confirm-message" class="muted"></p>
    <pre id="confirm-command"></pre>
    <button class="action" id="cancel-confirm">Cancel</button>
    <button class="action" id="approve-confirm">Approve</button>
  </div>
</div>
<script>
const BOOTSTRAP = __GUI_BOOTSTRAP__;
const SECTIONS = ["Today","Projects","Team","Tickets","Waiting","Manager Review","Views"];
let current = "Today";
let pending = null;

const nav = document.getElementById("nav");
const workspace = document.getElementById("workspace");
document.getElementById("vault-display").textContent = BOOTSTRAP.defaultVault;

function api(path, options = {}) {
  const headers = Object.assign({"X-Gui-Token": BOOTSTRAP.token}, options.headers || {});
  if (options.body) headers["Content-Type"] = "application/json";
  return fetch(BOOTSTRAP.serverUrl + path, Object.assign({}, options, {headers}))
    .then(r => r.json());
}

function renderNav() {
  nav.innerHTML = "";
  for (const name of SECTIONS) {
    const b = document.createElement("button");
    b.textContent = name;
    if (name === current) b.className = "active";
    b.onclick = () => { current = name; renderNav(); renderSection(); };
    nav.appendChild(b);
  }
}

function block(title, obj) {
  const panel = document.createElement("div");
  panel.className = "panel";
  const h = document.createElement("h2");
  h.textContent = title;
  const pre = document.createElement("pre");
  pre.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  panel.append(h, pre);
  return panel;
}

async function renderSection() {
  workspace.innerHTML = "";
  if (current === "Views") return renderViews();
  if (current === "Tickets" || current === "Waiting" || current === "Manager Review") {
    const data = await api("/api/today");
    const items = (data.items || []).filter(it => {
      if (current === "Tickets") return it.entity_type === "ticket";
      if (current === "Waiting") return it.kind === "waiting";
      return it.severity === "high";
    });
    workspace.appendChild(block(current, items));
    return;
  }
  const path = {"Today": "/api/today", "Projects": "/api/projects", "Team": "/api/team"}[current];
  const data = await api(path);
  workspace.appendChild(block(current, data));
}

async function renderViews() {
  const defs = await api("/api/views");
  const list = block("Views", defs.views);
  workspace.appendChild(list);
  for (const view of defs.views) {
    const panel = document.createElement("div");
    panel.className = "panel";
    const h = document.createElement("h2");
    h.textContent = view.title + " (" + view.filename + ")";
    const previewBtn = document.createElement("button");
    previewBtn.className = "action";
    previewBtn.textContent = "Preview";
    const out = document.createElement("pre");
    previewBtn.onclick = async () => {
      const res = await api("/api/view/preview", {method:"POST", body: JSON.stringify({name: view.name})});
      out.textContent = res.markdown || JSON.stringify(res, null, 2);
    };
    panel.append(h, previewBtn, out);
    workspace.appendChild(panel);
  }
  const gen = document.createElement("button");
  gen.className = "action";
  gen.textContent = "Generate views";
  gen.id = "generate";
  gen.onclick = () => confirmRender();
  const report = document.createElement("div");
  report.className = "panel";
  report.id = "change-set";
  report.innerHTML = "<h2>Change Set</h2><pre class=\"muted\">(none)</pre>";
  workspace.append(gen, report);
}

function confirmRender() {
  api("/api/view/render", {method:"POST", body: JSON.stringify({all_views:true, confirmed:false})})
    .then(res => {
      pending = res.equivalent_cli;
      document.getElementById("confirm-message").textContent =
        "This writes generated views under 90_Staging/Views/. No canonical note is touched.";
      document.getElementById("confirm-command").textContent = pending;
      document.getElementById("confirm").classList.add("open");
    });
}

document.getElementById("cancel-confirm").onclick = () => {
  document.getElementById("confirm").classList.remove("open");
  pending = null;
};
document.getElementById("approve-confirm").onclick = async () => {
  document.getElementById("confirm").classList.remove("open");
  const res = await api("/api/view/render", {method:"POST", body: JSON.stringify({all_views:true, confirmed:true})});
  const target = document.getElementById("change-set");
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify({change_set: res.change_set, equivalent_cli: res.equivalent_cli}, null, 2);
  target.innerHTML = "<h2>Change Set</h2>";
  target.appendChild(pre);
};

renderNav();
renderSection();
</script>
</body>
</html>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_operator_gui_static.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_operator/gui/static/index.html tests/test_operator_gui_static.py
git commit -m "feat: add operator gui static shell"
```

---

### Task 5: Import boundary, no-write regression, docs

**Files:**
- Create: `tests/test_operator_gui_import_boundary.py`
- Modify: `tests/test_operator_no_writes.py`
- Modify: `docs/72_operator_roadmap.md`
- Modify: `docs/74_gui_workspace.md`

**Interfaces:**
- Consumes: `obsidian_operator.gui.server.create_server` (Task 3), `obsidian_operator.gui.service` (Tasks 1–2).
- Produces: boundary evidence, no-write evidence, updated docs.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_operator_gui_import_boundary.py`:

```python
"""Guard the GUI boundary: gui imports only operator + stdlib."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import obsidian_operator.gui

_FORBIDDEN = ("obsidian_librarian", "obsidian_patron")


def test_gui_sources_do_not_reference_binary_packages() -> None:
    package_dir = Path(obsidian_operator.gui.__file__).parent
    for source in package_dir.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN:
            assert forbidden not in text, f"{source.name} references {forbidden}"


def test_importing_gui_does_not_load_binaries() -> None:
    code = (
        "import sys, obsidian_operator.gui.server; "
        "assert 'obsidian_librarian' not in sys.modules, 'librarian imported'; "
        "assert 'obsidian_patron' not in sys.modules, 'patron imported'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
```

Append to `tests/test_operator_no_writes.py`:

```python
def test_gui_read_session_writes_nothing(tmp_path: Path) -> None:
    import json
    import threading
    import urllib.request

    from obsidian_operator.gui.server import create_server

    vault = tmp_path / "vault"
    shutil.copytree(FIXTURE, vault)
    before = _snapshot(vault)

    httpd, token, url = create_server("127.0.0.1", 0, vault)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        for route in ["/api/overview", "/api/today", "/api/projects", "/api/team", "/api/views"]:
            req = urllib.request.Request(f"{url}{route}")
            req.add_header("X-Gui-Token", token)
            with urllib.request.urlopen(req, timeout=5) as response:
                json.loads(response.read().decode("utf-8"))
        req = urllib.request.Request(
            f"{url}/api/view/preview",
            data=json.dumps({"name": "today"}).encode("utf-8"),
        )
        req.add_header("X-Gui-Token", token)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=5) as response:
            json.loads(response.read().decode("utf-8"))
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert _snapshot(vault) == before
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_operator_gui_import_boundary.py tests/test_operator_no_writes.py -q`
Expected: FAIL — `test_operator_gui_import_boundary.py` may pass (gui already clean), but the new no-write test should pass only once the server exists. If both pass immediately, continue; the tests are still required as regression guards.

- [ ] **Step 3: Confirm the boundary holds**

The GUI already imports only `obsidian_operator` + stdlib (Tasks 1–3). No production change needed here beyond confirming the tests pass. If `test_gui_sources_do_not_reference_binary_packages` fails on the docstring/word `patron`, remove the offending word from the gui source.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_operator_gui_import_boundary.py tests/test_operator_no_writes.py -q`
Expected: PASS

- [ ] **Step 5: Update docs**

In `docs/72_operator_roadmap.md`, change the Phase 4 heading to `## Phase 4 — GUI management workspace *(implemented)*` and append a `**Delivered:**` line describing `obsidian_operator/gui/{service,server}.py`, `static/index.html`, the tokenized endpoints, and the gated view render.

In `docs/74_gui_workspace.md`, change `Status: Proposed (Phase 4).` to `Status: Implemented (Phase 4).`

- [ ] **Step 6: Commit**

```bash
git add tests/test_operator_gui_import_boundary.py tests/test_operator_no_writes.py docs/72_operator_roadmap.md docs/74_gui_workspace.md
git commit -m "test: guard operator gui boundary and no-write behavior; docs"
```

---

### Task 6: Full gates

**Files:** none (verification only).

- [ ] **Step 1: Run the full suite**

Run: `pytest -q`
Expected: PASS (Phases 1–3 tests plus the new GUI tests; 2 skipped).

- [ ] **Step 2: Lint**

Run: `ruff check src tests`
Expected: `All checks passed!`

- [ ] **Step 3: CLI help**

Run: `python -m obsidian_operator.cli view --help` and `python -m obsidian_operator.gui.server --help`
Expected: exit 0 both.

- [ ] **Step 4: Evals**

Run: `python evals/run_evals.py`
Expected: all PASS, exit 0.

- [ ] **Step 5: Report**

Report changed files, exact commands, test status, assumptions, and risks. Confirm no canonical note was written by any GUI read path.

---

## Self-Review

**Spec coverage:**
- FR-001 token gate → Task 3 (401 test). 
- FR-002 nav sections → Task 4 (static labels) + server read routes.
- FR-003 read endpoints write nothing → Task 1/5.
- FR-004 preview writes nothing → Task 2.
- FR-005 unconfirmed render writes nothing → Task 2/3.
- FR-006 containment → Task 2 (`_resolve_views_root`) + `write_view`.
- FR-007 overwrite/force → Task 2.
- FR-008 equivalent CLI → Task 2.
- FR-009 change set → Task 2/4.
- FR-010 no canonical writes → Task 5 (`test_gui_read_session_writes_nothing`, canonical-unchanged asserts).
- FR-011 stdlib only → Global Constraints.
- FR-012 import boundary → Task 5.
- FR-013 self-contained shell → Task 4.
- FR-014 reuse services → Tasks 1–2.
- FR-015 entry point/CLI → Task 3 + pyproject.
- SC-001..SC-007 → Tasks 5/6.

**Placeholder scan:** none — every step has concrete code/commands.

**Type consistency:** `create_server` returns a 3-tuple in both Task 3 implementation and Task 5 test; `render_view` request/response keys (`all_views`, `confirmed`, `change_set`, `equivalent_cli`, `status`, `safety_tier`) match Task 2 implementation and Task 3/4 consumers; `preview_view` returns `{"view", "markdown"}` consistently.
