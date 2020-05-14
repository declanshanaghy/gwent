import json
import random
import time
import logging

class Reader(object):
    _log = logging.getLogger(__name__)
    _reader = None

    def __init__(self):
        try:
            import mfrc522
            import RPi.GPIO as GPIO
            self._reader = mfrc522.SimpleMFRC522()
        except Exception as ex:
            self._log.error({
                'action': 'error setting up reader',
                'ex': ex,
            })
            random.seed()

    def read(self):
        if self._reader is not None:
            return self.read_real()
        else:
            return self.read_fake()

    def read_fake(self):
        t = float(random.randint(1, 100)) / 10
        self._log.info(f'Will produce a fake tag in {t} seconds')
        time.sleep(t)
        details = {'name': 'Somebodys name'}
        return random.randint(10000000, 999999999), json.dumps(details)

    def read_real(self):
        self._log.debug("Hold a tag near the reader")
        id, text = self._reader.read_no_block()
        if id:
            text = text.strip()
            return id, text
        else:
            return None, None
