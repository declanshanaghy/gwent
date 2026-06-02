"""Volume Mixer modal — alsamixer-style 4-channel mixer (Master + Music + SFX + TTS).

Channels:
  - Master  → ALSA `PCM` mixer control (shells out to `amixer`)
  - Music   → gwent_tui.tts.set_volume / get_volume
  - SFX     → gwent_tui.tts.set_sfx_volume / get_sfx_volume
  - TTS     → gwent_tui.tts.set_tts_volume / get_tts_volume

Keybindings:
  ← / →   select channel
  ↑ / ↓   ±5%
  m       mute selected (remembers prior level for unmute)
  q / Esc close

Touch: tap a column header/bar to select that channel; tap the bar at a given
height to set the volume directly.

Settings persist to ~/.config/gwent/mixer.json so reboots keep your levels.

Logs profusely to tmp/logs/gwent-tui.log via the shared root logger.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Callable

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static

from gwent_tui import tts as tts_mod

log = logging.getLogger("gwent_tui.volume_mixer")

CONFIG_PATH = Path.home() / ".config" / "gwent" / "mixer.json"


# -----------------------------------------------------------------------------
# Channel adapters — each Channel knows how to read/write its volume.
# -----------------------------------------------------------------------------

class Channel:
    """A named volume channel: 0..100 int, with get/set callables."""

    def __init__(self, key: str, label: str, getter: Callable[[], int],
                 setter: Callable[[int], int]):
        self.key = key
        self.label = label
        self._get = getter
        self._set = setter
        self._muted_value: int | None = None  # remembered level when muted

    @property
    def value(self) -> int:
        return self._get()

    def set(self, v: int) -> int:
        v = max(0, min(100, int(v)))
        new_v = self._set(v)
        log.debug("Channel[%s] set to %d (returned %d)", self.key, v, new_v)
        return new_v

    @property
    def is_muted(self) -> bool:
        return self.value == 0

    def toggle_mute(self) -> int:
        if self.is_muted and self._muted_value is not None:
            log.info("Channel[%s] unmute -> %d", self.key, self._muted_value)
            return self.set(self._muted_value)
        else:
            self._muted_value = self.value
            log.info("Channel[%s] mute (was %d)", self.key, self._muted_value)
            return self.set(0)


# ----- ALSA Master adapter ---------------------------------------------------

def _alsa_get() -> int:
    """Return ALSA PCM playback percent (0..100), or 0 if amixer fails."""
    try:
        out = subprocess.check_output(
            ["amixer", "get", "PCM"], stderr=subprocess.DEVNULL, text=True, timeout=2,
        )
        m = re.search(r"\[(\d+)%\]", out)
        return int(m.group(1)) if m else 0
    except Exception as e:
        log.warning("amixer get PCM failed: %s", e)
        return 0


def _alsa_set(value: int) -> int:
    """Set ALSA PCM playback to `value`%. Returns the value we set."""
    value = max(0, min(100, int(value)))
    try:
        subprocess.run(
            ["amixer", "set", "PCM", f"{value}%"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, check=False,
        )
        log.debug("amixer set PCM %d%%", value)
    except Exception as e:
        log.warning("amixer set PCM failed: %s", e)
    return value


# -----------------------------------------------------------------------------
# Persistence
# -----------------------------------------------------------------------------

def load_mixer_state() -> dict:
    """Read mixer.json. Returns {} if missing/unreadable."""
    try:
        with CONFIG_PATH.open() as f:
            data = json.load(f)
            log.info("mixer.json loaded: %s", data)
            return data
    except FileNotFoundError:
        log.info("mixer.json not found at %s — using current/default values", CONFIG_PATH)
        return {}
    except Exception as e:
        log.warning("mixer.json read failed: %s", e)
        return {}


def save_mixer_state(state: dict) -> None:
    """Write mixer.json. Best-effort — logs but doesn't raise."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w") as f:
            json.dump(state, f, indent=2)
        log.debug("mixer.json saved: %s", state)
    except Exception as e:
        log.warning("mixer.json write failed: %s", e)


def apply_persisted_state() -> None:
    """Load mixer.json and apply each known channel.

    Call from the App's on_mount so persisted levels are restored at startup.
    """
    data = load_mixer_state()
    if not data:
        return
    if "alsa_pcm" in data:
        _alsa_set(int(data["alsa_pcm"]))
    if "music" in data:
        tts_mod.set_volume(int(data["music"]))
    if "sfx" in data:
        tts_mod.set_sfx_volume(int(data["sfx"]))
    if "tts" in data:
        tts_mod.set_tts_volume(int(data["tts"]))
    log.info("Mixer state applied from %s", CONFIG_PATH)


def current_state_snapshot() -> dict:
    return {
        "alsa_pcm": _alsa_get(),
        "music": tts_mod.get_volume(),
        "sfx": tts_mod.get_sfx_volume(),
        "tts": tts_mod.get_tts_volume(),
    }


# -----------------------------------------------------------------------------
# Widgets
# -----------------------------------------------------------------------------

