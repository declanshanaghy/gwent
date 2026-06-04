"""MFDChoiceModal — touchscreen popup for interactive MFD picks.

When the server presents numeric-id choices on `gwent/mfd/present` (agile
"Choose a Row", leader weather-card pick, …) the rotary/OLED used to be the
only way to answer — a touchscreen play would simply get stuck. The app pops
this modal from `state.mfd_pick`; selecting a row publishes the choice on
`gwent/mfd/choose` exactly like the rotary does.

Profuse logging per feedback_profuse_logging.
"""
from __future__ import annotations

import json
import logging

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

log = logging.getLogger("gwent_tui.mfd_choice")

# Icons for well-known choice texts (rows etc.); fallback is a button dot.
_CHOICE_ICONS = {
    "close": "⚔",
    "ranged": "🏹",
    "siege": "🏰",
}


def _choice_icon(text: str) -> str:
    return _CHOICE_ICONS.get(text.strip().lower(), "🔘")


class _ChoiceRow(ListItem):
    def __init__(self, choice: dict) -> None:
        text = choice.get("text", "?")
        super().__init__(Label(f"{_choice_icon(text)}  {text}"))
        self.choice = choice


class MFDChoiceModal(ModalScreen):
    """Popup listing the server's pending MFD choices."""

    DEFAULT_CSS = """
    MFDChoiceModal {
        align: center middle;
    }
    #mfd-box {
        width: 50;
        height: auto;
        max-height: 26;
        background: $panel;
        border: thick $accent;
        padding: 1 2;
    }
    #mfd-title {
        height: auto;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }
    #mfd-list {
        height: auto;
        max-height: 18;
        background: $surface;
        border: round $primary;
        margin-top: 1;
    }
    #mfd-list ListItem {
        padding: 0 1;
        height: 2;
    }
    #mfd-hint {
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
    ]

    def __init__(self, pick: dict) -> None:
        super().__init__()
        self.pick = pick
        self._list: ListView | None = None
        log.info("MFDChoiceModal __init__ seq=%s choices=%s",
                 pick.get("seq"),
                 [c.get("text") for c in pick.get("choices", [])])

    def compose(self) -> ComposeResult:
        title = self.pick.get("prompt") or "Make a choice"
        with Container(id="mfd-box"):
            yield Static(title, id="mfd-title")
            rows = [_ChoiceRow(c) for c in self.pick.get("choices", [])]
            self._list = ListView(*rows, id="mfd-list")
            yield self._list
            yield Static("Tap / Enter to select • Esc to close",
                         id="mfd-hint")

    def on_mount(self) -> None:
        log.debug("MFDChoiceModal on_mount")
        if self._list and self._list.children:
            self._list.focus()
            self._list.index = 0

    def refresh_title(self) -> None:
        """Update the title if the contextual prompt arrived after popup."""
        try:
            prompt = self.pick.get("prompt")
            if prompt:
                self.query_one("#mfd-title", Static).update(prompt)
        except Exception as e:
            log.debug("refresh_title failed: %s", e)

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
        log.info("MFDChoiceModal dismissed (escape) — choice left to rotary")
        self.dismiss()

    def on_click(self, event: events.Click) -> None:
        """Dismiss when tapping the background outside the modal box."""
        try:
            widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
        except Exception:
            widget = None
        node = widget
        while node is not None:
            if getattr(node, "id", None) == "mfd-box":
                return
            node = getattr(node, "parent", None)
        log.info("MFDChoiceModal: background tap — dismissing (no choice)")
        self.dismiss()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        row = event.item
        if not isinstance(row, _ChoiceRow):
            return
        choice = row.choice
        log.info("MFDChoiceModal SELECTED id=%s text=%s",
                 choice.get("id"), choice.get("text"))
        app = self.app
        subscriber = getattr(app, "_subscriber", None)
        if subscriber is None:
            log.error("no _subscriber — cannot publish mfd choice")
            self.dismiss()
            return
        subscriber.publish_mfd_choose(choice.get("id"), choice.get("text"))
        # Consume the pick so the app doesn't immediately re-pop it.
        try:
            app.state.mfd_pick = None
        except Exception as e:
            log.debug("clearing mfd_pick failed: %s", e)
        self.dismiss()
