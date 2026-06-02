#!/usr/bin/env python3
"""Programmatic test for the VolumeMixerModal.

Drives the modal via Textual's Pilot — exercises every binding (←/→ navigation,
↑/↓ volume adjust, m mute, q close), then verifies the persisted mixer.json.
ALSA/pygame side effects are monkey-patched so the test is hermetic and safe
to re-run on any machine.

Logs profusely to tmp/logs/test-volume-mixer.log (per feedback_profuse_logging
and feedback_tmp_relative).

Run as `just test-volume-mixer` or directly:
    /home/dshanaghy/gwent-venv/bin/python scripts/test-volume-mixer.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "tmp" / "logs" / "test-volume-mixer.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _configure_logging() -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fh = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=2,
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
    return logging.getLogger("test-mixer")


log = _configure_logging()
log.info("=== test-volume-mixer startup ===")
log.info("LOG_PATH=%s", LOG_PATH)

# -----------------------------------------------------------------------------
# Stubs — keep the test hermetic. Apply BEFORE importing volume_mixer.
# -----------------------------------------------------------------------------

# 1. Don't touch real ALSA. Track the value in a module-level int.
_alsa_value = 50


def _stub_alsa_get() -> int:
    return _alsa_value


def _stub_alsa_set(v: int) -> int:
    global _alsa_value
    _alsa_value = max(0, min(100, int(v)))
    log.debug("stub_alsa_set -> %d", _alsa_value)
    return _alsa_value


# 2. Don't touch pygame. Track in-app channels in module-level ints.
_music_v = 50
_sfx_v = 50
_tts_v = 50


def _make_tts_stubs():
    def get_v():
        return _music_v

    def set_v(v):
        global _music_v
        _music_v = max(0, min(100, int(v)))
        log.debug("stub_music_set -> %d", _music_v)
        return _music_v

    def get_s():
        return _sfx_v

    def set_s(v):
        global _sfx_v
        _sfx_v = max(0, min(100, int(v)))
        log.debug("stub_sfx_set -> %d", _sfx_v)
        return _sfx_v

    def get_t():
        return _tts_v

    def set_t(v):
        global _tts_v
        _tts_v = max(0, min(100, int(v)))
        log.debug("stub_tts_set -> %d", _tts_v)
        return _tts_v

    return get_v, set_v, get_s, set_s, get_t, set_t


# 3. Redirect mixer.json to a temp path so we don't clobber the user's.
CONFIG_TMP = REPO_ROOT / "tmp" / "test-mixer-config.json"
if CONFIG_TMP.exists():
    CONFIG_TMP.unlink()

# Install stubs by monkey-patching tts module + volume_mixer module.
from gwent_tui import tts as tts_mod
gv, sv, gs, ss, gt, st = _make_tts_stubs()
tts_mod.get_volume = gv
tts_mod.set_volume = sv
tts_mod.get_sfx_volume = gs
tts_mod.set_sfx_volume = ss
tts_mod.get_tts_volume = gt
tts_mod.set_tts_volume = st
log.info("tts module stubbed")

# Import volume_mixer AFTER tts stubs are in place (so Channel adapters bind to stubs).
from gwent_tui import volume_mixer as vm  # noqa: E402

vm._alsa_get = _stub_alsa_get
vm._alsa_set = _stub_alsa_set
vm.CONFIG_PATH = CONFIG_TMP
log.info("volume_mixer module stubbed; CONFIG_PATH=%s", CONFIG_TMP)

# Re-import the Channel adapter constants so they bind to the new stubs.
# (Channels are constructed inside the modal __init__, so they'll see the stubs.)

from textual.app import App, ComposeResult  # noqa: E402
from textual.widgets import Static  # noqa: E402


# -----------------------------------------------------------------------------
# Harness app — just opens the mixer immediately
# -----------------------------------------------------------------------------

class _Harness(App):
    BINDINGS = [("v", "open_mixer", "Open mixer")]

    def __init__(self) -> None:
        super().__init__()
        self.modal: vm.VolumeMixerModal | None = None

    def compose(self) -> ComposeResult:
        yield Static("(harness)")

    def action_open_mixer(self) -> None:
        log.info("harness opening mixer")
        self.modal = vm.VolumeMixerModal()
        self.push_screen(self.modal)


# -----------------------------------------------------------------------------
# Test cases
# -----------------------------------------------------------------------------

FAILURES: list[str] = []


def expect(condition: bool, msg: str) -> None:
    if condition:
        log.info("PASS: %s", msg)
        print(f"  PASS: {msg}")
    else:
        log.error("FAIL: %s", msg)
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


async def run_test() -> None:
    # Reset stub values to a known baseline so behavior is deterministic.
    global _alsa_value, _music_v, _sfx_v, _tts_v
    _alsa_value = 50
    _music_v = 50
    _sfx_v = 50
    _tts_v = 50

    log.info("baseline: alsa=%d music=%d sfx=%d tts=%d",
             _alsa_value, _music_v, _sfx_v, _tts_v)

    app = _Harness()
    async with app.run_test() as pilot:
        await pilot.press("v")
        await pilot.pause()  # let modal mount
        modal = app.modal
        expect(modal is not None, "modal opened on v key")
        if modal is None:
            return

        # 1. Channels in order: Master, Music, SFX, TTS
        keys = [c.key for c in modal._channels]
        expect(keys == ["alsa_pcm", "music", "sfx", "tts"],
               f"channel order is Master/Music/SFX/TTS (got {keys})")

        # 2. Master selected first
        expect(modal._selected_idx == 0,
               f"Master selected by default (idx={modal._selected_idx})")

        # 3. Right arrow advances selection
        await pilot.press("right")
        await pilot.pause()
        expect(modal._selected_idx == 1, "right -> Music")

        await pilot.press("right")
        await pilot.pause()
        expect(modal._selected_idx == 2, "right again -> SFX")

        # 4. Left arrow goes back
        await pilot.press("left")
        await pilot.pause()
        expect(modal._selected_idx == 1, "left -> Music")

        # 5. Left from leftmost wraps
        await pilot.press("left")
        await pilot.press("left")
        await pilot.pause()
        expect(modal._selected_idx == 3,
               f"left wraps to last (TTS) (idx={modal._selected_idx})")

        # 6. Right from rightmost wraps
        await pilot.press("right")
        await pilot.pause()
        expect(modal._selected_idx == 0,
               f"right wraps to first (Master) (idx={modal._selected_idx})")

        # 7. ↑ raises Master by 5%
        baseline = _alsa_value
        await pilot.press("up")
        await pilot.pause()
        expect(_alsa_value == baseline + 5,
               f"up: master {baseline} -> {_alsa_value} (expected {baseline + 5})")

        # 8. ↓ lowers by 5%
        await pilot.press("down")
        await pilot.pause()
        expect(_alsa_value == baseline,
               f"down: master back to {_alsa_value} (expected {baseline})")

        # 9. ↑ many times saturates at 100
        for _ in range(25):
            await pilot.press("up")
            await pilot.pause()
        expect(_alsa_value == 100,
               f"up x25 saturates at 100 (got {_alsa_value})")

        # 10. ↓ many times saturates at 0
        for _ in range(25):
            await pilot.press("down")
            await pilot.pause()
        expect(_alsa_value == 0,
               f"down x25 saturates at 0 (got {_alsa_value})")

        # 11. m mutes (already at 0); m again unmutes to remembered level
        # Restore a non-zero level first.
        for _ in range(8):
            await pilot.press("up")
            await pilot.pause()
        before_mute = _alsa_value
        expect(before_mute == 40, f"prep mute test (master={before_mute})")

        await pilot.press("m")
        await pilot.pause()
        expect(_alsa_value == 0, f"mute -> 0 (got {_alsa_value})")

        await pilot.press("m")
        await pilot.pause()
        expect(_alsa_value == before_mute,
               f"unmute restores prior level (got {_alsa_value}, expected {before_mute})")

        # 12. Adjust Music channel
        await pilot.press("right")  # to Music
        await pilot.pause()
        baseline_m = _music_v
        await pilot.press("up")
        await pilot.pause()
        expect(_music_v == baseline_m + 5, f"music up 5% (got {_music_v})")

        # 13. Close + verify mixer.json was written with final state
        await pilot.press("q")
        await pilot.pause()
        expect(CONFIG_TMP.exists(), f"mixer.json written to {CONFIG_TMP}")
        if CONFIG_TMP.exists():
            data = json.loads(CONFIG_TMP.read_text())
            log.info("persisted: %s", data)
            expect(data.get("alsa_pcm") == _alsa_value,
                   f"persisted alsa_pcm={data.get('alsa_pcm')} matches stub={_alsa_value}")
            expect(data.get("music") == _music_v,
                   f"persisted music={data.get('music')} matches stub={_music_v}")
            expect(data.get("sfx") == _sfx_v,
                   f"persisted sfx={data.get('sfx')} matches stub={_sfx_v}")
            expect(data.get("tts") == _tts_v,
                   f"persisted tts={data.get('tts')} matches stub={_tts_v}")

    # 14. apply_persisted_state should reapply on a fresh startup-style call.
    # Reset stubs to 0, then apply. (Globals already declared at the top of this fn.)
    _alsa_value = 0
    _music_v = 0
    _sfx_v = 0
    _tts_v = 0
    log.info("resetting stubs to 0 before apply_persisted_state()")
    vm.apply_persisted_state()
    saved = json.loads(CONFIG_TMP.read_text())
    expect(_alsa_value == saved["alsa_pcm"], "apply: alsa restored")
    expect(_music_v == saved["music"], "apply: music restored")
    expect(_sfx_v == saved["sfx"], "apply: sfx restored")
    expect(_tts_v == saved["tts"], "apply: tts restored")


def main() -> int:
    log.info("running tests")
    asyncio.run(run_test())
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)} test(s)):")
        for f in FAILURES:
            print(f"  - {f}")
        log.error("FAILED %d test(s)", len(FAILURES))
        return 1
    print("ALL PASS")
    log.info("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
