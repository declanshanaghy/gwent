import asyncio
import functools
import logging
import signal
import sys

import gwent.log
import gwent.messaging.base
import gwent.cards.all
import gwent.messaging.card
import gwent.cards.util
import gwent.cards.scoiatael
import gwent.hal.rfid
import gwent.hal.sfx


class AsyncApp(object):
    def __init__(self):
        self._log = logging.getLogger(
            f'{self.__class__.__module__}.{self.__class__.__name__}')

    async def shutdown(self, signal, loop):
        """Cleanup tasks tied to the service's shutdown."""
        logging.info(f'Received exit signal {signal.name}...')
        logging.info('Nacking outstanding tasks')
        tasks = [t for t in asyncio.all_tasks() if t is not
                 asyncio.current_task()]

        logging.info(f'Cancelling {len(tasks)} outstanding tasks')
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)

        loop.stop()

    def setup_signal_handlers(self, loop):
        # Setup signal handlers for graceful exit
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(self.shutdown(s, loop)))


class CardWriterUtil(AsyncApp):
    async def _write_card(self, card: gwent.messaging.card.Message):
        loop = asyncio.get_running_loop()
        self._log.info({
            'action': 'Hold a tag near the writer to receive the data',
            'name': card.name,
            'faction': card.faction,
        })

        _writer = await loop.run_in_executor(None, gwent.hal.rfid.instance)

        id = None
        while id is None:
            id = await loop.run_in_executor(
                None, functools.partial(_writer.write_card,
                                        card=card))

        if id is not None:
            self._log.info({
                'action': 'card written successfully',
                'id': id,
            })

    def run(self, card: gwent.messaging.card.Message):
        loop = asyncio.get_event_loop()
        self.setup_signal_handlers(loop)

        self._log.info({
            'action': 'run',
            'full_name': card.full_name,
            'faction': card.faction,
        })
        task = loop.create_task(self._write_card(card))
        loop.run_until_complete(task)


class CardReaderUtil(AsyncApp):
    async def _read_card(self) -> gwent.messaging.card.Message:
        loop = asyncio.get_running_loop()

        reader = await loop.run_in_executor(None, gwent.hal.rfid.instance)

        card = await loop.run_in_executor(None, reader.read_card)
        if card is not None:
            self._log.info({
                'action': 'got card',
                'rfid': card.rfid,
                'name': card.name,
                'faction': card.faction,
            })

            sfx = await gwent.hal.sfx.instance(loop)

            length = await sfx.announce(card)
            if length:
                await asyncio.sleep(length)

        return card

    def run(self):
        loop = asyncio.get_event_loop()
        self.setup_signal_handlers(loop)

        task = loop.create_task(self._read_card())
        loop.run_until_complete(task)


# entrypoint to write a card
def write_card(card: gwent.messaging.card.Message):
    # import pydevd_pycharm
    # pydevd_pycharm.settrace('192.168.1.143', port=31337,
    #                         stdoutToServer=True, stderrToServer=True)

    # gwent.log.setup(level='info')
    gwent.log.setup(level='debug')

    u = CardWriterUtil()
    u.run(card)


# entrypoint to read a card
def read_card():
    # import pydevd_pycharm
    # pydevd_pycharm.settrace('192.168.1.143', port=31337,
    #                         stdoutToServer=True, stderrToServer=True)

    # gwent.log.setup(level='info')
    gwent.log.setup(level='debug')

    u = CardReaderUtil()
    u.run()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'write':
        card = None
        if len(sys.argv) == 3:
            card = sys.argv[3]
            card = gwent.cards.util.read_card(card)
        else:
            card = gwent.cards.util.random_card()
        write_card(card)
    else:
        read_card()
