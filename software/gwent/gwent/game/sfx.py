import gwent.game
import gwent.messaging.factory
import gwent.messaging.sfx
import gwent.hal.sfx


class SFX(gwent.game.PubSubComponent):
    async def init(self):
        self._tts = await gwent.hal.sfx.instance(self._loop)
        await self.subscribe(gwent.game.CH_SFX,
                             gwent.messaging.sfx.KIND,
                             self.process_sfx)

    async def shutdown(self):
        await self.unsubscribe(gwent.messaging.sfx.KIND)

    async def process_sfx(self, sfx: gwent.messaging.sfx.Message):
        self._log.info({
            'action': 'received sfx',
            'subkind': sfx.subkind,
            'body': sfx.body,
        })

        if sfx.subkind == gwent.messaging.sfx.ANNOUNCEMENT:
            await self._tts.announce(sfx)
        elif sfx.subkind == gwent.messaging.sfx.EFFECT:
            await self._tts.play_effect(sfx)
        else:
            self._log.error(f'Unhandled subkind: {sfx.subkind}')

