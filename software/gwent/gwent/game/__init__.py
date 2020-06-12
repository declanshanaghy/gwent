import logging
import asyncio
from typing import List, Callable

import aioredis

import gwent.messaging.base
import gwent.messaging.factory


SEP = '.'
MAIN_CHANNEL = 'gwent'

CH_CARDS = SEP.join((MAIN_CHANNEL, 'cards'))
CH_CARDS_RAW = SEP.join((CH_CARDS, 'raw'))
CH_CARDS_RAW_READ = SEP.join((CH_CARDS_RAW, 'read'))
CH_CARDS_RAW_WRITE = SEP.join((CH_CARDS_RAW, 'write'))

CH_CARDS_PLAY = SEP.join((CH_CARDS, 'play'))

CH_MFD = SEP.join((MAIN_CHANNEL, 'mfd'))
CH_MFD_PRESENT = SEP.join((CH_MFD, 'present'))
CH_MFD_CHOICE = SEP.join((CH_MFD, 'choice'))

CH_SFX = SEP.join((MAIN_CHANNEL, 'sfx'))


class Component(object):
    _loop = None
    _redis = None

    def __init__(self, loop: asyncio.AbstractEventLoop, redis: aioredis.Redis):
        self._log = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        self._loop = loop
        self._redis = redis

    async def publish(self, channel, message: gwent.messaging.base.Message):
        self._log.info({
            'action': 'publish',
            'kind': message.kind,
            'content_id': message.content_id,
        })
        await self._redis.publish(channel, message.body)

    async def subscribe(self, process:Callable, ch:str or aioredis.Channel,
                        *chs:str or aioredis.Channel, expect:List=None) -> List[aioredis.Channel]:
        channels = await self._redis.subscribe(ch, *chs)
        channel_names = [ch.name.decode() for ch in channels]
        self._log.info({
            'action': 'subscribed',
            'channels': channel_names,
        })

        async def reader(channel):
            async for msg in channel.iter():
                message = gwent.messaging.factory.unmarshall(msg, expect=expect)
                await process(message)

        for ch in channels:
            self._loop.create_task(reader(ch))

        return channels


