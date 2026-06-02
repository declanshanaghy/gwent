#!/usr/bin/env python3
"""touch-to-mouse — bridge a Linux touchscreen to a virtual pointer.

The official Raspberry Pi 7" DSI touchscreen exposes only a `touch`-capability
input device. libinput therefore does NOT emit `wl_pointer` emulation events,
and kitty 0.41 only consumes `wl_pointer` (not `wl_touch`). Result: taps don't
reach Textual as clicks.

This daemon reads touch events from /dev/input/event*-with-BTN_TOUCH and writes
them to a uinput virtual pointer (ABS_X / ABS_Y / BTN_LEFT). libinput discovers
the new device as a real pointer; cage forwards wl_pointer to kitty; kitty
emits xterm mouse escapes; Textual fires Click events.

Run as root (or with CAP_SYS_ADMIN / write access to /dev/uinput and the source
event device). systemd unit installs at /etc/systemd/system/gwent-touch.service
via scripts/install-kiosk.sh.

Logs to tmp/logs/touch-to-mouse.log (repo-relative).
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import time
from pathlib import Path

from evdev import (
    AbsInfo,
    InputDevice,
    UInput,
    ecodes,
    list_devices,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "tmp" / "logs" / "touch-to-mouse.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("TOUCH_DEBUG") else logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("touch-to-mouse")


def find_touchscreen() -> InputDevice | None:
    """Return the first /dev/input device exposing BTN_TOUCH + ABS_X + ABS_Y."""
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except (OSError, PermissionError):
            continue
        caps = dev.capabilities()
        keys = caps.get(ecodes.EV_KEY, [])
        absx = caps.get(ecodes.EV_ABS, [])
        abs_codes = {code for code, _info in absx} if absx and isinstance(absx[0], tuple) else set()
        if ecodes.BTN_TOUCH in keys and ecodes.ABS_X in abs_codes and ecodes.ABS_Y in abs_codes:
            return dev
        dev.close()
    return None


def main() -> int:
    src = find_touchscreen()
    if src is None:
        log.error("no touchscreen with BTN_TOUCH/ABS_X/ABS_Y found")
        return 1

    abs_x_info = next(info for code, info in src.capabilities()[ecodes.EV_ABS] if code == ecodes.ABS_X)
    abs_y_info = next(info for code, info in src.capabilities()[ecodes.EV_ABS] if code == ecodes.ABS_Y)
    log.info(
        "source: %s (path=%s) extents=(%d-%d, %d-%d)",
        src.name,
        src.path,
        abs_x_info.min,
        abs_x_info.max,
        abs_y_info.min,
        abs_y_info.max,
    )

    caps = {
        ecodes.EV_KEY: [ecodes.BTN_LEFT],
        ecodes.EV_ABS: [
            (ecodes.ABS_X, AbsInfo(0, abs_x_info.min, abs_x_info.max, 0, 0, 0)),
            (ecodes.ABS_Y, AbsInfo(0, abs_y_info.min, abs_y_info.max, 0, 0, 0)),
        ],
    }
    ui = UInput(caps, name="gwent-touch-pointer", vendor=0xABCD, product=0x0001)
    log.info("uinput device created: %s", ui.device.path)

    # State
    btn_down = False
    last_x: int | None = None
    last_y: int | None = None
    stop = False

    def _sigterm(signum, frame):
        nonlocal stop
        log.info("signal %d received; exiting", signum)
        stop = True

    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    # select() with timeout so we can periodically check the `stop` flag —
    # avoids hanging in read_loop() when no touch events are arriving.
    import select as _select
    src_fd = src.fileno()

    try:
        while not stop:
            r, _, _ = _select.select([src_fd], [], [], 0.5)
            if not r:
                continue
            try:
                events_batch = list(src.read())
            except BlockingIOError:
                continue
            for event in events_batch:
                if stop:
                    break
                etype = event.type
                ecode = event.code
                evalue = event.value

                if etype == ecodes.EV_ABS:
                    if ecode == ecodes.ABS_X:
                        last_x = evalue
                        ui.write(ecodes.EV_ABS, ecodes.ABS_X, evalue)
                    elif ecode == ecodes.ABS_Y:
                        last_y = evalue
                        ui.write(ecodes.EV_ABS, ecodes.ABS_Y, evalue)
                elif etype == ecodes.EV_KEY and ecode == ecodes.BTN_TOUCH:
                    btn_down = bool(evalue)
                    ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, evalue)
                    log.debug("BTN_LEFT %s at (%s, %s)", "down" if btn_down else "up", last_x, last_y)
                elif etype == ecodes.EV_SYN:
                    ui.syn()
    except KeyboardInterrupt:
        pass
    finally:
        ui.close()
        src.close()
        log.info("clean exit")

    return 0


if __name__ == "__main__":
    sys.exit(main())
