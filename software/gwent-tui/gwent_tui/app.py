"""Gwent TUI — Textual-based live game dashboard."""

import argparse
import logging
import logging.handlers
import os

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from rich.text import Text
from rich.align import Align

from gwent_tui.game_state import GameState
from gwent_tui.mqtt_client import MqttSubscriber
from gwent_tui.snapshot import SnapshotPoller
from gwent_tui.save_dialog import SaveScreen
from gwent_tui.widgets import (
    HeaderWidget, BoardWidget, HandsWidget,
    DecksWidget, DiscardWidget, WeatherWidget, FooterWidget,
)
import gwent_tui.snapshot as snapshot_mod

log = logging.getLogger("gwent_tui.app")

DEFAULT_GWENT_URL = "http://localhost:8080/state"


def _configure_logging():
    log_file = "/tmp/logs/gwent-tui.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=50 * 1024 * 1024, backupCount=3,
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)
    if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
        fh.doRollover()


class LobbyWidget(Static):
    """Simple lobby screen for non-game stages."""

    def render(self):
        state = self.app.state
        from gwent_tui.widgets.header import _STATUS_COLOR
        mc = _STATUS_COLOR.get(state.mqtt_status, "grey50")
        hc = _STATUS_COLOR.get(state.http_status, "grey50")

        text = Text.from_markup(
            f"\n\n\u2694\ufe0f  Server Stage: [bold cyan]{state.stage}[/bold cyan]\n\n"
            f"[dim]Waiting for game to start...[/dim]\n\n"
            f"[{mc}]MQTT[/{mc}] [{hc}]HTTP[/{hc}]\n\n"
            f"[dim]? for help  Ctrl+S to save state[/dim]"
        )
        text.justify = "center"
        return Align.center(text, vertical="middle")


class GwentTUI(App):
    """Gwent Companion TUI."""

    TITLE = "Gwent TUI"

    CSS = """
    Screen {
        layout: vertical;
    }
    #header { height: 3; }
    #body { height: 1fr; }
    #footer { height: 7; }
    #left { width: 1fr; }
    #right { width: 1fr; }
    #board-area { height: 2fr; }
    #discard-area { height: 1fr; min-height: 5; }
    #weather-area { height: 6; }
    #hands-area { height: 2fr; }
    #decks-area { height: 1fr; }
    #lobby { height: 1fr; }
    """

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("question_mark", "help", "Help"),
        Binding("ctrl+s", "save", "Save State"),
        Binding("left", "widen_left", "Widen Left", show=False),
        Binding("right", "widen_right", "Widen Right", show=False),
        Binding("up", "poll_up", "Poll +5s", show=False),
        Binding("down", "poll_down", "Poll -5s", show=False),
    ]

    def __init__(self, gwent_url: str, mqtt_host: str = "localhost",
                 mqtt_port: int = 1883, no_snapshot: bool = False):
        super().__init__()
        self.state = GameState()
        self._gwent_url = gwent_url
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._no_snapshot = no_snapshot
        self._poller = None
        self._subscriber = None

    def compose(self) -> ComposeResult:
        yield HeaderWidget(id="header")
        with Horizontal(id="body"):
            with Vertical(id="left"):
                yield BoardWidget(id="board-area")
                yield DiscardWidget(id="discard-area")
                yield WeatherWidget(id="weather-area")
            with Vertical(id="right"):
                yield HandsWidget(id="hands-area")
                yield DecksWidget(id="decks-area")
        yield FooterWidget(id="footer")

    def on_mount(self):
        log.info("gwent-tui starting (url=%s)", self._gwent_url)

        # MQTT
        self._subscriber = MqttSubscriber(
            self.state, host=self._mqtt_host, port=self._mqtt_port)
        self._subscriber.connect()

        # Snapshot long-poller
        if not self._no_snapshot:
            self._poller = SnapshotPoller(state=self.state)
            self._poller.data_ready_callback = self._on_poller_data
            self._poller.start()

        # Periodic refresh as fallback (1s)
        self.set_interval(1.0, self._check_updates)

    def _on_poller_data(self):
        """Called from poller thread when new data is available."""
        self.call_from_thread(self._apply_pending_snapshots)

    def _check_updates(self):
        """Periodic check for pending snapshot data."""
        self._apply_pending_snapshots()

    def _apply_pending_snapshots(self):
        """Drain poller queue and refresh widgets."""
        if self._poller:
            count = self._poller.drain(self.state)
            if count > 0:
                self._refresh_all()

    def _refresh_all(self):
        """Refresh all widgets."""
        for widget in self.query("Static"):
            widget.refresh()

    # --- Actions ---

    def action_help(self):
        from textual.screen import ModalScreen
        from textual.widgets import Static as S
        from rich.table import Table
        from rich import box

        class HelpScreen(ModalScreen):
            CSS = """
            HelpScreen { align: center middle; }
            #help-box { width: 60; height: auto; max-height: 30; border: round $accent;
                        padding: 1 2; background: $surface; }
            """
            BINDINGS = [Binding("escape", "dismiss", "Close")]

            def compose(self):
                yield S(id="help-box")

            def on_mount(self):
                table = Table(box=box.ROUNDED, expand=False, show_header=True,
                              padding=(0, 2), title="\U0001f3ae Keyboard Shortcuts",
                              title_style="bold bright_cyan")
                table.add_column("Key", style="bold yellow", justify="right")
                table.add_column("Action", style="white")
                for key, action in [
                    ("?", "Help"), ("\u2190/\u2192", "Resize panels"),
                    ("\u2191/\u2193", "Poll timeout"), ("Ctrl+S", "Save state"),
                    ("Ctrl+C", "Quit"), ("Tab", "Navigate dialog"),
                    ("Esc", "Close dialog/help"),
                ]:
                    table.add_row(key, action)
                self.query_one("#help-box").update(table)

            def key_escape(self):
                self.dismiss()

            def on_key(self, event):
                self.dismiss()

        self.push_screen(HelpScreen())

    def action_save(self):
        self.push_screen(SaveScreen(self._gwent_url, self.state))

    def action_widen_left(self):
        left = self.query_one("#left")
        right = self.query_one("#right")
        # Cycle through ratios by adjusting CSS
        # Simple approach: toggle between presets
        pass  # TODO: implement CSS-based ratio adjustment

    def action_widen_right(self):
        pass  # TODO: implement CSS-based ratio adjustment

    def action_poll_up(self):
        snapshot_mod.POLL_TIMEOUT = min(60, snapshot_mod.POLL_TIMEOUT + 5)
        log.info("Poll timeout: %ds", snapshot_mod.POLL_TIMEOUT)
        self._refresh_all()

    def action_poll_down(self):
        snapshot_mod.POLL_TIMEOUT = max(0, snapshot_mod.POLL_TIMEOUT - 5)
        log.info("Poll timeout: %ds", snapshot_mod.POLL_TIMEOUT)
        self._refresh_all()

    def on_unmount(self):
        if self._poller:
            self._poller.stop()
        if self._subscriber:
            self._subscriber.disconnect()
        log.info("gwent-tui stopped")


def main():
    _configure_logging()

    parser = argparse.ArgumentParser(description="Gwent TUI — live game dashboard")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--no-snapshot", action="store_true")
    parser.add_argument("--gwent-url", default=DEFAULT_GWENT_URL)
    args = parser.parse_args()

    snapshot_mod.gwent_state_url = args.gwent_url

    app = GwentTUI(
        gwent_url=args.gwent_url,
        mqtt_host=args.host,
        mqtt_port=args.port,
        no_snapshot=args.no_snapshot,
    )
    app.run()


if __name__ == "__main__":
    main()
