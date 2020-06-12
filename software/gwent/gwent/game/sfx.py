import gwent.messaging.factory
import gwent.messaging.sfx.sfx
import gwent.game
import gwent.hal.tts


class SFX(gwent.game.Component):
    _tts = gwent.hal.tts.instance()

    async def run(self):
        await self.subscribe(self.process,
                             gwent.game.CH_SFX,
                             expect=[gwent.messaging.sfx.sfx.KIND,])

    async def process(self, sfx: gwent.messaging.sfx.sfx.Message):
        self._log.info({
            'action': 'received sfx',
            'sfx.action': sfx.action,
            'speech': sfx.speech,
        })
        await self._tts.announce(sfx)

