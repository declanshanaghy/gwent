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

    _REAL = True
    log.info({'real_mode': _REAL})