class _ChannelColumn(Static):
    """A vertical bar showing one channel's volume."""

    DEFAULT_CSS = """
    _ChannelColumn {
        width: 12;
        height: 100%;
        background: $surface;
        color: $text;
        content-align: center top;
        border: round $primary;
        padding: 0 1;
    }
    _ChannelColumn.selected {
        border: heavy $accent;
        background: $boost;
    }
    """

    def __init__(self, channel: Channel) -> None:
        super().__init__(self._render_text(channel))
        self.channel = channel

    @staticmethod
    def _render_text(ch: Channel) -> str:
        val = ch.value
        # Build a vertical bar using block characters. 10 segments.
        filled = val // 10
        # Some "soft" half-block when value % 10 >= 5.
        half = "▄" if (val % 10) >= 5 else " "
        bar_lines = []
        for i in range(10, 0, -1):
            if i <= filled:
                bar_lines.append("█")
            elif i == filled + 1 and half == "▄":
                bar_lines.append(half)
            else:
                bar_lines.append(" ")
        # 'M' indicator when muted
        mute_indicator = "🔇" if ch.is_muted else "  "
        body = "\n".join(bar_lines)
        return f"{ch.label}\n{mute_indicator}\n{body}\n{val:>3}%"

    def refresh_text(self) -> None:
        self.update(self._render_text(self.channel))

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")


class VolumeMixerModal(ModalScreen):
    """alsamixer-style volume modal."""

    DEFAULT_CSS = """
    VolumeMixerModal {
        align: center middle;
    }
    #mixer-box {
        width: 60;
        height: 22;
        background: $panel;
        border: thick $accent;
        padding: 1;
    }
    #mixer-title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }
    #mixer-row {
        height: 18;
        align: center middle;
    }
    #mixer-hint {
        height: 1;
        content-align: center middle;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("left", "prev_channel", "Prev channel"),
        Binding("right", "next_channel", "Next channel"),
        Binding("up", "louder", "Louder"),
        Binding("down", "softer", "Softer"),
        Binding("m", "toggle_mute", "Mute"),
        Binding("q", "dismiss", "Close"),
        Binding("escape", "dismiss", "Close"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._channels: list[Channel] = [
            Channel("alsa_pcm", "Master", _alsa_get, _alsa_set),
            Channel("music", "Music", tts_mod.get_volume, tts_mod.set_volume),
            Channel("sfx", "SFX", tts_mod.get_sfx_volume, tts_mod.set_sfx_volume),
            Channel("tts", "TTS", tts_mod.get_tts_volume, tts_mod.set_tts_volume),
        ]
        self._selected_idx = 0  # Master selected by default
        self._cols: list[_ChannelColumn] = []
        self._last_save = 0.0
        log.info(
            "VolumeMixerModal __init__ — initial state %s",
            {c.key: c.value for c in self._channels},
        )

    def compose(self) -> ComposeResult:
        with Container(id="mixer-box"):
            yield Static("VOLUME", id="mixer-title")
            with Horizontal(id="mixer-row"):
                for c in self._channels:
                    col = _ChannelColumn(c)
                    self._cols.append(col)
                    yield col
            yield Static("← → channel   ↑ ↓ vol   m mute   q close", id="mixer-hint")

    def on_mount(self) -> None:
        log.debug("VolumeMixerModal on_mount")
        self._refresh_all()

    # --- selection ---

    def _refresh_all(self) -> None:
        for i, col in enumerate(self._cols):
            col.refresh_text()
            col.set_selected(i == self._selected_idx)

    def action_prev_channel(self) -> None:
        self._selected_idx = (self._selected_idx - 1) % len(self._channels)
        log.debug("prev_channel -> %s", self._channels[self._selected_idx].key)
        self._refresh_all()

    def action_next_channel(self) -> None:
        self._selected_idx = (self._selected_idx + 1) % len(self._channels)
        log.debug("next_channel -> %s", self._channels[self._selected_idx].key)
        self._refresh_all()

    # --- adjust ---

    def _adjust(self, delta: int) -> None:
        ch = self._channels[self._selected_idx]
        new_v = ch.set(ch.value + delta)
        log.info("adjust %s by %+d -> %d", ch.key, delta, new_v)
        self._cols[self._selected_idx].refresh_text()
        self._save_debounced()

    def action_louder(self) -> None:
        self._adjust(+5)

    def action_softer(self) -> None:
        self._adjust(-5)

    def action_toggle_mute(self) -> None:
        ch = self._channels[self._selected_idx]
        ch.toggle_mute()
        self._cols[self._selected_idx].refresh_text()
        self._save_debounced()

    def action_dismiss(self) -> None:
        log.info("VolumeMixerModal dismiss; final state %s", current_state_snapshot())
        # Force a final save regardless of debounce.
        save_mixer_state(current_state_snapshot())
        self.dismiss()

    # --- touch ---

    def on_click(self, event: events.Click) -> None:
        """Tap on a column selects it; tap on a column AT a height sets vol."""
        # Find which column the click hit by walking widgets at the click pos.
        try:
            widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
        except Exception:
            widget = None
        for i, col in enumerate(self._cols):
            if widget is col or (widget is not None and widget in col.walk_children()):
                if self._selected_idx != i:
                    self._selected_idx = i
                    log.info(
                        "click selected channel %s via (%d,%d)",
                        self._channels[i].key, event.screen_x, event.screen_y,
                    )
                # Map the y offset within the column to a volume.
                # The bar occupies the middle 10 rows of the 18-row mixer-row.
                # Approximate: tapping high in the column = high volume.
                col_region = col.region
                if col_region.height > 0:
                    rel_y = event.screen_y - col_region.y
                    pct = int(round(100 * (1 - rel_y / max(1, col_region.height - 1))))
                    pct = max(0, min(100, pct))
                    self._channels[i].set(pct)
                    log.info(
                        "click set %s to %d%% (rel_y=%d region_h=%d)",
                        self._channels[i].key, pct, rel_y, col_region.height,
                    )
                self._refresh_all()
                self._save_debounced()
                return

    # --- persistence ---

    def _save_debounced(self) -> None:
        now = time.monotonic()
        if now - self._last_save < 0.25:
            return
        self._last_save = now
        save_mixer_state(current_state_snapshot())
