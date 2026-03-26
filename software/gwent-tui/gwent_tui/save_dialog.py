"""Save state dialog — modal overlay with filename input and OK/Cancel."""

import json
import logging
import urllib.request
import urllib.error

from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from gwent_tui.keyboard import KEY_ENTER, KEY_NEWLINE, KEY_ESCAPE, KEY_TAB, KEY_BACKSPACE, KEY_BACKSPACE2

log = logging.getLogger("gwent_tui.save_dialog")

# Focus targets
FOCUS_INPUT = 0
FOCUS_OK = 1
FOCUS_CANCEL = 2
FOCUS_COUNT = 3


class SaveDialog:
    """Modal save-state dialog state and logic."""

    def __init__(self, base_url, state=None):
        self.active = False
        self.filename = ""
        self.focus = FOCUS_INPUT
        self.status_msg = ""
        self._base_url = base_url  # e.g. "http://localhost:8080"
        self._state = state  # GameState for event log

    def open(self):
        self.active = True
        self.filename = ""
        self.focus = FOCUS_INPUT
        self.status_msg = ""
        log.info("Save dialog opened")

    def close(self):
        self.active = False
        self.status_msg = ""
        log.info("Save dialog closed")

    def handle_key(self, key):
        """Process a keystroke while dialog is active.

        Returns True if the dialog consumed the key.
        """
        if not self.active:
            return False

        log.debug("Dialog key: %r focus=%d", key, self.focus)

        if key == KEY_ESCAPE:
            self.close()
            return True

        if key == KEY_TAB:
            self.focus = (self.focus + 1) % FOCUS_COUNT
            return True

        if key in (KEY_ENTER, KEY_NEWLINE):
            if self.focus == FOCUS_CANCEL:
                self.close()
            else:
                # Enter on input or OK triggers save
                self._do_save()
            return True

        if key in (KEY_BACKSPACE, KEY_BACKSPACE2):
            if self.focus == FOCUS_INPUT:
                self.filename = self.filename[:-1]
            return True

        # Printable character — add to filename if input focused
        if self.focus == FOCUS_INPUT and len(key) == 1 and key.isprintable():
            self.filename += key
            return True

        return True  # consume all keys while dialog is open

    def _do_save(self):
        """POST to /save endpoint."""
        name = self.filename.strip()
        if not name:
            self.status_msg = "Filename cannot be empty"
            self.focus = FOCUS_INPUT
            return

        # Ensure .json extension
        if name.endswith(".json"):
            pass
        elif "." in name:
            name = name.rsplit(".", 1)[0] + ".json"
        else:
            name = name + ".json"

        save_url = self._base_url.rsplit("/", 1)[0] + f"/save?name={name}"
        try:
            req = urllib.request.Request(save_url, method="POST", data=b"")
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            filepath = result.get("filepath", name)
            log.info("State saved to %s", filepath)
            self._event(f"State saved: {name}")
            self.close()
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
                msg = body.get("error", str(e))
            except Exception:
                msg = str(e)
            log.error("Save failed: %s", msg)
            self._event(f"Save failed: {msg}")
            self.close()
        except Exception as e:
            log.error("Save failed: %s", e)
            self._event(f"Save failed: {e}")
            self.close()

    def _event(self, msg):
        """Post a message to the TUI event log."""
        if self._state:
            self._state.event_log.append(msg)

    def render(self):
        """Build a Rich renderable for the dialog overlay."""
        inner = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        inner.add_column(ratio=1)

        # Filename input
        cursor = "\u2588" if self.focus == FOCUS_INPUT else ""
        input_style = "bold white on blue" if self.focus == FOCUS_INPUT else "white on grey23"
        input_text = Text(f" {self.filename}{cursor} ", style=input_style)
        inner.add_row(Text("Filename:", style="bold"))
        inner.add_row(input_text)
        inner.add_row(Text(""))

        # Buttons
        ok_style = "bold white on green" if self.focus == FOCUS_OK else "white on grey30"
        cancel_style = "bold white on red" if self.focus == FOCUS_CANCEL else "white on grey30"

        btn_table = Table(box=None, show_header=False, padding=(0, 2))
        btn_table.add_column(justify="center")
        btn_table.add_column(justify="center")
        btn_table.add_row(
            Text(" OK ", style=ok_style),
            Text(" Cancel ", style=cancel_style),
        )
        inner.add_row(btn_table)

        # Status message
        if self.status_msg:
            inner.add_row(Text(""))
            inner.add_row(Text(self.status_msg, style="bold yellow"))

        # Hint
        inner.add_row(Text(""))
        inner.add_row(Text("Tab: navigate  Enter: select  Esc: cancel", style="dim"))

        panel = Panel(
            inner,
            title="\U0001f4be Save Game State",
            border_style="bright_cyan",
            box=box.DOUBLE,
            width=60,
            padding=(1, 2),
        )
        return Align.center(panel, vertical="middle")
