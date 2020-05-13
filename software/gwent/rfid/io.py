fake = False

import time
import logging
try:
    import mfrc522
    import RPi.GPIO as GPIO
except:
    fake = True

class RFIDio(object):
    _log = logging.getLogger(__name__)

    def read(self):
        if fake:
            return self.read_fake()
        else:
            return self.read_real()

    def read_fake(self):
        self._log.info("Will produce a fake tag")
        time.sleep(1.0)
        return "23435", "fake text"

    def read_real(self):
        self._log.info("Hold a tag near the reader")
        reader = mfrc522.SimpleMFRC522()
        id, text = reader.read()
        self._log.info(print("ID: %s\nText: %s" % (id, text)))
        return id, text
