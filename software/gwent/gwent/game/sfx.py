import asyncio
import gwent.messaging.factory
import gwent.messaging.sfx.sfx
import gwent.game
import gwent.hal.tts


class SFX(gwent.game.Component):
    _tts = gwent.hal.tts.instance()

    async def init(self):
        await self.subscribe(gwent.messaging.sfx.sfx.KIND,
                             gwent.game.CH_SFX,
                             self.process_sfx)

    async def shutdown(self):
        await self.unsubscribe(gwent.messaging.sfx.sfx.KIND)

    async def process_sfx(self, sfx: gwent.messaging.sfx.sfx.Message):
        self._log.info({
            'action': 'received sfx',
            'sfx.action': sfx.action,
            'speech': sfx.speech,
        })
        await self._tts.announce(sfx)

