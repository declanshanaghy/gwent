#!/usr/bin/env python3
"""Touch verification — 3×3 grid of tappable cells with profuse logging.

Logs EVERY event (lifecycle, mouse, key, errors) to tmp/logs/test-touch.log
plus stdout. The kiosk panel has no developer console, so we lean heavily on
the log — `tail -f tmp/logs/test-touch.log` over SSH while you tap.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import time
import traceback
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual import events

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "tmp" / "logs" / "test-touch.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _configure_logging() -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # File handler — rotating so logs don't grow unbounded across reruns.
    fh = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=3
    )
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s.%(msecs)03d %(levelname)-5s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(fh)
    # Stdout handler — visible in kitty if user runs interactively.
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    root.addHandler(sh)
    return logging.getLogger("test-touch")


log = _configure_logging()
log.info("=== test-touch startup ===")
log.info("REPO_ROOT=%s", REPO_ROOT)
log.info("LOG_PATH=%s", LOG_PATH)
log.info(
    "env: TERM=%s KITTY_WINDOW_ID=%s WAYLAND_DISPLAY=%s XDG_SESSION_TYPE=%s",
    os.environ.get("TERM"),
    os.environ.get("KITTY_WINDOW_ID"),
    os.environ.get("WAYLAND_DISPLAY"),
    os.environ.get("XDG_SESSION_TYPE"),
)
log.info("python=%s", sys.version.split()[0])
try:
    import textual
    log.info("textual version=%s", getattr(textual, "__version__", "?"))
except Exception:
    log.exception("could not import textual for version probe")


class Cell(Static):
    """A tappable grid cell."""
    DEFAULT_CSS = """
    Cell {
        background: $primary-darken-2;
        color: white;
        border: heavy white;
        content-align: center middle;
        text-style: bold;
    }
    Cell.tapped {
        background: $success;
        color: black;
    }
    """

    def __init__(self, label: str, idx: int) -> None:
        super().__init__(label)
        self._taps = 0
        self._idx = idx
        log.debug("Cell[%d] __init__ label=%r", idx, label)

    def on_mount(self) -> None:
        log.debug("Cell[%d] on_mount size=%s", self._idx, self.size)

    def on_click(self, event: events.Click) -> None:
        self._taps += 1
        self.add_class("tapped")
        log.info(
            "Cell[%d] CLICK x=%d y=%d button=%d ctrl=%s meta=%s taps=%d",
            self._idx, event.x, event.y, event.button,
            event.ctrl, event.meta, self._taps,
        )


class TouchTestApp(App):
    CSS = """
    Screen { background: $surface; }
    #title { dock: top; height: 1; content-align: center middle; background: $accent; color: black; text-style: bold; }
    #status { dock: bottom; height: 3; content-align: center middle; background: $boost; color: $text; }
    #grid { layout: grid; grid-size: 3 3; grid-gutter: 0; }
    """
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self._events: list[dict] = []
        self._down_at: float | None = None
        self._cells: list[Cell] = []
        log.info("TouchTestApp __init__")

    def compose(self) -> ComposeResult:
        log.info("compose() start")
        yield Static("TOUCH TEST  —  tap the cells  —  q to quit", id="title")
        self._cells = [Cell(str(i + 1), i) for i in range(9)]
        with Container(id="grid"):
            for c in self._cells:
                yield c
        yield Static("(no taps yet)", id="status")
        log.info("compose() done — 1 title + 9 cells + 1 status")

    def on_mount(self) -> None:
        log.info(
            "on_mount: console size=%dx%d driver=%s",
            self.size.width, self.size.height,
            type(self._driver).__name__ if self._driver else "?",
        )
        try:
            from textual import constants as _c
            log.debug("textual driver class=%s", _c)
        except Exception:
            pass

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self._down_at = time.monotonic()
        log.debug(
            "MouseDown x=%d y=%d button=%d screen=(%d,%d) at t=%.6f",
            event.x, event.y, event.button,
            event.screen_x, event.screen_y, self._down_at,
        )

    def on_mouse_up(self, event: events.MouseUp) -> None:
        log.debug(
            "MouseUp   x=%d y=%d button=%d",
            event.x, event.y, event.button,
        )

    def on_mouse_move(self, event: events.MouseMove) -> None:
        # Verbose — only log if a button is held (i.e. drag).
        if event.button:
            log.debug("MouseMove x=%d y=%d button=%d", event.x, event.y, event.button)

    def on_click(self, event: events.Click) -> None:
        now = time.monotonic()
        duration_ms = int((now - (self._down_at or now)) * 1000)
        self._down_at = None
        rec = {
            "ts": time.strftime("%H:%M:%S"),
            "x": event.x,
            "y": event.y,
            "screen_x": event.screen_x,
            "screen_y": event.screen_y,
            "button": event.button,
            "duration_ms": duration_ms,
        }
        self._events.append(rec)
        log.info(
            "APP CLICK x=%d y=%d screen=(%d,%d) button=%d duration_ms=%d total=%d",
            event.x, event.y, event.screen_x, event.screen_y,
            event.button, duration_ms, len(self._events),
        )
        status = self.query_one("#status", Static)
        status.update(
            f"last: ({event.x}, {event.y})  button {event.button}  "
            f"{duration_ms} ms     total events: {len(self._events)}"
        )

    def on_key(self, event: events.Key) -> None:
        log.info("Key key=%r character=%r name=%s", event.key, event.character, event.name)

    def on_resize(self, event: events.Resize) -> None:
        log.info("Resize new_size=%dx%d", event.size.width, event.size.height)

    def on_unmount(self) -> None:
        log.info("on_unmount — events=%d", len(self._events))
        self._summary()

    def _summary(self) -> None:
        n = len(self._events)
        avg = sum(e["duration_ms"] for e in self._events) / n if n else 0
        summary = f"SUMMARY events={n} avg_duration_ms={avg:.1f}"
        log.info(summary)
        print(summary)
        if n == 0:
            log.error("FAIL: no click events received")
            print("FAIL: no click events received", file=sys.stderr)
            sys.exit(2)
        log.info("PASS")
        print("PASS")


def main() -> None:
    log.info("entering main()")
    try:
        TouchTestApp().run()
    except SystemExit:
        raise
    except BaseException:
        log.error("unhandled exception in run:\n%s", traceback.format_exc())
        raise
    log.info("main() returned cleanly")


if __name__ == "__main__":
    main()
