"""AssignControllerModal — TUI controller picker for a single side.

Reads the retained `gwent/menu/present/assign-p1` or `assign-p2` menu (cached
in state.menus) and renders it as a tappable list. Selecting a choice
publishes `gwent/menu/choose` and the backend's LLMPlayerManager takes over
(spawns / kills the appropriate subprocess).

Profuse logging per feedback_profuse_logging.
"""
from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Static

from gwent_tui.widgets.menu_choices import MenuChoicesWidget

log = logging.getLogger("gwent_tui.assign_controller")


class AssignControllerModal(ModalScreen):
    DEFAULT_CSS = """
    AssignControllerModal {
        align: center middle;
    }
    #acm-box {
        width: 60;
        height: 24;
        max-height: 26;
        background: $panel;
        border: thick $accent;
        padding: 1 2;
    }
    #acm-title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }
    #acm-hint {
        height: 1;
        content-align: center middle;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def __init__(self, side: str) -> None:
        """side: 'P1' or 'P2' — selects which assign-pN menu to render."""
        super().__init__()
        self.side = side.upper()
        self.menu_id = "assign-p1" if self.side == "P1" else "assign-p2"
        self._chooser: MenuChoicesWidget | None = None
        log.info("AssignControllerModal __init__ side=%s menu_id=%s",
                 self.side, self.menu_id)

    def compose(self) -> ComposeResult:
        title = f"⚙  {self.side} controller"
        with Container(id="acm-box"):
            yield Static(title, id="acm-title")
            self._chooser = MenuChoicesWidget(self.menu_id, id="acm-list")
            yield self._chooser
            yield Static("Tap / Enter to select • Esc to close", id="acm-hint")

    def on_mount(self) -> None:
        log.debug("AssignControllerModal on_mount; refreshing choices")
        if self._chooser:
            self._chooser.refresh_choices()

    def action_dismiss(self) -> None:
        log.info("AssignControllerModal dismissed (side=%s)", self.side)
        self.dismiss()

    def on_click(self, event) -> None:
        """Dismiss when tapping the background outside the modal box."""
        try:
            widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
        except Exception:
            widget = None
        node = widget
        while node is not None:
            if getattr(node, "id", None) == "acm-box":
                return
            node = getattr(node, "parent", None)
        log.info("AssignControllerModal: background tap, dismissing (side=%s)", self.side)
        self.dismiss()

    def on_list_view_selected(self, event) -> None:
        """ListView.Selected bubbles up from MenuChoicesWidget — auto-close."""
        log.info("AssignControllerModal: selection bubbled, auto-dismissing")
        self.dismiss()
