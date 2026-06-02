#!/usr/bin/env python3
"""Interactive volume mixer test — drives the real modal on the panel.

Unlike test-volume-mixer.py (headless, all stubbed), this script asks YOU to
perform every interaction by hand. It opens the actual VolumeMixerModal
against the real AudioMixer + ALSA, then walks you through a checklist:

  1. Navigate channels with ← / →
  2. Adjust the selected channel with ↑ / ↓
  3. Toggle mute with `m`
  4. Tap a column to select it
  5. Tap on the bar at a specific height to jump volume
  6. Close with `q`

After you close the mixer, prints a summary of what happened (which
channels were touched, how many key vs. mouse events, persistence written,
etc.). Each step has a pass/fail outcome based on observation, not a
contrived assertion.

Profuse logging to tmp/logs/test-volume-mixer-interactive.log.
Run via:
    just test-volume-mixer-ui     # uses kitty wrapper, sets KITTY_WINDOW_ID
or:
    /home/dshanaghy/gwent-venv/bin/python scripts/test-volume-mixer-interactive.py
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "tmp" / "logs" / "test-volume-mixer-interactive.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _configure_logging() -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fh = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=2
    )
    fh.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)-5s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    root.addHandler(sh)
    return logging.getLogger("test-mixer-ui")


log = _configure_logging()
log.info("=== test-volume-mixer-interactive startup ===")
log.info("LOG_PATH=%s", LOG_PATH)
log.info(
    "env: TERM=%s KITTY_WINDOW_ID=%s WAYLAND_DISPLAY=%s XDG_SESSION_TYPE=%s",
    os.environ.get("TERM"),
    os.environ.get("KITTY_WINDOW_ID"),
    os.environ.get("WAYLAND_DISPLAY"),
    os.environ.get("XDG_SESSION_TYPE"),
)

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static

from gwent_tui import volume_mixer as vm


# -----------------------------------------------------------------------------
# Tracking
# -----------------------------------------------------------------------------

class Tracker:
    def __init__(self) -> None:
        self.opened_at: float | None = None
        self.closed_at: float | None = None
        self.key_events: list[str] = []
        self.click_events: list[tuple[int, int]] = []
        self.channel_selections: list[str] = []
        self.value_changes: dict[str, list[int]] = {
            "alsa_pcm": [], "music": [], "sfx": [], "tts": [],
        }
        self.mute_toggles = 0

    def report(self) -> str:
        duration = (self.closed_at - self.opened_at) if (self.opened_at and self.closed_at) else 0
        lines = []
        lines.append("=" * 64)
        lines.append("VOLUME MIXER — INTERACTIVE TEST RESULTS")
        lines.append("=" * 64)
        lines.append(f"  Session duration: {duration:.1f}s")
        lines.append(f"  Total key events:   {len(self.key_events)}  ({', '.join(self.key_events[:20])}{'...' if len(self.key_events) > 20 else ''})")
        lines.append(f"  Total click events: {len(self.click_events)}")
        if self.click_events:
            lines.append(f"    sample positions: {self.click_events[:6]}")
        lines.append(f"  Channel selections: {len(self.channel_selections)}  ({' → '.join(self.channel_selections[:10])}{'...' if len(self.channel_selections) > 10 else ''})")
        lines.append(f"  Mute toggles: {self.mute_toggles}")
        lines.append("  Volume movements per channel:")
        for k, vs in self.value_changes.items():
            if vs:
                lines.append(f"    {k:9s}: start={vs[0]:3d}  end={vs[-1]:3d}  steps={len(vs)}  min={min(vs):3d}  max={max(vs):3d}")
            else:
                lines.append(f"    {k:9s}: (no change)")
        lines.append("")
        lines.append("CHECKLIST RESULTS")
        return "\n".join(lines)

    def checklist(self) -> list[tuple[bool, str]]:
        clicks = len(self.click_events) > 0
        keys = len(self.key_events) > 0
        nav = len(self.channel_selections) > 1
        adjusted = any(len(v) >= 2 for v in self.value_changes.values())
        touched_via_click_only = any(
            "click" in s for s in self.channel_selections
        )
        all_channels_touched = sum(
            1 for v in self.value_changes.values() if v
        ) >= 2
        muted = self.mute_toggles > 0
        return [
            (keys, "Keyboard input received (at least one key press)"),
            (clicks, "Touch / click input received (at least one tap)"),
            (nav, "Navigated between at least two channels"),
            (adjusted, "Adjusted at least one channel's volume"),
            (all_channels_touched, "Adjusted at least 2 different channels"),
            (touched_via_click_only, "Selected a channel by tapping (not just keys)"),
            (muted, "Toggled mute at least once"),
        ]


TRACKER = Tracker()


# -----------------------------------------------------------------------------
# Subclass of VolumeMixerModal that records every interaction
# -----------------------------------------------------------------------------

class _RecordedMixer(vm.VolumeMixerModal):
    def on_mount(self) -> None:  # type: ignore[override]
        super().on_mount()
        TRACKER.opened_at = time.monotonic()
        TRACKER.channel_selections.append(self._channels[self._selected_idx].key)
        for c in self._channels:
            TRACKER.value_changes[c.key].append(c.value)
        log.info("mixer opened. initial: %s", {c.key: c.value for c in self._channels})

    def _record_channel_state(self, source: str) -> None:
        sel = self._channels[self._selected_idx].key
        if TRACKER.channel_selections[-1] != sel:
            TRACKER.channel_selections.append(f"{sel}({source})")
            log.info("selection -> %s via %s", sel, source)
        for c in self._channels:
            history = TRACKER.value_changes[c.key]
            if not history or history[-1] != c.value:
                history.append(c.value)
                log.debug("value[%s] -> %d", c.key, c.value)

    def action_prev_channel(self) -> None:  # type: ignore[override]
        super().action_prev_channel()
        self._record_channel_state("key")

    def action_next_channel(self) -> None:  # type: ignore[override]
        super().action_next_channel()
        self._record_channel_state("key")

    def action_louder(self) -> None:  # type: ignore[override]
        super().action_louder()
        self._record_channel_state("key")

    def action_softer(self) -> None:  # type: ignore[override]
        super().action_softer()
        self._record_channel_state("key")

    def action_toggle_mute(self) -> None:  # type: ignore[override]
        super().action_toggle_mute()
        TRACKER.mute_toggles += 1
        log.info("mute toggle (#%d)", TRACKER.mute_toggles)
        self._record_channel_state("key")

    def action_dismiss(self) -> None:  # type: ignore[override]
        TRACKER.closed_at = time.monotonic()
        log.info("mixer dismissed")
        super().action_dismiss()

    def on_click(self, event: events.Click) -> None:  # type: ignore[override]
        TRACKER.click_events.append((event.screen_x, event.screen_y))
        log.info("CLICK on mixer screen=(%d,%d)", event.screen_x, event.screen_y)
        super().on_click(event)
        self._record_channel_state("click")

    def on_key(self, event: events.Key) -> None:  # type: ignore[override]
        TRACKER.key_events.append(event.key)
        log.debug("KEY %r", event.key)
        # Don't call super().on_key — Textual handles bindings via action_*.


# -----------------------------------------------------------------------------
# Harness app — shows instructions, opens the mixer on `v` (auto on mount).
# -----------------------------------------------------------------------------

INSTRUCTIONS = """\
INTERACTIVE VOLUME MIXER TEST

