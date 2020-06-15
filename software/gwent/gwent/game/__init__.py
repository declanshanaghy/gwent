import logging
import asyncio
from typing import Any, Callable

import asyncio_mqtt

import gwent.messaging.base
import gwent.messaging.factory
import gwent.messaging.mfd

SEP = '/'
MAIN_CHANNEL = 'gwent'

CH_CTRL = SEP.join((MAIN_CHANNEL, 'ctrl'))
CH_GAMESTAGE = SEP.join((CH_CTRL, 'stage'))

CH_CARDS = SEP.join((MAIN_CHANNEL, 'cards'))
CH_CARDS_RAW = SEP.join((CH_CARDS, 'raw'))
CH_CARDS_RAW_READ = SEP.join((CH_CARDS_RAW, 'read'))
CH_CARDS_RAW_WRITE = SEP.join((CH_CARDS_RAW, 'write'))

CH_CARDS_PLAY = SEP.join((CH_CARDS, 'play'))

CH_MFD = SEP.join((MAIN_CHANNEL, 'mfd'))
CH_MFD_PRESENT = SEP.join((CH_MFD, 'present'))
CH_MFD_CHOICE = SEP.join((CH_MFD, 'choice'))

CH_SFX = SEP.join((MAIN_CHANNEL, 'sfx'))

DEFAULT_ERROR_TIME = 3


class Component(object):
    _loop = None
    _pubsub = None

    def __init__(self, loop: asyncio.AbstractEventLoop,
                 pubsub: asyncio_mqtt.Client):
        self._log = logging.getLogger(
            f'{self.__class__.__module__}.{self.__class__.__name__}')
        self._loop = loop
        self._pubsub = pubsub

    async def publish_error(self, error: str):
        mfd = gwent.messaging.mfd.Message.from_properties(error=error)
        await self.publish(CH_MFD_PRESENT, mfd)

    async def init(self):
        pass

    async def shutdown(self):
        pass

    async def run(self):
        while True:
            await asyncio.sleep(1)

    async def subscribe(self, topic_filter: str, expect_kind: str,
                        callback: Callable[
                            [gwent.messaging.base.Message], Any]):
        async def processor():
            async with self._pubsub.filtered_messages(topic_filter) as messages:
                self._log.debug({
                    'action': 'listening to',
                    'topic_filter': topic_filter,
                    'expect_kind': expect_kind,
                    'messages': messages,
                })
                async for message in messages:
                    decoded = message.payload.decode()
                    self._log.debug({
                        'action': 'received raw message',
                        'topic': message.topic,
                        'message': decoded,
                    })
                    message = gwent.messaging.factory.unmarshall(
                        decoded, expect_kind=expect_kind)
                    await callback(message)

        self._loop.create_task(processor())

        self._log.info({
            'action': 'subscribe',
            'topic_filter': topic_filter,
            'expect_kind': expect_kind,
        })
        await self._pubsub.subscribe(topic_filter)

    async def unsubscribe(self, topic: str):
        self._log.info({
            'action': 'unsubscribe',
            'topic': topic,
        })
        await self._pubsub.unsubscribe(topic)

    async def publish(self, topic, message: gwent.messaging.base.Message):
        self._log.info({
            'action': 'publish',
            'topic': topic,
            'kind': message.kind,
            'content_id': message.content_id,
            'body': message.body,
        })
        await self._pubsub.publish(topic, message.body, qos=1)
