"""Main application: wires up MQTT, snapshot, and renderer with rich Live."""

import argparse
import logging
import logging.handlers
import os
import signal
import time

from rich.live import Live
from rich.console import Console

from gwent_tui.game_state import GameState
from gwent_tui.keyboard import KeyboardReader, KEY_CTRL_S
from gwent_tui.mqtt_client import MqttSubscriber
from gwent_tui.renderer import Renderer
from gwent_tui.save_dialog import SaveDialog
from gwent_tui import snapshot

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
        "--refresh", type=float, default=2.0,
        help="Display refresh rate in Hz (default: 2)",
    )
    parser.add_argument(
        "--gwent-url", default=DEFAULT_GWENT_URL,
        help=f"Gwent HTTP API state URL (default: {DEFAULT_GWENT_URL})",
    )
    args = parser.parse_args()

    log.info("gwent-tui starting (url=%s, interval=%.1fs)", args.gwent_url, args.snapshot_interval)

    # Configure snapshot module with the URL
    snapshot.gwent_state_url = args.gwent_url

    console = Console()
    state = GameState()
    renderer = Renderer()
    save_dialog = SaveDialog(args.gwent_url, state)

    # Load initial snapshot
    if not args.no_snapshot:
        console.print("[dim]Loading game state from HTTP API...[/dim]")
        if snapshot.load_snapshot(state):
            console.print("[green]Snapshot loaded.[/green]")
            log.info("Initial snapshot loaded")
        else:
            console.print("[yellow]Gwent server not reachable — starting empty.[/yellow]")
            log.warning("Initial snapshot failed — server not reachable at %s", args.gwent_url)

    # Connect MQTT
    subscriber = MqttSubscriber(state, host=args.host, port=args.port)
    subscriber.connect()

    # Graceful shutdown
    running = True

    def shutdown(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keyboard input handler
    def on_key(key):
        nonlocal running
        log.debug("Key received: %r dialog_active=%s", key, save_dialog.active)
        if save_dialog.active:
            save_dialog.handle_key(key)
        elif key == KEY_CTRL_S:
            save_dialog.open()
        elif key == "\x03":  # Ctrl+C
            running = False

    keyboard = KeyboardReader(on_key)
    keyboard.start()

    # Main render loop — renders at snapshot interval (default 5s)
    last_snapshot = time.monotonic()

    try:
        with Live(
            renderer.render(state, save_dialog),
            console=console,
            refresh_per_second=1,
            screen=True,
        ) as live:
            while running:
                # Periodic snapshot to refresh board/hands/decks/discard
                now = time.monotonic()
                if (
                    not args.no_snapshot
                    and now - last_snapshot >= args.snapshot_interval
                ):
                    snapshot.load_snapshot(state)
                    last_snapshot = now

                live.update(renderer.render(state, save_dialog))
                time.sleep(args.snapshot_interval)
    except KeyboardInterrupt:
        pass
    finally:
        keyboard.stop()
        subscriber.disconnect()
        log.info("gwent-tui stopped")
        console.print("[dim]gwent-tui stopped.[/dim]")


if __name__ == "__main__":
    main()
