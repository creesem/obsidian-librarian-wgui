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


def test_index_html_served(tmp_path: Path) -> None:
    vault = _copy_vault(tmp_path)
    httpd, _token, url, thread = _serve(vault)
    try:
        request = urllib.request.Request(f"{url}/")
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.status == 200
            html = response.read().decode("utf-8")
        assert "obsidian-operator" in html
        assert "__GUI_BOOTSTRAP__" not in html
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
