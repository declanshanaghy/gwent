import logging
import os
import signal
import time

import gwent.game.board
import gwent.log

class Gwent(object):
    running = True
    log = logging.getLogger(__name__)
    brd = gwent.game.board.New()

    def sig(self, signum, frame):
        self.log.info({
            'message': 'Received signal',
            'signum': signum,
            'frame': frame,
        })
        self.running = False


    def setup(self):
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
    gwent.log.setup()

    g = Gwent()
    g.run()


if __name__ == '__main__':
    run()
