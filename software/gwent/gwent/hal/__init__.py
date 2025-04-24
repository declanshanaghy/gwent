import logging
import random
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
    log = logging.getLogger('hal')
    random.seed()
    global _REAL

    _REAL = True
    log.info({'real_mode': _REAL})
