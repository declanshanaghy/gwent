"""Generic menu-choices widget — renders the cached MQTT menu payload as a
tappable / keyboard-navigable list. Reused by State A (main menu), Phase 3
controller picker, and Phase 4 in-game menu.

The widget reads `app.state.menus[menu_id]` for its payload. When the cache
updates (via `MqttSubscriber.on_menu`), call `refresh_choices()` to repaint.
Selections are published on `gwent/menu/choose` via `app._subscriber.publish_choose()`.
"""
from __future__ import annotations

import logging

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Static, ListView, ListItem, Label

log = logging.getLogger("gwent_tui.menu_choices")


class _ChoiceRow(ListItem):
    """Single tappable menu row carrying its choice payload."""

    def __init__(self, choice: dict) -> None:
        text = choice.get("text", "?")
        icon = choice.get("icon", "")
        desc = choice.get("description", "")
        disabled = choice.get("disabled", False)
        label = f"{icon}  {text}" if icon else text
        if desc:
            label = f"{label}\n  [dim]{desc}[/dim]"
        super().__init__(Label(label))
        self.choice = choice
        if disabled:
            self.disabled = True


class MenuChoicesWidget(Container):
    """Renders cached `state.menus[menu_id]` as a tappable list."""

    DEFAULT_CSS = """
    MenuChoicesWidget {
        height: auto;
        padding: 0 1;
    }
    MenuChoicesWidget > Static#mc-prompt {
        height: auto;
        padding: 0 1;
        text-style: bold;
        color: $accent;
    }
    MenuChoicesWidget > ListView {
        height: auto;
        max-height: 18;
        border: round $primary;
        background: $surface;
    }
    MenuChoicesWidget ListItem {
        padding: 0 1;
    }
    MenuChoicesWidget > Static#mc-empty {
        height: auto;
        padding: 1 2;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select_cursor", "Select", show=False),
    ]

    def __init__(self, menu_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.menu_id = menu_id
        self._list: ListView | None = None
        self._prompt: Static | None = None
        self._empty: Static | None = None
        # Dedup repeated refresh_choices() calls — only rebuild the ListView
        # when the cached payload's content_id changes. The 1Hz periodic
        # refresh in app.py calls refresh_choices() every tick; without this
        # we'd churn the ListView every second and the UI would flicker.
        self._last_content_id: str | None = None
        log.debug("MenuChoicesWidget[%s] __init__", menu_id)

    def compose(self) -> ComposeResult:
        self._prompt = Static("", id="mc-prompt")
        yield self._prompt
        self._list = ListView()
        yield self._list
        self._empty = Static(f"(waiting for menu '{self.menu_id}'…)", id="mc-empty")
        yield self._empty

    def on_mount(self) -> None:
        log.debug("MenuChoicesWidget[%s] on_mount", self.menu_id)
        self.refresh_choices()

    def refresh_choices(self) -> None:
        """Re-read state.menus[menu_id] and rebuild the list if it changed."""
        state = self.app.state
        payload = state.menus.get(self.menu_id)
        if not payload or not payload.get("choices"):
            if self._last_content_id is not None:
                log.info(
                    "MenuChoicesWidget[%s]: cleared (was %s)",
                    self.menu_id, self._last_content_id,
                )
            self._last_content_id = None
            self._show_empty()
            return
        # Short-circuit when the cached payload hasn't changed. Each menu
        # message carries a content_id (md5 of its body); rebuilds happen
        # only on a new id.
        new_cid = payload.get("content_id")
        if new_cid is not None and new_cid == self._last_content_id:
            return
        self._last_content_id = new_cid
        prompt = payload.get("prompt", "")
        choices = payload.get("choices", [])
        log.info(
            "MenuChoicesWidget[%s]: rendering %d choices (prompt=%r, cid=%s)",
            self.menu_id, len(choices), prompt, new_cid,
        )
        self._prompt.update(prompt)
        self._prompt.display = bool(prompt)
        self._list.clear()
        for c in choices:
            self._list.append(_ChoiceRow(c))
        self._empty.display = False
        self._list.display = True
        # Focus the list so keyboard navigation works.
        try:
            self._list.focus()
        except Exception:
            pass
        if self._list.children:
            self._list.index = 0

    def _show_empty(self) -> None:
        if self._list is not None:
            self._list.clear()
            self._list.display = False
        if self._empty is not None:
            self._empty.display = True
        if self._prompt is not None:
            self._prompt.update("")
            self._prompt.display = False

    @on(ListView.Selected)
    def _on_selected(self, event: ListView.Selected) -> None:
        row = event.item
        if not isinstance(row, _ChoiceRow):
            return
        choice = row.choice
        log.info(
            "MenuChoicesWidget[%s] SELECTED id=%r text=%r",
            self.menu_id, choice.get("id"), choice.get("text"),
        )
        subscriber = getattr(self.app, "_subscriber", None)
        if subscriber is None:
            log.error("no _subscriber on app — cannot publish choose")
            return
        subscriber.publish_choose(self.menu_id, choice.get("id"))

    def action_cursor_up(self) -> None:
        if self._list:
            self._list.action_cursor_up()

    def action_cursor_down(self) -> None:
        if self._list:
            self._list.action_cursor_down()

    def action_select_cursor(self) -> None:
        if self._list:
            self._list.action_select_cursor()
