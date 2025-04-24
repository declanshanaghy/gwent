import gwent.game
import gwent.messaging.factory
import gwent.messaging.sfx
import gwent.hal.sfx


class SFX(gwent.game.PubSubComponent):
    def init(self):
        self._tts = gwent.hal.sfx.instance()
        self.subscribe(gwent.game.CH_SFX,
                      gwent.messaging.sfx.KIND,
                      self.process_sfx)

    def shutdown(self):
        self.unsubscribe(gwent.game.CH_SFX)
        super().shutdown()

    def process_sfx(self, sfx: gwent.messaging.sfx.Message):
        self._log.info({
            'action': 'received sfx',
            'subkind': sfx.subkind,
            'body': sfx.body,
        })

        if sfx.subkind == gwent.messaging.sfx.ANNOUNCEMENT:
            self._tts.announce(sfx)
        elif sfx.subkind == gwent.messaging.sfx.EFFECT:
            self._tts.play_effect(sfx)
        elif sfx.subkind == gwent.messaging.sfx.MUSIC:
            self._tts.play_music(sfx)
        else:
            self._log.error(f'Unhandled subkind: {sfx.subkind}')
