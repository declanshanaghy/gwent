import logging


class GwentBoard(object):
    log = logging.getLogger(__name__)

    def setup(self):
        self.log.info("setup...")

    def loop(self):
        self.log.info("loop...")


def New():
    return GwentBoard()
