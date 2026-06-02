"""Lightweight HTTP API for exposing game state.

Provides:
- GET /state — immediate snapshot
- GET /state/poll?timeout=30 — long-poll, blocks until state changes or timeout
- GET /health — health check
- POST /save?name=filename — save state to recordings

Uses stdlib http.server — no extra dependencies.
"""

import hashlib
import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

import gwent.game.state as game_state
from gwent.utils.logging import get_logger

log = get_logger("gwent.game.http_api")

DEFAULT_PORT = 8080
MAX_POLL_TIMEOUT = 300
DEFAULT_POLL_TIMEOUT = 300


class _Handler(BaseHTTPRequestHandler):
    """HTTP request handler with /state, /state/poll, /save, and /health."""

    def do_GET(self):
        path = urlparse(self.path).path
        log.debug("do_GET %s", path)
        if path == "/state":
            self._handle_state_poll()
        elif path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self.send_error(404)

    def do_PUT(self):
        path = urlparse(self.path).path
        log.debug("do_PUT %s", path)
        if path == "/players":
            self._handle_set_players()
        elif path == "/client-tts":
            self._handle_set_client_tts()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.startswith("/save"):
            self._handle_save()
        else:
            self.send_error(404)

    def _handle_state_poll(self):
        """Long-poll: block until state changes or timeout.

        Uses ETag (If-None-Match) to detect changes. First call returns
        immediately with full state + ETag. Subsequent calls with matching
        ETag block until state changes or timeout.
        """
        controller = self.server.get_controller()
        if controller is None:
            self._send_json(503, {"error": "controller not available"})
            return

        # Parse timeout from query string
        params = parse_qs(urlparse(self.path).query)
        try:
            timeout = min(float(params.get("timeout", [DEFAULT_POLL_TIMEOUT])[0]),
                          MAX_POLL_TIMEOUT)
        except (ValueError, IndexError):
            timeout = DEFAULT_POLL_TIMEOUT

        client_etag = self.headers.get("If-None-Match", "")
        log.debug("GET /state timeout=%.0f etag=%s", timeout, client_etag or "(none)")

        try:
            # Get current state and its ETag
            snapshot = game_state.snapshot_dict(controller, player_names=self.server.player_names, player_pronouns=self.server.player_pronouns, client_tts=self.server.client_tts)
            etag = self._compute_etag(snapshot)

            if client_etag and client_etag == etag:
                # Client already has this state — wait for a change
                log.debug("ETag matches, waiting up to %.0fs for change", timeout)
                cond = self.server.state_condition
                if cond:
                    with cond:
                        cond.wait(timeout=timeout)

                # Re-snapshot after wake
                snapshot = game_state.snapshot_dict(controller, player_names=self.server.player_names, player_pronouns=self.server.player_pronouns, client_tts=self.server.client_tts)
                new_etag = self._compute_etag(snapshot)

                if new_etag == client_etag:
                    log.debug("Long-poll timed out, no change (304)")
                    self.send_response(304)
                    self.send_header("ETag", new_etag)
                    self.end_headers()
                    return

                log.debug("Long-poll woke — state changed, new etag=%s", new_etag)
                etag = new_etag
            else:
                log.debug("First poll or ETag mismatch, returning immediately")

            # Return current state with ETag
            log.debug("Returning state (stage=%s, etag=%s)", snapshot.get("active_stage"), etag)
            self._send_json_with_etag(200, snapshot, etag)

        except Exception as e:
            log.error(f"Error in long-poll: {e}")
            self._send_json(503, {"error": str(e)})

    def _handle_set_players(self):
        """Set player display names and optional pronouns."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            for key in ("PLAYER.ONE", "PLAYER.TWO"):
                if key in data:
                    val = data[key]
                    if isinstance(val, dict):
                        # Extended format: {"name": "...", "pronoun": "he|she"}
                        self.server.player_names[key] = str(val.get("name", key))
                        if "pronoun" in val:
                            self.server.player_pronouns[key] = str(val["pronoun"])
                    else:
                        self.server.player_names[key] = str(val)
            log.info("Player names updated: %s, pronouns: %s",
                     self.server.player_names, self.server.player_pronouns)
            # Wake long-poll clients so they pick up the change
            cond = self.server.state_condition
            if cond:
                with cond:
                    cond.notify_all()
            self._send_json(200, {
                "status": "ok",
                "player_names": self.server.player_names,
                "player_pronouns": self.server.player_pronouns,
            })
        except Exception as e:
            log.error("Error setting player names: %s", e)
            self._send_json(400, {"error": str(e)})

    def _handle_set_client_tts(self):
        """Register a client's TTS provider."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            client_id = data.get("client_id", "gwent-tui")
            provider = data.get("provider", "none")
            self.server.client_tts[client_id] = provider
            log.info("Client TTS registered: %s=%s", client_id, provider)
            # Tell server SFX to skip local music AND TTS — TUI handles both
            import gwent.game
            already_handled = gwent.game.PubSubComponent._client_handles_music
            gwent.game.PubSubComponent._client_handles_music = True
            gwent.game.PubSubComponent._client_handles_tts = True
            # If the server was already playing music when the client
            # registered, the existing pygame stream keeps running at 100%
            # forever (subsequent plays are skipped). Stop it now so the
            # TUI's stream is the only source.
            if not already_handled:
                try:
                    from gwent_shared.audio import get_mixer
                    mixer = get_mixer()
                    log.info("TUI took over music — disabling local server playback")
                    # disable_music() both stops the current pygame stream
                    # AND blocks any in-flight play_music() (which may be
                    # mid-fadeout sleep) from resuming with a fresh track.
                    mixer.disable_music()
                except Exception as e:
                    log.warning("failed to disable local music on client takeover: %s", e)
            cond = self.server.state_condition
            if cond:
                with cond:
                    cond.notify_all()
            self._send_json(200, {"status": "ok", "client_tts": self.server.client_tts})
        except Exception as e:
            log.error("Error setting client TTS: %s", e)
            self._send_json(400, {"error": str(e)})

    def _handle_save(self):
        """Save game state to a file in the recordings directory."""
        log.debug("POST /save")
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

    def _compute_etag(self, snapshot):
        """Compute ETag from snapshot content hash, excluding volatile fields."""
        stable = dict(snapshot)
        stable.pop("saved_at", None)
        raw = json.dumps(stable, sort_keys=True).encode("utf-8")
        return hashlib.md5(raw).hexdigest()

    def _send_json_with_etag(self, code, obj, etag=None):
        """Send JSON response with ETag header."""
        body = json.dumps(obj).encode("utf-8")
        if etag is None:
            etag = hashlib.md5(body).hexdigest()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", etag)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        log.debug(fmt, *args)


