"""Lightweight HTTP API for exposing game state.

Provides GET /state (same JSON as SIGUSR1 snapshots) and GET /health.
Uses stdlib http.server — no extra dependencies.
"""

import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import gwent.game.state as game_state
from gwent.utils.logging import get_logger

log = get_logger("gwent.game.http_api")

DEFAULT_PORT = 8080


class _Handler(BaseHTTPRequestHandler):
    """HTTP request handler with /state, /save, and /health endpoints."""

    def do_GET(self):
        if self.path == "/state":
            self._handle_state()
        elif self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.startswith("/save"):
            self._handle_save()
        else:
            self.send_error(404)

    def _handle_state(self):
        controller = self.server.get_controller()
        if controller is None:
            self._send_json(503, {"error": "controller not available"})
            return
        try:
            snapshot = game_state.snapshot_dict(controller)
            self._send_json(200, snapshot)
        except Exception as e:
            log.error(f"Error serializing state: {e}")
            self._send_json(503, {"error": str(e)})

    def _handle_save(self):
        """Save game state to a file in the recordings directory."""
        from urllib.parse import urlparse, parse_qs
        controller = self.server.get_controller()
        if controller is None:
            self._send_json(503, {"error": "controller not available"})
            return

        params = parse_qs(urlparse(self.path).query)
        name = params.get("name", [""])[0].strip()
        if not name:
            self._send_json(400, {"error": "missing 'name' query parameter"})
            return

        try:
            filepath = game_state.get_filepath(name)
            game_state.save(filepath, controller)
            log.info(f"State saved via HTTP to {filepath}")
            self._send_json(200, {"status": "saved", "filepath": filepath})
        except Exception as e:
            log.error(f"Error saving state: {e}")
            self._send_json(500, {"error": str(e)})

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        log.debug(fmt, *args)


class _GwentHTTPServer(HTTPServer):
    """HTTPServer that holds a reference to the controller getter."""

    def __init__(self, controller_getter, port):
        self.get_controller = controller_getter
        super().__init__(("", port), _Handler)


def start_http_server(controller_getter, port=None):
    """Start the HTTP API server in a daemon thread.

    Args:
        controller_getter: Callable that returns the Controller instance.
        port: Port to listen on (default: GWENT_HTTP_PORT env or 8080).

    Returns:
        The HTTPServer instance (call .shutdown() to stop).
    """
    if port is None:
        port = int(os.environ.get("GWENT_HTTP_PORT", str(DEFAULT_PORT)))

    server = _GwentHTTPServer(controller_getter, port)
    thread = threading.Thread(target=server.serve_forever, name="http-api", daemon=True)
    thread.start()
    log.info(f"HTTP API listening on port {port}")
    return server
