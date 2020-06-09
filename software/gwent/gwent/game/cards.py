import asyncio
import functools
import json
import logging

import aioredis

import gwent.cards
import gwent.hal.rfid
import gwent.hal.tts


CHANNEL_CARDS = 'gwent.cards'


class GwentComponent(object):
    _log = logging.getLogger(__name__)
    _loop = None
    _redis = None

    def __init__(self, loop, redis: aioredis.Redis):
        self._loop = loop
        self._redis = redis


class Reader(GwentComponent):
    _reader = gwent.hal.rfid.Reader()

    async def run(self):
        while True:
            card = await self._loop.run_in_executor(
                None, functools.partial(self._reader.read_card, block=False))

            if card is not None:
                self._log.info({
                    'action': 'publish card',
                    'id': card.id,
                    'name': card.name,
                    'faction': card.faction,
                })
                await self._redis.publish(CHANNEL_CARDS, card.body)
            else:
                self._log.info({
                    'action': 'no card received',
                })
                await asyncio.sleep(0.1)


class Announcer(GwentComponent):
    _tts = gwent.hal.tts.TTS()

    async def run(self):
        channel, = await self._redis.subscribe(CHANNEL_CARDS)
        self._log.info({
            'action': 'subscribed',
            'channel': channel.name,
        })

        async for message in channel.iter():
            details = json.loads(message)
            card = gwent.cards.Card(details)
            self._log.info({
                'action': 'received card',
                'id': card.id,
                'name': card.name,
                'faction': card.faction,
            })
            # await self._loop.run_in_executor(
            #     None, functools.partial(self._tts.read_card, card=card))
            await self._tts.read_card(card)

