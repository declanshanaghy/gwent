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
        # Music control: toggle on/off
        self.subscribe(gwent.game.CH_MUSIC_CTRL,
                      gwent.messaging.music.KIND,
                      self._on_music_ctrl)
        self._music_enabled = True

    def shutdown(self):
        self.unsubscribe(gwent.game.CH_SFX)
        self.unsubscribe(gwent.game.CH_MUSIC)
        self.unsubscribe(gwent.game.CH_MUSIC_COMPLETE)
        self.unsubscribe(gwent.game.CH_MUSIC_CTRL)
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

        if self._is_muted() or not self._music_enabled:
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
        if not self._music_enabled:
            self._log.info("Music disabled, ignoring complete")
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

    def _on_music_ctrl(self, msg: gwent.messaging.music.Message):
        """Handle gwent/music/ctrl — toggle music on/off."""
        action = msg._instance.get("action", "")
        self._log.info(f"Music control: action={action}, source={msg.source}")
        if action == "toggle":
            self._music_enabled = not self._music_enabled
            self._log.info(f"Music {'enabled' if self._music_enabled else 'disabled'}")
            if self._music_enabled:
                self.publish_music()
            else:
                try:
                    import pygame.mixer
                    pygame.mixer.music.stop()
                except Exception:
                    pass
                # Cancel auto-advance timer
                if hasattr(self, '_music_timer') and self._music_timer:
                    self._music_timer.cancel()
                    self._music_timer = None

    def _on_announcement_complete(self, msg):
        complete = gwent.messaging.sfx.Message.with_announcement_complete(
            source="gwent",
            original_content_id=msg.content_id)
        self.publish(gwent.game.CH_SFX_COMPLETE, complete)
