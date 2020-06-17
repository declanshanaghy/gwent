import logging
import random
import asyncio

_REAL = None
_lock = asyncio.Lock()

async def real_mode():
    async with _lock:
        if _REAL is None:
            init()
    return _REAL

def init():
    log = logging.getLogger('hal')
    random.seed()
    global _REAL

    try:
        import mfrc522
        _REAL = True
    except ImportError:
        _REAL = False

    log.info({'real_mode': _REAL})
