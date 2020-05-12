import logging
import os
import signal
import time

import log.util

import gwent.board

class Gwent(object):
    running = True
    log = logging.getLogger(__name__)
    brd = gwent.board.New()

    def sig(self, signum, frame):
        self.log.info({
            'message': 'Received signal',
            'signum': signum,
            'frame': frame,
        })
        self.running = False


    def setup(self):
        log.util.setup()

        signal.signal(signal.SIGTERM, self.sig)
        signal.signal(signal.SIGABRT, self.sig)
        signal.signal(signal.SIGINT, self.sig)

    def run(self):
        self.log.info('PID is: %s', os.getpid())

        self.setup()
        self.brd.setup()

        while self.running:
            self.loop()
            self.brd.loop()
            time.sleep(1)

        self.log.info('exiting...')

    def loop(self):
        self.log.info('loop...')


def run():
    gwent = Gwent()
    gwent.run()


if __name__ == '__main__':
    run()
