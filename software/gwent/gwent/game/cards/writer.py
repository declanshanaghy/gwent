import asyncio
import functools
import logging
import signal

import gwent.log

import gwent.game.cards
import gwent.game.cards.all
import gwent.game.cards.skellige
import gwent.hal.rfid


SKELLIGE = gwent.game.cards.SKELLIGE
SKELLIGE_CARDS = gwent.game.cards.all.CARDS_BY_FACTION[SKELLIGE]


class CardWriterUtil(object):
    _log = logging.getLogger(__name__)
    _writer = None

    def __init__(self):
        self._writer = gwent.hal.rfid.Writer()

    def log_card_info(self) -> gwent.game.cards.Card:
        biggest_card = gwent.game.cards.Card({}, name='fake', faction='fake')
        for name, card in SKELLIGE_CARDS.items():
            card = gwent.game.cards.Card(card, name=name, faction=SKELLIGE)
            self._log.info({
                'action': 'card info',
                'name': card.name,
                'bytes': card.bytes,
                'blocks': card.blocks,
                'sectors': card.sectors
            })
            if card.bytes > biggest_card.bytes:
                biggest_card = card

        self._log.warning({
            'action': 'biggest_card',
            'name': biggest_card.name,
            'bytes': biggest_card.bytes,
            'blocks': biggest_card.blocks
        })

        return biggest_card

    async def _write_card(self, card: gwent.game.cards.Card):
        loop = asyncio.get_running_loop()
        self._log.info({
            'action': 'Hold a tag near the writer to receive the data',
            'name': card.name,
            'faction': card.faction,
        })

        text = None
        id = None
        while id is None:
            id, text = await loop.run_in_executor(
                None, functools.partial(self._writer.write_card, card=card))

        if id is not None:
            self._log.info({
                'action': 'card written successfully',
                'id': id,
                'text': text,
                'len(text)': len(text)
            })

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

    def run(self):
        biggest_card = self.log_card_info()
        loop = asyncio.get_event_loop()

        # Setup signal handlers for graceful exit
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(self.shutdown(s, loop)))

        task = loop.create_task(self._write_card(biggest_card))
        loop.run_until_complete(task)


def write_biggest_card():
    gwent.log.setup(level='debug')

    u = CardWriterUtil()
    u.run()


if __name__ == '__main__':
    write_biggest_card()
