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
from obsidian_operator.gui.service import (
    _resolve_generated_at,
    _resolve_today,
    entity_detail,
    manager_review,
    overview,
    preview_view,
    project_board,
    render_view,
    team_board,
    tickets,
    view_definitions,
    waiting,
)
from obsidian_operator.gui.service import (
    today as today_view,
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
            if path == "/api/tickets":
                self._send_json({"status": "ok", **tickets(self.server.vault, today=reference)})
                return
            if path == "/api/waiting":
                self._send_json({"status": "ok", **waiting(self.server.vault, today=reference)})
                return
            if path == "/api/manager-review":
                self._send_json(
                    {"status": "ok", **manager_review(self.server.vault, today=reference)}
                )
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
        except (ValueError, OSError) as exc:
            self._send_json({"status": "error", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        if not self._authorized():
            self._drain_body()
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
                self._send_json(render_view(self.server.vault, dict(payload)))
                return
        except (ValueError, OSError) as exc:
            self._send_json({"status": "error", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)

    def _authorized(self) -> bool:
        provided = self.headers.get("X-Gui-Token") or ""
        return secrets.compare_digest(provided, self.server.token)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length == 0:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object")
        return payload

    def _drain_body(self) -> None:
        """Read and discard any request body before an early response.

        Sending a response without consuming a declared body makes the client
        abort the connection on some platforms (notably Windows), which the
        server would otherwise observe as a spurious socket error.
        """
        length = int(self.headers.get("Content-Length") or "0")
        if length > 0:
            self.rfile.read(length)

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
    return _resolve_today(_first(query, "today") or None)


def _reference_date_from_payload(payload: dict[str, Any]) -> date:
    value = payload.get("today")
    return _resolve_today(str(value) if value else None)


def _generated_at(payload: dict[str, Any]) -> str:
    value = payload.get("generated_at")
    return _resolve_generated_at(str(value) if value else None)


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
    parser.add_argument(
        "--no-browser", action="store_true", help="Print URL without opening a browser."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_gui(vault=args.vault, host=args.host, port=args.port, no_browser=args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
