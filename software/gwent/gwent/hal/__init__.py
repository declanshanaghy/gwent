import random
from gwent.utils.logging import get_logger
import threading

_REAL = None
_lock = threading.RLock()

# Shared SPI bus lock — RFID (CE0) and OLED (CE1) share the SPI bus
# and must not access it concurrently from different threads.
spi_lock = threading.Lock()

def real_mode():
    global _REAL
    with _lock:
        if _REAL is None:
            init()
    return _REAL

def init():
    log = get_logger('hal')
    random.seed()
    global _REAL

    _REAL = True
    log.info({'real_mode': _REAL})
