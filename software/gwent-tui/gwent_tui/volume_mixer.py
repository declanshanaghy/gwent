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

Touch: tap a column bar to select and set volume at that height.
       tap the mute button below each channel to toggle mute.
       tap outside the box to close.

Settings persist to ~/.config/gwent/mixer.json so reboots keep your levels.
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
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from gwent_tui import tts as tts_mod

log = logging.getLogger("gwent_tui.volume_mixer")

CONFIG_PATH = Path.home() / ".config" / "gwent" / "mixer.json"


# -----------------------------------------------------------------------------
# Channel adapters
# -----------------------------------------------------------------------------

class Channel:
    """A named volume channel: 0..100 int, with get/set callables."""

    def __init__(self, key: str, label: str, getter: Callable[[], int],
                 setter: Callable[[int], int]):
        self.key = key
        self.label = label
        self._get = getter
        self._set = setter
        self._muted_value: int | None = None  # remembered level for unmute

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

    def toggle_mute(self) -> bool:
        """Toggle mute; returns True if now muted, False if now unmuted."""
        if self.is_muted and self._muted_value is not None:
            log.info("Channel[%s] unmute -> %d", self.key, self._muted_value)
            self.set(self._muted_value)
            return False
        else:
            self._muted_value = self.value or 80  # fallback if already 0
            log.info("Channel[%s] mute (was %d)", self.key, self._muted_value)
            self.set(0)
            return True


# ----- ALSA Master adapter ---------------------------------------------------

# `-M` = mapped volume: ALSA's perceptual (≈log/dB) scale, the same one
# alsamixer uses. The PCM control spans ~-102 dB..+4 dB, so the raw linear
# percent crams all useful loudness into the top ~10%. Mapped percent spreads
# it evenly across 0..100 so the whole slider is useful.
def _alsa_get() -> int:
    try:
        out = subprocess.check_output(
            ["amixer", "-M", "get", "PCM"], stderr=subprocess.DEVNULL,
            text=True, timeout=2,
        )
        m = re.search(r"\[(\d+)%\]", out)
        return int(m.group(1)) if m else 0
    except Exception as e:
        log.warning("amixer get PCM failed: %s", e)
        return 0


