"""TUI stage: Offline — shown when the gwent server is unreachable."""

import logging
import subprocess

from rich.panel import Panel
from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Button, Static

log = logging.getLogger("gwent_tui.offline")


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
        # Restart the systemd service rather than dev-server.sh: a nohup'd
        # dev server runs without GWENT_DISABLE_SERVER_TTS (so it plays its
        # own music over the TUI's stream) and its pidfile blocks the real
        # service from ever starting again.
        log.info("OfflineStage: restarting gwent.service")
        try:
            subprocess.Popen(
                ["sudo", "-n", "systemctl", "restart", "gwent"],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log.info("OfflineStage: server start command launched successfully")
        except Exception as e:
            log.error("OfflineStage: failed to launch server: %s", e, exc_info=True)
