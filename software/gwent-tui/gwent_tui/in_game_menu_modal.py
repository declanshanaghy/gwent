"""In-game hamburger menu — opened by tapping the player-bar ☰ or pressing
`m` during a game.

Structure (every item functional, unique icon per entry):
  1. 🎮 Assign Player 1 controller
  2. 🤖 Assign Player 2 controller
  3. 🚪 Quit Game                  (back to the New Game screen)
  4. 🖥 Server        → submodal: 🔄 Restart TUI / ♻ Restart Server /
                                  🔁 Restart Both / ⏹ Stop TUI /
                                  🛑 Stop Server / ⛔ Stop Both
  5. 🐞 Debugging     → submodal: 🖼 Show/Hide Header /
                                  📊 Show/Hide Events & Timers
  6. ❓ Help / Shortcuts

Profuse logging per feedback_profuse_logging.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from gwent_tui.game_state import P1, P2

log = logging.getLogger("gwent_tui.in_game_menu")

_MODEL_LABELS = None


def _model_labels() -> dict:
    """id → friendly label from data/llm-models.json (cached)."""
    global _MODEL_LABELS
    if _MODEL_LABELS is None:
        _MODEL_LABELS = {}
        try:
            import gwent.game.decks as gdecks
            path = os.path.join(os.path.dirname(gdecks.CARDS_DIR),
                                "llm-models.json")
            for m in json.load(open(path)).get("models", []):
                _MODEL_LABELS[m.get("id")] = m.get("label", m.get("id"))
        except Exception as e:
            log.debug("could not load model labels: %s", e)
    return _MODEL_LABELS


def _controller_desc(state, player) -> str:
    """'Currently: <controller>' for a player's assigned controller."""
    cid = (getattr(state, "controllers", {}) or {}).get(player, "human")
    if not cid or cid == "human":
        return "Currently: Human (RFID / touch)"
    label = (_model_labels().get(cid)
             or (getattr(state, "player_names", {}) or {}).get(player)
             or cid)
    return f"Currently: {label}"


