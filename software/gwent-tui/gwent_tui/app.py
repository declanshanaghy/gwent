"""Gwent TUI — Textual-based live game dashboard."""

import argparse
import logging
import logging.handlers
import os

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static

from gwent_tui.game_state import GameState
from gwent_tui.mqtt_client import MqttSubscriber
from gwent_tui.snapshot import SnapshotPoller
from gwent_tui.save_dialog import SaveScreen
from gwent_tui.widgets.header import HeaderWidget
from gwent_tui.widgets.footer import FooterWidget
from gwent_tui.widgets.timers import TimersWidget
from gwent_tui.stages import STAGE_WIDGETS, UnknownStage, OfflineStage
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


class GwentTUI(App):
    """Gwent Companion TUI."""

    TITLE = "Gwent TUI"

    CSS = """
    Screen { layout: vertical; }
    * { scrollbar-size: 0 0; }
    #header { height: 3; }
    #stage-container { height: 1fr; overflow-y: auto; }
    #bottom-bar { height: 7; }
    #footer { width: 3fr; height: 100%; }
    #timers { width: 1fr; height: 100%; }
    """

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("question_mark", "help", "Help"),
        Binding("ctrl+s", "save", "Save State"),
        Binding("p", "cycle_poll", "Poll timeout", show=False),
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
        self._current_stage_name = None

    def compose(self) -> ComposeResult:
        yield HeaderWidget(id="header")
        # Stage container — will be populated dynamically
        yield UnknownStage(id="stage-container")
        with Horizontal(id="bottom-bar"):
            yield FooterWidget(id="footer")
            yield TimersWidget(id="timers")

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
        try:
            self.call_from_thread(self._apply_pending_snapshots)
        except Exception as e:
            log.debug("call_from_thread failed: %s", e)

    async def _check_updates(self):
        """Periodic check for pending snapshot data and connection status."""
        await self._apply_pending_snapshots()
        # Switch to/from offline stage based on HTTP status
        if self.state.http_status == "error":
            if self._current_stage_name != "Offline":
                self.state.stage = "Offline"
                await self._refresh_all()
        elif self._current_stage_name == "Offline":
            # Recovered — refresh will pick up the real stage
            await self._refresh_all()
        # Refresh all Static widgets so MQTT-driven updates (dealt cards,
        # announcements, etc.) appear without waiting for an HTTP snapshot.
        try:
            await self._switch_stage(self.state.stage)
            for widget in self.query("Static"):
                widget.refresh()
        except Exception:
            pass

    async def _apply_pending_snapshots(self):
        """Drain poller queue and refresh widgets."""
        if self._poller:
            count = self._poller.drain(self.state)
            if count > 0:
                await self._refresh_all()

    async def _switch_stage(self, stage_name):
        """Swap the stage container widget if the stage changed."""
        if stage_name == self._current_stage_name:
            return

        self._current_stage_name = stage_name

        if stage_name == "Offline":
            stage_cls = OfflineStage
        else:
            stage_cls = STAGE_WIDGETS.get(stage_name)

            if stage_cls is None and stage_name != "—":
                log.error("No TUI screen for stage: %s", stage_name)
                stage_cls = UnknownStage

            if stage_cls is None:
                stage_cls = UnknownStage

        # Replace the stage container
        try:
            old = self.query_one("#stage-container")
            await old.remove()
        except Exception:
            pass

        new_widget = stage_cls(id="stage-container")
        try:
            await self.mount(new_widget, before=self.query_one("#bottom-bar"))
            log.info("Switched to stage: %s", stage_name)
        except Exception as e:
            log.error("Failed to mount stage %s: %s", stage_name, e)

        log.info("Switched to stage: %s (%s)", stage_name, stage_cls.__name__)

    async def _refresh_all(self):
        """Refresh all visible widgets and switch stage if needed."""
        await self._switch_stage(self.state.stage)
        # Refresh all Static widgets (including those nested inside VerticalScroll)
        try:
            for widget in self.query("Static"):
                widget.refresh()
        except Exception:
            pass

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
                    ("?", "Help"),
                    ("p", "Cycle poll timeout (5s/30s/60s/5m)"),
                    ("Ctrl+S", "Save state"),
                    ("Ctrl+C", "Quit"),
                    ("Esc", "Close dialog/help"),
                ]:
                    table.add_row(key, action)
                self.query_one("#help-box").update(table)

            def on_key(self, event):
                self.dismiss()

        self.push_screen(HelpScreen())

    def action_save(self):
        self.push_screen(SaveScreen(self._gwent_url, self.state))

    _POLL_PRESETS = [5, 30, 60, 300]

    async def action_cycle_poll(self):
        """Cycle through poll timeout presets."""
        current = snapshot_mod.POLL_TIMEOUT
        # Find next preset
        for preset in self._POLL_PRESETS:
            if preset > current:
                snapshot_mod.POLL_TIMEOUT = preset
                break
        else:
            snapshot_mod.POLL_TIMEOUT = self._POLL_PRESETS[0]
        log.info("Poll timeout: %ds", snapshot_mod.POLL_TIMEOUT)
        await self._refresh_all()

    def on_unmount(self):
        if self._poller:
            self._poller.stop()
        if self._subscriber:
            self._subscriber.disconnect()
        log.info("gwent-tui stopped")


def main():
    _configure_logging()

    parser = argparse.ArgumentParser(description="Gwent TUI — live game dashboard")
    parser.add_argument("--host", default="localhost",
                        help="Gwent server hostname (used for both MQTT and HTTP)")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--no-snapshot", action="store_true")
    parser.add_argument("--gwent-url", default=None,
                        help="Override HTTP state URL (default: http://<host>:8080/state)")
    args = parser.parse_args()

    gwent_url = args.gwent_url or f"http://{args.host}:8080/state"
    snapshot_mod.gwent_state_url = gwent_url

    app = GwentTUI(
        gwent_url=gwent_url,
        mqtt_host=args.host,
        mqtt_port=args.port,
        no_snapshot=args.no_snapshot,
    )
    try:
        app.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
