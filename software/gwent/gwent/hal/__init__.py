import os
import threading


def mfd_disabled() -> bool:
    """True when the OLED + rotary (MFD) are disabled via GWENT_DISABLE_MFD."""
    return os.environ.get("GWENT_DISABLE_MFD", "").lower() in (
        "1", "true", "yes", "on")


class _NoopLock:
    """No-op stand-in for spi_lock when the OLED is disabled.

    With no OLED sharing the SPI bus, the RFID reader is the sole user and
    doesn't need to serialize access — so acquire() always succeeds instantly.
    """

    def acquire(self, *args, **kwargs):
        return True

    def release(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# Shared SPI bus lock — RFID (CE0) and OLED (CE1) share the SPI bus and must
# not access it concurrently. When the OLED/rotary (MFD) is disabled, the RFID
# reader is the only SPI user, so the lock becomes a no-op (no mutex needed).
# RLock allows reentrant acquisition (e.g. redraw -> clear -> println).
spi_lock = _NoopLock() if mfd_disabled() else threading.RLock()