def _systemctl(verb: str, *units: str) -> None:
    """Run a systemctl verb on units, detached so it survives this process
    dying (e.g. restarting/stopping greetd kills the TUI itself)."""
    cmd = ["sudo", "-n", "systemctl", verb, *units]
    log.info("systemctl action: %s", " ".join(cmd))
    try:
        subprocess.Popen(
            cmd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        log.error("systemctl %s %s failed: %s", verb, units, e, exc_info=True)


class _MenuRow(ListItem):
    """A single action row in the hamburger menu (optional 2nd-line desc)."""

    def __init__(self, action_id: str, label: str, icon: str = "",
                 description: str | None = None) -> None:
        text = f"{icon}  {label}" if icon else label
        if description:
            text = f"{text}\n   [dim]{description}[/dim]"
        super().__init__(Label(text))
        self.action_id = action_id


class _BaseMenuModal(ModalScreen):
    """Shared chrome for the hamburger menu and its submodals.

    Subclasses set TITLE and ACTIONS ([(id, label, icon)]) and implement
    _handle(action_id). Rows get an optional description via _row_desc().
    """

    TITLE = "Menu"
    ACTIONS: list = []

    DEFAULT_CSS = """
    _BaseMenuModal {
        align: center middle;
    }
    #imm-box {
        width: 44;
        height: auto;
        background: $panel;
        border: thick $accent;
        padding: 1 2;
    }
    #imm-title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }
    #imm-list {
        height: auto;
        max-height: 18;
        background: $surface;
        border: round $primary;
        margin-top: 1;
    }
    #imm-list ListItem {
        padding: 0 1;
        height: 2;
    }
    #imm-hint {
        height: 1;
        content-align: center middle;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select_cursor", "Select", show=False),
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._list: ListView | None = None
        log.info("%s __init__", type(self).__name__)

    def _row_desc(self, action_id: str) -> str | None:
        return None

    def compose(self) -> ComposeResult:
        with Container(id="imm-box"):
            yield Static(self.TITLE, id="imm-title")
            rows = [_MenuRow(aid, label, icon, self._row_desc(aid))
                    for aid, label, icon in self.ACTIONS]
            self._list = ListView(*rows, id="imm-list")
            yield self._list
            yield Static("↑↓ to move • Enter / tap to select • Esc to close",
                         id="imm-hint")

    def on_mount(self) -> None:
        log.debug("%s on_mount", type(self).__name__)
        if self._list and self._list.children:
            self._list.focus()
            self._list.index = 0

    def action_cursor_up(self) -> None:
        if self._list:
            self._list.action_cursor_up()

    def action_cursor_down(self) -> None:
        if self._list:
            self._list.action_cursor_down()

    def action_select_cursor(self) -> None:
        if self._list:
            self._list.action_select_cursor()

    def action_dismiss(self) -> None:
        log.info("%s dismissed (escape)", type(self).__name__)
        self.dismiss()

    def on_click(self, event: events.Click) -> None:
        """Dismiss when tapping the translucent background outside the box."""
        try:
            widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
        except Exception:
            widget = None
        node = widget
        while node is not None:
            if getattr(node, "id", None) == "imm-box":
                log.debug("%s: click inside modal box, ignoring",
                          type(self).__name__)
                return
            node = getattr(node, "parent", None)
        log.info("%s: background tap (%d,%d) — dismissing",
                 type(self).__name__, event.screen_x, event.screen_y)
        self.dismiss()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        row = event.item
        if not isinstance(row, _MenuRow):
            return
        log.info("%s SELECTED action=%s", type(self).__name__, row.action_id)
        self._handle(row.action_id)

    def _handle(self, action_id: str) -> None:  # pragma: no cover - abstract
        log.warning("%s unhandled action: %s", type(self).__name__, action_id)
        self.dismiss()


class ServerMenuModal(_BaseMenuModal):
    """Server submodal — restart/stop the TUI (greetd) and game server."""

    TITLE = "🖥  Server"
    ACTIONS = [
        ("restart-tui",    "Restart TUI",    "🔄"),
        ("restart-server", "Restart Server", "♻"),
        ("restart-both",   "Restart Both",   "🔁"),
        ("stop-tui",       "Stop TUI",       "⏹"),
        ("stop-server",    "Stop Server",    "🛑"),
        ("stop-both",      "Stop Both",      "⛔"),
    ]

    # action_id → (verb, units). greetd = the kiosk TUI session; gwent = the
    # game server. "Both" stops/restarts the server first so the TUI comes
    # back to a fresh server.
    _UNIT_MAP = {
        "restart-tui":    ("restart", ["greetd"]),
        "restart-server": ("restart", ["gwent"]),
        "restart-both":   ("restart", ["gwent", "greetd"]),
        "stop-tui":       ("stop", ["greetd"]),
        "stop-server":    ("stop", ["gwent"]),
        "stop-both":      ("stop", ["gwent", "greetd"]),
    }

    def _handle(self, action_id: str) -> None:
        verb_units = self._UNIT_MAP.get(action_id)
        if verb_units is None:
            log.warning("ServerMenuModal unknown action: %s", action_id)
            self.dismiss()
            return
        verb, units = verb_units
        self.dismiss()
        _systemctl(verb, *units)


class DebugMenuModal(_BaseMenuModal):
    """Debugging submodal — visibility toggles for dev/diagnostics."""

    TITLE = "🐞  Debugging"
    ACTIONS = [
        ("toggle-header", "Show / Hide Header", "🖼"),
        ("toggle-panels", "Show / Hide Events & Timers", "📊"),
    ]

    def _handle(self, action_id: str) -> None:
        app = self.app
        self.dismiss()
        try:
            if action_id == "toggle-header":
                app.action_toggle_header()
            elif action_id == "toggle-panels":
                app.action_toggle_panels()
            else:
                log.warning("DebugMenuModal unknown action: %s", action_id)
        except Exception as e:
            log.error("%s failed: %s", action_id, e, exc_info=True)


class InGameMenuModal(_BaseMenuModal):
    """Top-level hamburger menu shown over the in-game UI."""

    TITLE = "⚙  Menu"
    ACTIONS = [
        ("assign-p1", "Assign Player 1 controller", "🎮"),
        ("assign-p2", "Assign Player 2 controller", "🤖"),
        ("camera",    "Camera On/Off",              "🎥"),
        ("live-view", "Live View Show/Hide",        "👁"),
        ("quit",      "Quit Game",                  "🚪"),
        ("server",    "Server",                     "🖥"),
        ("debugging", "Debugging",                  "🐞"),
        ("help",      "Help / Shortcuts",           "❓"),
    ]

    def _row_desc(self, action_id: str) -> str | None:
        state = getattr(self.app, "state", None)
        if state is None:
            return None
        if action_id == "assign-p1":
            return _controller_desc(state, P1)
        if action_id == "assign-p2":
            return _controller_desc(state, P2)
        if action_id == "camera":
            if getattr(state, "camera_on", False):
                rec = getattr(state, "camera_recording", False)
                return ("Currently: ON — recording this game" if rec
                        else "Currently: ON — games are recorded")
            return "Currently: OFF — games are not recorded"
        if action_id == "live-view":
            if not getattr(state, "camera_on", False):
                return "Camera is off — turn it on first"
            return ("Currently: SHOWN — drag it anywhere; hiding never stops "
                    "recording"
                    if getattr(state, "camera_live_view", False)
                    else "Currently: HIDDEN — recording is unaffected")
        if action_id == "quit":
            return "Start a new random game"
        return None

    def _handle(self, action_id: str) -> None:
        app = self.app
        if action_id in ("assign-p1", "assign-p2"):
            side = "P1" if action_id == "assign-p1" else "P2"
            self.dismiss()
            from gwent_tui.assign_controller_modal import AssignControllerModal
            app.push_screen(AssignControllerModal(side))
            return
        if action_id == "camera":
            state = getattr(app, "state", None)
            subscriber = getattr(app, "_subscriber", None)
            if subscriber is None:
                log.error("no _subscriber on app — cannot toggle camera")
                self.dismiss()
                return
            cam_on = bool(state and getattr(state, "camera_on", False))
            action = "off" if cam_on else "on"
            log.info("InGameMenuModal: camera toggle -> %s", action)
            subscriber.publish_camera_ctrl(action)
            self.dismiss()
            return
        if action_id == "live-view":
            state = getattr(app, "state", None)
            subscriber = getattr(app, "_subscriber", None)
            if subscriber is None:
                log.error("no _subscriber on app — cannot toggle live view")
                self.dismiss()
                return
            if not (state and getattr(state, "camera_on", False)):
                log.info("InGameMenuModal: live-view tapped but camera is off")
                self.dismiss()
                return
            view = bool(getattr(state, "camera_live_view", False))
            action = "view-off" if view else "view-on"
            log.info("InGameMenuModal: live view toggle -> %s", action)
            subscriber.publish_camera_ctrl(action)
            self.dismiss()
            return
        if action_id == "quit":
            log.info("InGameMenuModal: quit game via menu/choose reset")
            subscriber = getattr(app, "_subscriber", None)
            if subscriber is None:
                log.error("no _subscriber on app — cannot publish reset")
                self.dismiss()
                return
            # Backend's MenuPublisher dispatches in-game-menu:reset →
            # start_main_menu() + republish main menu.
            subscriber.publish_choose("in-game-menu", "reset")
            self.dismiss()
            return
        if action_id == "server":
            self.dismiss()
            app.push_screen(ServerMenuModal())
            return
        if action_id == "debugging":
            self.dismiss()
            app.push_screen(DebugMenuModal())
            return
        if action_id == "help":
            self.dismiss()
            try:
                app.action_help()
            except Exception as e:
                log.error("help action failed: %s", e, exc_info=True)
            return
        log.warning("InGameMenuModal unknown action: %s", action_id)
        self.dismiss()