You should see a 4-channel mixer modal appear after a moment.
Please drive every interaction at least once:

  • Press  ← / →   to navigate between Master / Music / SFX / TTS
  • Press  ↑ / ↓   to raise / lower the selected channel
  • Press  m       to mute / unmute
  • TAP    a column header to select it with touch
  • TAP    high or low on a bar to jump the volume
  • Press  q       to close (results print on exit)

The on-screen log below records what we detect."""


class _HarnessApp(App):
    CSS = """
    Screen { background: $surface; }
    #instructions { padding: 1 2; height: auto; color: $text; background: $boost; border: round $accent; }
    #status { dock: bottom; height: 3; content-align: center middle; color: $text-muted; }
    """

    BINDINGS = [
        Binding("v", "open_mixer", "Open mixer", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(INSTRUCTIONS, id="instructions")
            yield Static("(mixer will open on launch — press q inside it to finish)", id="status")

    def on_mount(self) -> None:
        log.info("harness mounted; opening mixer immediately")
        self.set_timer(0.5, self._open_mixer)

    def _open_mixer(self) -> None:
        self.push_screen(_RecordedMixer())

    def action_open_mixer(self) -> None:
        self._open_mixer()

    def on_screen_resume(self) -> None:
        # When the mixer dismisses, this harness becomes active again — exit.
        if TRACKER.closed_at is not None:
            log.info("mixer closed; printing summary and exiting")
            self.exit(result=0)


def _print_summary() -> int:
    report = TRACKER.report()
    print(report)
    log.info("\n%s", report)
    checklist = TRACKER.checklist()
    fail_count = 0
    for ok, label in checklist:
        mark = "✓" if ok else "✗"
        line = f"  {mark} {label}"
        print(line)
        log.info(line)
        if not ok:
            fail_count += 1
    print()
    print(f"Log file: {LOG_PATH}")
    if fail_count:
        print(f"INCOMPLETE: {fail_count} of {len(checklist)} item(s) not exercised")
        return 2
    print("ALL CHECKLIST ITEMS EXERCISED — visual & touch path looks good")
    return 0


def main() -> int:
    if not os.environ.get("TERM", "").startswith("xterm-kitty"):
        log.warning(
            "TERM=%r does not look like kitty — touch + Textual mouse may not work. "
            "Run inside the kiosk's kitty (just test-volume-mixer-ui).",
            os.environ.get("TERM"),
        )

    app = _HarnessApp()
    try:
        app.run()
    except KeyboardInterrupt:
        log.info("Ctrl+C")
    finally:
        return _print_summary()


if __name__ == "__main__":
    sys.exit(main())
