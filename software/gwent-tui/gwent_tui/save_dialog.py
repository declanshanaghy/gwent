"""Save state dialog — Textual ModalScreen with filename input and OK/Cancel."""

import json
import logging
import urllib.request
import urllib.error

from textual.screen import ModalScreen
from textual.widgets import Input, Button, Static, Label
from textual.containers import Horizontal, Vertical
from textual import on

log = logging.getLogger("gwent_tui.save_dialog")


class SaveScreen(ModalScreen[str]):
    """Modal dialog for saving game state."""

    CSS = """
    SaveScreen {
        align: center middle;
    }
    #save-dialog {
        width: 60;
        height: auto;
        max-height: 20;
        border: double $accent;
        padding: 1 2;
        background: $surface;
    }
    #save-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #save-input {
        margin-bottom: 1;
    }
    #save-buttons {
        align: center middle;
        height: 3;
    }
    #save-buttons Button {
        margin: 0 2;
    }
    #save-status {
        text-align: center;
        color: $warning;
        margin-top: 1;
    }
    """

    def __init__(self, base_url: str, state=None):
        super().__init__()
        self._base_url = base_url
        self._state = state

    def compose(self):
        with Vertical(id="save-dialog"):
            yield Label("\U0001f4be Save Game State", id="save-title")
            yield Input(placeholder="Enter filename...", id="save-input")
            with Horizontal(id="save-buttons"):
                yield Button("OK", variant="success", id="save-ok")
                yield Button("Cancel", variant="error", id="save-cancel")
            yield Label("", id="save-status")

    def on_mount(self):
        self.query_one("#save-input").focus()

    @on(Button.Pressed, "#save-ok")
    def on_ok(self):
        self._do_save()

    @on(Button.Pressed, "#save-cancel")
    def on_cancel(self):
        self.dismiss("")

    @on(Input.Submitted)
    def on_submit(self):
        self._do_save()

    def key_escape(self):
        self.dismiss("")

    def on_click(self, event) -> None:
        """Dismiss when tapping the background outside the dialog."""
        try:
            widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
        except Exception:
            widget = None
        node = widget
        while node is not None:
            if getattr(node, "id", None) == "save-dialog":
                return
            node = getattr(node, "parent", None)
        log.info("SaveScreen: background tap, dismissing")
        self.dismiss("")

    def _do_save(self):
        name = self.query_one("#save-input").value.strip()
        if not name:
            self.query_one("#save-status").update("Filename cannot be empty")
            return

        if not name.endswith(".json"):
            name += ".json"

        save_url = self._base_url.rsplit("/", 1)[0] + f"/save?name={name}"
        try:
            req = urllib.request.Request(save_url, method="POST", data=b"")
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            filepath = result.get("filepath", name)
            log.info("State saved to %s", filepath)
            if self._state:
                self._state._log_event(f"State saved: {name}")
            self.dismiss(name)
        except Exception as e:
            log.error("Save failed: %s", e)
            self.query_one("#save-status").update(f"Error: {e}")
            if self._state:
                self._state._log_event(f"Save failed: {e}")