class _GwentHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTPServer — each request gets its own thread so long-polls don't block others."""
    daemon_threads = True

    def __init__(self, controller_getter, pubsub, port):
        self.get_controller = controller_getter
        self.state_condition = getattr(pubsub, 'state_condition', None) if pubsub else None
        self.player_names = {"PLAYER.ONE": "Player 1", "PLAYER.TWO": "Player 2"}
        self.player_pronouns = {"PLAYER.ONE": "he", "PLAYER.TWO": "he"}
        self.client_tts = {}  # {client_id: provider_name}
        super().__init__(("", port), _Handler)


def start_http_server(controller_getter, pubsub=None, port=None):
    """Start the HTTP API server in a daemon thread.

    Args:
        controller_getter: Callable that returns the Controller instance.
        pubsub: MQTTClient instance (for state_condition access).
        port: Port to listen on (default: GWENT_HTTP_PORT env or 8080).

    Returns:
        The HTTPServer instance (call .shutdown() to stop).
    """
    if port is None:
        port = int(os.environ.get("GWENT_HTTP_PORT", str(DEFAULT_PORT)))

    server = _GwentHTTPServer(controller_getter, pubsub, port)
    thread = threading.Thread(target=server.serve_forever, name="http-api", daemon=True)
    thread.start()
    log.info(f"HTTP API listening on port {port}")
    return server
