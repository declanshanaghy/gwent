import asyncio

import asyncio_mqtt

import gwent.messaging.factory
import gwent.messaging.sfx
import gwent.game
import gwent.hal.tts


class SFX(gwent.game.PubSubComponent):
    async def init(self):
        self._tts = gwent.hal.tts.instance()
        await self.subscribe(gwent.game.CH_SFX,
                             gwent.messaging.sfx.KIND,
                             self.process_sfx)

    async def shutdown(self):
        await self.unsubscribe(gwent.messaging.sfx.KIND)

    async def process_sfx(self, sfx: gwent.messaging.sfx.Message):
        self._log.info({
            'action': 'received sfx',
            'body': sfx.body,
        })
        await self._tts.announce(sfx)

