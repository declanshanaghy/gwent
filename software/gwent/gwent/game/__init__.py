import logging
import asyncio
from typing import Any, Callable

import aioredis

import gwent.messaging.base
import gwent.messaging.factory
import gwent.messaging.mfd.mfd


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
            'body': message.body,
        })
        await self._redis.publish(channel, message.body)

    async def publish_error(self, error: str):
        mfd = gwent.messaging.mfd.mfd.Message.from_properties(error=error)
        await self.publish(CH_MFD_PRESENT, mfd)

    async def unsubscribe(self, channel:str):
        self._log.info({
            'action': 'unsubscribe',
            'channel': channel,
        })
        await self._redis.unsubscribe(channel)

    async def subscribe(self, ch:str, expect_kind:str,
                        callback:Callable[[gwent.messaging.base.Message],Any]):
        channel, = await self._redis.subscribe(ch)
        self._log.info({
            'action': 'subscribed',
            'channel': channel.name.decode(),
        })

        async def reader(channel):
            async for msg in channel.iter():
                self._log.info({
                    'action': 'reader received',
                    'msg': msg,
                })
                message = gwent.messaging.factory.unmarshall(
                    msg, expect_kind=expect_kind)
                await callback(message)

        self._loop.create_task(reader(channel))

    async def init(self):
        pass

    async def shutdown(self):
        pass

    async def run(self):
        while True:
            await asyncio.sleep(1)

