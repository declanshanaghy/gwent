import gwent.game
import gwent.messaging.factory
import gwent.messaging.sfx
import gwent.messaging.music
import gwent.hal.sfx
from gwent.hal.tts import DEFAULT_PROVIDER


class SFX(gwent.game.PubSubComponent):
    def __init__(self, pubsub, tts_provider: str = DEFAULT_PROVIDER):
        super().__init__(pubsub)
        self._tts_provider_name = tts_provider

    def init(self):
        super().init()
        self._tts = gwent.hal.sfx.instance(tts_provider=self._tts_provider_name)
        # SFX: announcements + effects
        self.subscribe(gwent.game.CH_SFX,
                      gwent.messaging.sfx.KIND,
                      self.process_sfx)
        # Music: play tracks
        self.subscribe(gwent.game.CH_MUSIC,
                      gwent.messaging.music.KIND,
                      self.process_music)
        # Music completion: queue next track
        self.subscribe(gwent.game.CH_MUSIC_COMPLETE,
                      gwent.messaging.music.KIND,
                      self._on_music_complete)

    def shutdown(self):
        self.unsubscribe(gwent.game.CH_SFX)
        self.unsubscribe(gwent.game.CH_MUSIC)
        self.unsubscribe(gwent.game.CH_MUSIC_COMPLETE)
        super().shutdown()

    def _is_muted(self):
        from gwent_shared.tts.none_provider import NoneProvider
        return isinstance(self._tts._tts_provider, NoneProvider)

    def process_sfx(self, sfx: gwent.messaging.sfx.Message):
        """Handle gwent/sfx — announcements and effects."""
        self._log.info({
            'action': 'received sfx',
            'subkind': sfx.subkind,
        })

        muted = self._is_muted()

        try:
            if sfx.subkind == gwent.messaging.sfx.ANNOUNCEMENT:
                if muted:
                    self._on_announcement_complete(sfx)
                else:
                    self._log.info(f"Playing announcement: {sfx.announcement}")
                    self._tts.announce(sfx, on_complete=self._on_announcement_complete)
            elif sfx.subkind == gwent.messaging.sfx.EFFECT:
                if not muted:
                    self._log.info(f"Playing effect: {sfx.effect}")
                    self._tts.play_effect(sfx)
            elif sfx.subkind == gwent.messaging.sfx.ANNOUNCEMENT_COMPLETE:
                pass  # handled by game-loop sync, not here
            else:
                self._log.debug(f'Unhandled sfx subkind: {sfx.subkind}')
        except Exception as e:
            self._log.error(f"Error processing sfx: {e}", exc_info=True)

    def process_music(self, msg: gwent.messaging.music.Message):
        """Handle gwent/music — play a track."""
        self._log.info(f"Music: {msg.music} (next: {msg.next_music})")

        if self._is_muted():
            return

        try:
            self._tts.play_music(msg)
        except Exception as e:
            self._log.error(f"Error playing music: {e}", exc_info=True)

    _last_music_advance = 0.0

    def _on_music_complete(self, msg: gwent.messaging.music.Message):
        """Handle gwent/music/complete — queue next track.

        Debounced: ignores duplicate completions within 5 seconds.
        Sources: gwent-tui (client finished), gwent-timer (server scheduled).
        """
        import time as _time
        self._log.info(f"Music complete received: source={msg.source}, music={msg.music}")
        if msg.subkind != "complete":
            return
        now = _time.time()
        elapsed = now - self._last_music_advance
        if elapsed < 5.0:
            self._log.info(f"Music complete debounced ({elapsed:.1f}s since last, source={msg.source})")
            return
        self._last_music_advance = now
        # Advance to the next_music that was promised in the last play message
        from gwent.game import PubSubComponent
        promised = PubSubComponent._music_next_track
        self._log.info(f"Music advancing to: {promised or 'playlist next'} (triggered by {msg.source})")
        self.publish_music(music=promised)

    def _on_announcement_complete(self, msg):
        complete = gwent.messaging.sfx.Message.with_announcement_complete(
            source="gwent",
            original_content_id=msg.content_id)
        self.publish(gwent.game.CH_SFX_COMPLETE, complete)
