import logging
import asyncio
import time
from typing import Any, Callable

import asyncio_mqtt

import gwent.messaging.base
import gwent.messaging.factory
import gwent.messaging.mfd
import gwent.messaging.sfx

CH_SEP = '/'
MAIN_CHANNEL = 'gwent'

CH_CTRL = CH_SEP.join((MAIN_CHANNEL, 'ctrl'))

CH_CARDS = CH_SEP.join((MAIN_CHANNEL, 'cards'))
CH_CARDS_RAW = CH_SEP.join((CH_CARDS, 'raw'))
CH_CARDS_RAW_READ = CH_SEP.join((CH_CARDS_RAW, 'read'))
CH_CARDS_RAW_WRITE = CH_SEP.join((CH_CARDS_RAW, 'write'))

CH_CARDS_PLAY = CH_SEP.join((CH_CARDS, 'play'))

CH_MFD = CH_SEP.join((MAIN_CHANNEL, 'mfd'))
CH_MFD_PRESENT = CH_SEP.join((CH_MFD, 'present'))
CH_MFD_CHOOSE = CH_SEP.join((CH_MFD, 'choose'))

CH_SFX = CH_SEP.join((MAIN_CHANNEL, 'sfx'))

DEFAULT_YIELD_TIME = 0.01
DEFAULT_ERROR_TIME = 3.0
LOG_FREQ_SECS = 5


def make_channel(base, *topics):
    return CH_SEP.join((base, *topics))


class BaseComponent(object):
    _last_log = time.time() - LOG_FREQ_SECS - 1
    _log = None

    def __init__(self, log_verbose: bool = False):
        self._log = logging.getLogger(
            f'{self.__class__.__module__}.{self.__class__.__name__}')
        if log_verbose:
            self._log.setLevel(logging.DEBUG)
        else:
            self._log.setLevel(logging.INFO)

    def should_log(self) -> bool:
        r = time.time() > self._last_log + LOG_FREQ_SECS
        if r:
            self._last_log = time.time()
        return r

    def log_time(self, action, start):
        end = time.time()
        self._log.info({
            'action': action,
            'start': f'{start:.5f}',
            'end': f'{end:.5f}',
            'duration': f'{end - start:.5f}',
        })


class GameComponent(BaseComponent):
    _loop = None

    def __init__(self, loop: asyncio.AbstractEventLoop,
                 log_verbose: bool = False):
        super().__init__(log_verbose=log_verbose)
        self._loop = loop


class PubSubComponent(GameComponent):
    _pubsub = None

    def __init__(self, loop: asyncio.AbstractEventLoop,
                 pubsub: asyncio_mqtt.Client, log_verbose: bool = False):
        super().__init__(loop, log_verbose=log_verbose)
        self._pubsub = pubsub

    async def init(self):
        pass

    async def shutdown(self):
        pass

    async def run(self):
        while True:
            await asyncio.sleep(DEFAULT_YIELD_TIME)

    async def subscribe(self, topic_filter: str, expect_kind: str,
                        callback: Callable[
                            [gwent.messaging.base.Message], Any]):
        async def processor():
            async with self._pubsub.filtered_messages(topic_filter) as messages:
                self._log.debug({
                    'action': 'listening to',
                    'topic_filter': topic_filter,
                    'expect_kind': expect_kind,
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

    async def publish_effect(self, effect: str):
        e = gwent.messaging.sfx.Message.with_effect(effect)
        await self.publish(CH_SFX, e)

    async def publish_music(self, music: str = None):
        e = gwent.messaging.sfx.Message.with_music(music=music)
        await self.publish(CH_SFX, e)

    async def publish_error(self, error: str):
        e = gwent.messaging.mfd.Message.with_error(error=error)
        await self.publish(CH_MFD_PRESENT, e)

        e = gwent.messaging.sfx.Message.with_announcement(e.error)
        await self.publish(CH_SFX, e)

    async def publish_prompt(self, prompt: str, ok=True,
                             cancel=True, clear_choices=True):
        p = gwent.messaging.mfd.Message.with_prompt(
            prompt=prompt, ok=ok, cancel=cancel, clear_choices=clear_choices)
        await self.publish(CH_MFD_PRESENT, p)

        p = gwent.messaging.sfx.Message.with_announcement(p.prompt)
        await self.publish(CH_SFX, p)
