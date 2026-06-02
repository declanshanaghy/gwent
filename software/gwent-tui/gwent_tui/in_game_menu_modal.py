"""In-game hamburger menu — opened by tapping the round-display header or
pressing `m` during a game. Provides Reset / Volume / Help / Cancel.

Phase 4 will extend with Step-mode toggle once the LLM-driver Phase 3 lands;
for now it stays minimal so the touchscreen has a working escape from any
in-progress game.

Profuse logging per feedback_profuse_logging.
"""
from __future__ import annotations

import logging

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

log = logging.getLogger("gwent_tui.in_game_menu")


class _MenuRow(ListItem):
    """A single action row in the hamburger menu."""

    def __init__(self, action_id: str, label: str, icon: str = "") -> None:
        text = f"{icon}  {label}" if icon else label
        super().__init__(Label(text))
        self.action_id = action_id


class InGameMenuModal(ModalScreen):
    """Hamburger menu shown over the in-game UI."""

    DEFAULT_CSS = """
    InGameMenuModal {
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

    # Action IDs are stable strings — what we send back to the caller.
    ACTIONS = [
        ("assign-p1", "Assign Player 1 controller", "1"),
        ("assign-p2", "Assign Player 2 controller", "2"),
        ("reset", "Reset to main menu", "⏏"),
        ("restart-server", "Restart server", "🔄"),
        ("volume", "Volume mixer", "🔊"),
        ("toggle-panels", "Show / hide Events & Timers", "📊"),
        ("toggle-header", "Show / hide header", "🖥"),
        ("help", "Help / shortcuts", "?"),
        ("cancel", "Cancel (close menu)", "✕"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._list: ListView | None = None
        log.info("InGameMenuModal __init__")

    def compose(self) -> ComposeResult:
        with Container(id="imm-box"):
            yield Static("⚙  In-game menu", id="imm-title")
            rows = [_MenuRow(aid, label, icon) for aid, label, icon in self.ACTIONS]
            self._list = ListView(*rows, id="imm-list")
            yield self._list
            yield Static("↑↓ to move • Enter / tap to select • Esc to close",
                         id="imm-hint")

    def on_mount(self) -> None:
        log.debug("InGameMenuModal on_mount")
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
        log.info("InGameMenuModal dismissed (escape/cancel)")
        self.dismiss()

    def on_click(self, event: events.Click) -> None:
        """Dismiss when tapping the translucent background outside the modal box."""
        try:
            widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
        except Exception:
            widget = None
        # Walk up the DOM — if the click landed inside #imm-box, let it through
        node = widget
        while node is not None:
            if getattr(node, "id", None) == "imm-box":
                log.debug("InGameMenuModal: click inside modal box, ignoring")
                return
            node = getattr(node, "parent", None)
        log.info("InGameMenuModal: background tap (%d,%d) — dismissing",
                 event.screen_x, event.screen_y)
        self.dismiss()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        row = event.item
        if not isinstance(row, _MenuRow):
            return
        log.info("InGameMenuModal SELECTED action=%s", row.action_id)
        self._handle(row.action_id)

    def _handle(self, action_id: str) -> None:
        app = self.app
        if action_id == "cancel":
            self.dismiss()
            return
        if action_id in ("assign-p1", "assign-p2"):
            side = "P1" if action_id == "assign-p1" else "P2"
            self.dismiss()
            from gwent_tui.assign_controller_modal import AssignControllerModal
            app.push_screen(AssignControllerModal(side))
            return
        if action_id == "volume":
            self.dismiss()
            from gwent_tui.volume_mixer import VolumeMixerModal
            app.push_screen(VolumeMixerModal())
            return
        if action_id == "toggle-panels":
            self.dismiss()
            try:
                app.action_toggle_panels()
            except Exception as e:
                log.error("toggle-panels action failed: %s", e, exc_info=True)
            return
        if action_id == "toggle-header":
            self.dismiss()
            try:
                app.action_toggle_header()
            except Exception as e:
                log.error("toggle-header action failed: %s", e, exc_info=True)
            return
        if action_id == "help":
            self.dismiss()
            # Reuse the app's existing help action.
            try:
                app.action_help()
            except Exception as e:
                log.error("help action failed: %s", e, exc_info=True)
            return
        if action_id == "reset":
            log.info("InGameMenuModal: requesting reset via menu/choose")
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
        if action_id == "restart-server":
            log.info("InGameMenuModal: restarting gwent.service")
            self.dismiss()
            import subprocess
            try:
                # Restart the server. The TUI loses the HTTP poll → shows the
                # Offline screen, then reconnects to a fresh server which boots
                # straight into the New Game (wizard) screen. Detached so the
                # restart proceeds even as this process keeps running.
                subprocess.Popen(
                    ["sudo", "-n", "systemctl", "restart", "gwent"],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                log.info("restart command launched")
            except Exception as e:
                log.error("restart-server failed: %s", e, exc_info=True)
            return
        log.warning("InGameMenuModal unknown action: %s", action_id)
        self.dismiss()
