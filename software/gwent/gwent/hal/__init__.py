import random
from gwent.utils.logging import get_logger
import threading

_REAL = None
_lock = threading.RLock()

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
