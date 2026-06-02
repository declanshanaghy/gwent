"""TUI stage: Offline — shown when the gwent server is unreachable."""

import logging
import os
import subprocess
from pathlib import Path

from rich.panel import Panel
from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Button, Static

log = logging.getLogger("gwent_tui.offline")

_REPO_ROOT = Path(os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
_SCRIPT = _REPO_ROOT / "scripts" / "dev-server.sh"


class _OfflineContent(Static):

    def render(self):
        lines = [
            "",
            "[bold red]Server Offline[/bold red]",
            "",
            "[dim]The gwent game server is not responding.[/dim]",
            "[dim]Tap Start Server or wait for auto-connect.[/dim]",
            "",
        ]
        return Panel(
            Text.from_markup("\n".join(lines)),
            title="⚠  Gwent Server Offline",
            style="red",
        )


class OfflineStage(Vertical):
    DEFAULT_CSS = """
    OfflineStage { height: 1fr; align: center middle; }
    #offline-start-btn { margin-top: 1; min-width: 28; }
    """

    def compose(self):
        yield _OfflineContent()
        yield Button("▶  Start Server", id="offline-start-btn", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "offline-start-btn":
            return
        log.info("OfflineStage: launching gwent server via %s", _SCRIPT)
        try:
            subprocess.Popen(
                ["bash", str(_SCRIPT), "gwent", "start"],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log.info("OfflineStage: server start command launched successfully")
        except Exception as e:
            log.error("OfflineStage: failed to launch server: %s", e, exc_info=True)
