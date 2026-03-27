import gwent.game
import gwent.messaging.factory
import gwent.messaging.sfx
import gwent.hal.sfx
from gwent.hal.tts import DEFAULT_PROVIDER


class SFX(gwent.game.PubSubComponent):
    def __init__(self, pubsub, tts_provider: str = DEFAULT_PROVIDER):
        super().__init__(pubsub)
        self._tts_provider_name = tts_provider

    def init(self):
        super().init()
        self._tts = gwent.hal.sfx.instance(tts_provider=self._tts_provider_name)
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

        try:
            if sfx.subkind == gwent.messaging.sfx.ANNOUNCEMENT:
                self._log.info(f"Playing announcement: {sfx.announcement}")
                self._tts.announce(sfx, on_complete=self._on_announcement_complete)
            elif sfx.subkind == gwent.messaging.sfx.EFFECT:
                self._log.info(f"Playing effect: {sfx.effect}")
                self._tts.play_effect(sfx)
            elif sfx.subkind == gwent.messaging.sfx.MUSIC:
                music_info = f"music: {sfx.music}" if hasattr(sfx, 'music') else "random music"
                self._log.info(f"Playing {music_info}")
                self._tts.play_music(sfx)
            else:
                self._log.debug(f'Unhandled subkind: {sfx.subkind}')
        except Exception as e:
            self._log.error(f"Error processing audio: {e}", exc_info=True)

    def _on_announcement_complete(self, msg):
        complete = gwent.messaging.sfx.Message.with_announcement_complete(
            msg.announcement)
        self.publish(gwent.game.CH_SFX_COMPLETE, complete)
