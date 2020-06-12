import asyncio

import logging
import random


REAL = True
try:
    import mfrc522
except Exception as ex:
    REAL = False


random.seed()


class Component(object):
    _loop = None

    def __init__(self, loop: asyncio.AbstractEventLoop=None):
        self._log = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        self._loop = loop
