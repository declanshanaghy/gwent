import asyncio
import functools
import logging
import signal

import gwent.log
import gwent.cards
import gwent.cards.all
import gwent.cards.scoiatael
import gwent.hal.rfid
import gwent.hal.tts

class AsyncApp(object):
    _log = logging.getLogger(__name__)

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

    def setup_signal_handlers(self):
        loop = asyncio.get_event_loop()
        # Setup signal handlers for graceful exit
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(self.shutdown(s, loop)))


class CardWriterUtil(AsyncApp):
    _writer = None
    cards_by_faction = None
    cards_by_faction_by_owner = {}
    starters_by_faction = {}

    def __init__(self, cards_by_faction: dict):
        self.cards_by_faction = cards_by_faction
        self._writer = gwent.hal.rfid.Writer()

    def some_card(self) -> gwent.cards.Card:
        # Known biggest card
        name = "Francesca Findabair: The Beautiful"
        faction = gwent.cards.SCOIATAEL
        details = gwent.cards.scoiatael.CARDS_BY_FACTION[faction][name]
        return gwent.cards.Card(details, name=name, faction=faction)

    def validate_cards(self) -> gwent.cards.Card:
        biggest_card = None
        total_cards = 0
        for faction, cards in self.cards_by_faction.items():
            if not faction in self.cards_by_faction_by_owner:
                self.cards_by_faction_by_owner[faction] = {}
            if not faction in self.starters_by_faction:
                self.starters_by_faction[faction] = {}

            total_cards += len(cards.keys())
            for name, card in cards.items():
                card = gwent.cards.Card(card, name=name, faction=faction)

                if card.is_starter:
                    self.starters_by_faction[faction][card.name] = card

                if card.has_owner:
                    if not card.owner in self.cards_by_faction_by_owner[
                        faction]:
                        self.cards_by_faction_by_owner[faction][card.owner] = {}
                    self.cards_by_faction_by_owner[faction][card.owner][
                        card.name] = card

                # if self._log.isEnabledFor(logging.DEBUG):
                #     self._log.debug({
                #         'action': 'card loaded',
                #         'name': card.name,
                #         'faction': card.faction,
                #         'bytes': card.bytes,
                #         'blocks': card.blocks,
                #         'sectors': card.sectors
                #     })

                if biggest_card is None or card.bytes > biggest_card.bytes:
                    biggest_card = card

        for faction, cards in self.starters_by_faction.items():
            self._log.info({
                'action': 'starters',
                'faction': faction,
                'count': len(cards),
            })

        totals_by_owner = {}
        for faction, cards_by_owner in self.cards_by_faction_by_owner.items():
            for owner, cards in cards_by_owner.items():
                if not owner in totals_by_owner:
                    totals_by_owner[owner] = 0
                totals_by_owner[owner] += len(cards)
                self._log.info({
                    'owner': owner,
                    'faction': faction,
                    'count': len(cards),
                })

        for owner, total in totals_by_owner.items():
            self._log.info({
                'owner': owner,
                'total': total,
            })

        self._log.info({
            'action': 'biggest_card',
            'total_cards': total_cards,
            'name': biggest_card.name,
            'bytes': biggest_card.bytes,
            'blocks': biggest_card.blocks,
            'body_sectors': biggest_card.body_sectors
        })

        return biggest_card

    async def _write_card(self, card: gwent.cards.Card):
        loop = asyncio.get_running_loop()
        self._log.info({
            'action': 'Hold a tag near the writer to receive the data',
            'name': card.name,
            'faction': card.faction,
        })

        id = None
        while id is None:
            id = await loop.run_in_executor(
                None, functools.partial(self._writer.write_card,
                                        card=card, block=True))

        if id is not None:
            self._log.info({
                'action': 'card written successfully',
                'id': id,
            })

        tts = gwent.hal.tts.TTS()
        await loop.run_in_executor(
            None, functools.partial(tts.clear_cache, card=card))


    def run(self):
        self.setup_signal_handlers()

        card = gwent.cards.all.random_card()

        loop = asyncio.get_event_loop()
        task = loop.create_task(self._write_card(card))
        loop.run_until_complete(task)


class CardReaderUtil(AsyncApp):
    _reader = None

    def __init__(self):
        self._reader = gwent.hal.rfid.Reader()

    async def _read_card(self) -> gwent.cards.Card:

        loop = asyncio.get_running_loop()
        card = await loop.run_in_executor(
            None, functools.partial(self._reader.read_card, block=True))

        self._log.info({
            'action': 'read card',
            'id': card.id,
            'name': card.name,
            'faction': card.faction,
        })

        tts = gwent.hal.tts.TTS()
        await loop.run_in_executor(
            None, functools.partial(tts.read_card, card=card))

        return card

    def run(self):
        self.setup_signal_handlers()

        loop = asyncio.get_event_loop()
        task = loop.create_task(self._read_card())
        loop.run_until_complete(task)


# entrypoint to write the biggest hardcoded card
def write_card():
    # import pydevd_pycharm
    # pydevd_pycharm.settrace('192.168.1.143', port=31337,
    #                         stdoutToServer=True, stderrToServer=True)

    # gwent.log.setup(level='info')
    gwent.log.setup(level='debug')

    log = logging.getLogger(__name__)
    for faction, cards in gwent.cards.all.CARDS_BY_FACTION.items():
        log.info(f"{faction} has {len(cards.keys())} cards")

    u = CardWriterUtil(gwent.cards.all.CARDS_BY_FACTION)
    u.run()


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
    import pygame.mixer
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2)

    import pygame
    pygame.init()

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'write':
        write_card()
    else:
        read_card()