def _alsa_set(value: int) -> int:
    value = max(0, min(100, int(value)))
    try:
        subprocess.run(
            ["amixer", "-M", "set", "PCM", f"{value}%"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, check=False,
        )
    except Exception as e:
        log.warning("amixer set PCM failed: %s", e)
    return value


# -----------------------------------------------------------------------------
# Persistence
# -----------------------------------------------------------------------------

def load_mixer_state() -> dict:
    try:
        with CONFIG_PATH.open() as f:
            data = json.load(f)
            log.info("mixer.json loaded: %s", data)
            return data
    except FileNotFoundError:
        return {}
    except Exception as e:
        log.warning("mixer.json read failed: %s", e)
        return {}


def save_mixer_state(state: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w") as f:
            json.dump(state, f, indent=2)
        log.debug("mixer.json saved: %s", state)
    except Exception as e:
        log.warning("mixer.json write failed: %s", e)


def apply_persisted_state() -> None:
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

class _ChannelBar(Static):
    """Volume bar for one channel — label, block bar, percentage."""

    DEFAULT_CSS = """
    _ChannelBar {
        height: 1fr;
        content-align: center top;
        text-align: center;
        padding: 0 1;
    }
    _ChannelBar.muted {
        color: $text-muted;
    }
    """

    def __init__(self, channel: Channel) -> None:
        super().__init__("")
        self.channel = channel

    # Vertical track height (rows) and inner width of the thumb/fill.
    _TRACK = 11
    _WIDTH = 9

    def refresh_bar(self) -> None:
        ch = self.channel
        val = ch.value
        muted = ch.is_muted
        n, w = self._TRACK, self._WIDTH
        # Row of the thumb: 0 = top (100%), n-1 = bottom (0%).
        pos = round((100 - val) / 100 * (n - 1))

        fill_c = "grey42" if muted else "deep_sky_blue2"
        thumb_c = "grey58" if muted else "bold black on bright_white"
        rail = " " * ((w - 1) // 2) + "┊" + " " * (w // 2)

        lines = []
        for i in range(n):
            if i == pos:
                # The grabbable thumb — a wide rectangle across the slider.
                lines.append(f"[{thumb_c}]◀{'█' * (w - 2)}▶[/]")
            elif i > pos:
                lines.append(f"[{fill_c}]{'█' * w}[/]")
            else:
                lines.append(f"[grey30]{rail}[/]")
        body = "\n".join(lines)
        self.update(f"{ch.label}\n{body}\n{val:>3}%")
        if muted:
            self.add_class("muted")
        else:
            self.remove_class("muted")

    def on_mount(self) -> None:
        self.refresh_bar()


class _ChannelColumn(Vertical):
    """One mixer channel: volume bar + mute button."""

    DEFAULT_CSS = """
    _ChannelColumn {
        width: 12;
        background: $surface;
        border: round $primary;
        padding: 0;
    }
    _ChannelColumn.selected {
        border: heavy $accent;
        background: $boost;
    }
    _ChannelColumn Button.mute-btn {
        height: 3;
        width: 100%;
        min-width: 0;
        border: tall $primary;
        margin: 0;
        content-align: center middle;
    }
    _ChannelColumn Button.mute-btn.muted {
        border: tall $warning;
        color: $warning;
    }
    """

    def __init__(self, channel: Channel) -> None:
        super().__init__()
        self.channel = channel
        self._bar: _ChannelBar | None = None
        self._btn: Button | None = None

    def compose(self) -> ComposeResult:
        self._bar = _ChannelBar(self.channel)
        yield self._bar
        self._btn = Button(
            self._mute_label(),
            id=f"mute-{self.channel.key}",
            classes="mute-btn",
        )
        yield self._btn

    def _mute_label(self) -> str:
        return "🔇" if self.channel.is_muted else "🔊"

    def refresh_col(self) -> None:
        if self._bar:
            self._bar.refresh_bar()
        if self._btn:
            muted = self.channel.is_muted
            self._btn.label = self._mute_label()
            if muted:
                self._btn.add_class("muted")
            else:
                self._btn.remove_class("muted")

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")

    @property
    def bar(self) -> _ChannelBar | None:
        return self._bar


class VolumeMixerModal(ModalScreen):
    """alsamixer-style volume modal with per-channel mute buttons."""

    DEFAULT_CSS = """
    VolumeMixerModal {
        align: center middle;
    }
    #mixer-box {
        width: 60;
        height: 90%;
        max-height: 26;
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
        height: 1fr;
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
        self._selected_idx = 0
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
            yield Static("← → channel   ↑ ↓ vol   m mute   q close",
                         id="mixer-hint")

    def on_mount(self) -> None:
        log.debug("VolumeMixerModal on_mount")
        self._refresh_all()

    # --- selection ---

    def _refresh_all(self) -> None:
        for i, col in enumerate(self._cols):
            col.refresh_col()
            col.set_selected(i == self._selected_idx)

    def action_prev_channel(self) -> None:
        self._selected_idx = (self._selected_idx - 1) % len(self._channels)
        self._refresh_all()

    def action_next_channel(self) -> None:
        self._selected_idx = (self._selected_idx + 1) % len(self._channels)
        self._refresh_all()

    # --- adjust ---

    def _adjust(self, delta: int) -> None:
        ch = self._channels[self._selected_idx]
        if ch.is_muted:
            log.debug("_adjust skipped — %s is muted", ch.key)
            return
        new_v = ch.set(ch.value + delta)
        log.info("adjust %s by %+d -> %d", ch.key, delta, new_v)
        self._cols[self._selected_idx].refresh_col()
        self._save_debounced()

    def action_louder(self) -> None:
        self._adjust(+5)

    def action_softer(self) -> None:
        self._adjust(-5)

    # --- mute ---

    def _do_toggle_mute(self, idx: int) -> None:
        ch = self._channels[idx]
        now_muted = ch.toggle_mute()
        log.info("toggle_mute %s -> muted=%s", ch.key, now_muted)
        if ch.key == "music":
            if now_muted:
                log.info("music muted — stopping playback")
                tts_mod.pause_music()
            else:
                log.info("music unmuted — resuming playback")
                tts_mod.resume_music()
        self._cols[idx].refresh_col()
        self._save_debounced()

    def action_toggle_mute(self) -> None:
        self._do_toggle_mute(self._selected_idx)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if not btn_id.startswith("mute-"):
            return
        key = btn_id[len("mute-"):]
        for i, ch in enumerate(self._channels):
            if ch.key == key:
                self._selected_idx = i
                self._do_toggle_mute(i)
                break
        event.stop()

    def action_dismiss(self) -> None:
        log.info("VolumeMixerModal dismiss; final state %s", current_state_snapshot())
        save_mixer_state(current_state_snapshot())
        self.dismiss()

    # --- touch ---

    def on_click(self, event: events.Click) -> None:
        """Tap bar to select channel + set volume at that height.
        Tap mute button to toggle mute (handled by on_button_pressed).
        Tap outside mixer box to close."""
        try:
            widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
        except Exception:
            widget = None

        # Dismiss on background click (outside #mixer-box)
        node = widget
        while node is not None:
            if getattr(node, "id", None) == "mixer-box":
                break
            node = getattr(node, "parent", None)
        else:
            log.info("VolumeMixerModal: background tap — dismissing")
            self.dismiss()
            return

        # Ignore clicks on mute buttons — Button.Pressed handles those
        node = widget
        while node is not None:
            if isinstance(node, Button):
                return
            node = getattr(node, "parent", None)

        # Find which column bar was tapped
        for i, col in enumerate(self._cols):
            bar = col.bar
            if bar is None:
                continue
            if widget is bar or widget is col or (
                    widget is not None and widget in col.walk_children()):
                self._selected_idx = i
                ch = self._channels[i]
                log.info("tap selected channel %s", ch.key)
                if ch.is_muted:
                    log.debug("tap ignored — %s is muted", ch.key)
                    self._refresh_all()
                    return
                bar_region = bar.region if bar else col.region
                if bar_region.height > 0:
                    rel_y = event.screen_y - bar_region.y
                    pct = int(round(100 * (1 - rel_y / max(1, bar_region.height - 1))))
                    pct = max(0, min(100, pct))
                    ch.set(pct)
                    log.info("tap set %s to %d%%", ch.key, pct)
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
