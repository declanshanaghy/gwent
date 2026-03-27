"""Main application: wires up MQTT, snapshot poller, and renderer with rich Live."""

import argparse
import logging
import logging.handlers
import os
import signal
import time

from rich.live import Live
from rich.console import Console

from gwent_tui.game_state import GameState
from gwent_tui.keyboard import KeyboardReader, KEY_CTRL_S, KEY_ARROW_UP, KEY_ARROW_DOWN
from gwent_tui.mqtt_client import MqttSubscriber
from gwent_tui.renderer import Renderer
from gwent_tui.save_dialog import SaveDialog
from gwent_tui.snapshot import SnapshotPoller, load_snapshot
import gwent_tui.snapshot as snapshot_mod

log = logging.getLogger("gwent_tui.app")

DEFAULT_SNAPSHOT_INTERVAL = 5.0  # seconds between full state refreshes
DEFAULT_GWENT_URL = "http://localhost:8080/state"


def _configure_logging():
    """Set up rotating file logging for gwent-tui (no stdout — would corrupt Rich)."""
    log_file = "/tmp/logs/gwent-tui.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=50 * 1024 * 1024, backupCount=3, delay=True,
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Rotate on startup if log exists and has content
    if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
        fh.doRollover()


def main():
    _configure_logging()

    parser = argparse.ArgumentParser(description="Gwent TUI — live game dashboard")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument(
        "--no-snapshot", action="store_true",
        help="Skip loading snapshots entirely (MQTT-only mode)",
    )
    parser.add_argument(
        "--snapshot-interval", type=float, default=DEFAULT_SNAPSHOT_INTERVAL,
        help=f"Seconds between full state refreshes (default: {DEFAULT_SNAPSHOT_INTERVAL})",
    )
    parser.add_argument(
        "--gwent-url", default=DEFAULT_GWENT_URL,
        help=f"Gwent HTTP API state URL (default: {DEFAULT_GWENT_URL})",
    )
    args = parser.parse_args()

    log.info("gwent-tui starting (url=%s, interval=%.1fs)", args.gwent_url, args.snapshot_interval)

    # Configure snapshot module with the URL
    snapshot_mod.gwent_state_url = args.gwent_url

    console = Console()
    state = GameState()
    renderer = Renderer()
    save_dialog = SaveDialog(args.gwent_url, state)

    # Load initial snapshot synchronously
    if not args.no_snapshot:
        console.print("[dim]Loading game state from HTTP API...[/dim]")
        if load_snapshot(state):
            console.print("[green]Snapshot loaded.[/green]")
            log.info("Initial snapshot loaded")
        else:
            console.print("[yellow]Gwent server not reachable — starting empty.[/yellow]")
            log.warning("Initial snapshot failed — server not reachable at %s", args.gwent_url)

    # Connect MQTT
    subscriber = MqttSubscriber(state, host=args.host, port=args.port)
    subscriber.connect()

    # Start background snapshot poller
    poller = None
    if not args.no_snapshot:
        poller = SnapshotPoller(interval=args.snapshot_interval)
        poller.start()

    # Graceful shutdown
    running = True

    def shutdown(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Help screen toggle
    show_help = [False]

    # UI dirty flag — set when keyboard/dialog changes need a re-render
    ui_dirty = [True]  # start dirty to render initial frame

    # Keyboard input handler
    def on_key(key):
        nonlocal running
        log.debug("Key received: %r dialog_active=%s", key, save_dialog.active)
        if save_dialog.active:
            save_dialog.handle_key(key)
        elif show_help[0]:
            show_help[0] = False
        elif key == "?":
            show_help[0] = True
        elif key == KEY_ARROW_UP:
            if poller:
                poller.interval = min(30.0, poller.interval + 1.0)
                log.info("Poll interval: %.0fs", poller.interval)
        elif key == KEY_ARROW_DOWN:
            if poller:
                poller.interval = max(1.0, poller.interval - 1.0)
                log.info("Poll interval: %.0fs", poller.interval)
        elif key == KEY_CTRL_S:
            save_dialog.open()
        elif key == "\x03":  # Ctrl+C
            running = False
            return
        ui_dirty[0] = True
        if poller:
            poller.data_ready.set()  # wake main loop for UI changes too

    keyboard = KeyboardReader(on_key)
    keyboard.start()

    # Main render loop — only renders when new data arrives or UI changes
    try:
        with Live(
            renderer.render(state, save_dialog, show_help[0], poller),
            console=console,
            refresh_per_second=1,
            screen=True,
        ) as live:
            while running:
                # Block until new data or UI change, with timeout as fallback
                if poller:
                    poller.data_ready.wait(timeout=1.0)
                    poller.data_ready.clear()
                else:
                    time.sleep(1.0)

                needs_render = False

                # Drain snapshot queue
                if poller:
                    count = poller.drain(state)
                    if count > 0:
                        needs_render = True

                # Check for UI-triggered changes
                if ui_dirty[0]:
                    ui_dirty[0] = False
                    needs_render = True

                if needs_render:
                    live.update(renderer.render(state, save_dialog, show_help[0], poller))
    except KeyboardInterrupt:
        pass
    finally:
        if poller:
            poller.stop()
        keyboard.stop()
        subscriber.disconnect()
        log.info("gwent-tui stopped")
        console.print("[dim]gwent-tui stopped.[/dim]")


if __name__ == "__main__":
    main()
