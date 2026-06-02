"""Shared pygame audio mixer for Gwent — used by both server and TUI.

Provides channelized playback: music (streamed), SFX and TTS on named
channels with independent volume control and sound caching.
"""

import logging
import os
import threading
import time

log = logging.getLogger("gwent_shared.audio")

# Sentinel for "mixer failed to init"
_DISABLED = False


class AudioMixer:
    """Pygame-based audio mixer with named channels and independent volume."""

    def __init__(self, frequency=44100, buffer=4096):
        """Initialize pygame.mixer. Safe to call multiple times."""
        self._initialized = False
        self._sound_cache = {}
        self._channels = {}  # name -> pygame.mixer.Channel
        self._channel_volumes = {}  # name -> float (0.0-1.0)
        self._next_channel_id = 0
        self._lock = threading.Lock()
        self._music_volume = 1.0
        # When True, all subsequent play_music() calls are no-ops. Set by the
        # server via disable_music() once a TUI client takes over playback —
        # prevents an in-flight play_music (which sleeps during fadeout) from
        # resuming with a fresh track after the takeover.
        self._music_disabled = False

        try:
            import pygame.mixer
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=frequency, size=-16, channels=2,
                                  buffer=buffer)
            self._initialized = True
            log.info("AudioMixer initialized: %s", pygame.mixer.get_init())
        except Exception as e:
            log.warning("AudioMixer init failed (audio disabled): %s", e)

    # ------------------------------------------------------------------
    # Music (streamed via pygame.mixer.music — one track at a time)
    # ------------------------------------------------------------------

    def play_music(self, path, volume=None, fade_ms=2000, loop=True):
        """Play a music file. Crossfades if something is already playing.

        No-op when disable_music() has been called (TUI took over playback).
        """
        if not self._initialized:
            return
        if self._music_disabled:
            log.info("play_music ignored — mixer's music is disabled: %s",
                     os.path.basename(path))
            return
        if volume is not None:
            self._music_volume = max(0.0, min(1.0, volume))

        import pygame.mixer
        try:
            if not os.path.exists(path):
                log.error("Music file not found: %s", path)
                return
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms)
                time.sleep(fade_ms / 1000.0 + 0.1)

            # Re-check after the blocking fadeout — disable_music() may have
            # been called during the sleep (e.g. TUI registered mid-fadeout).
            if self._music_disabled:
                log.info("play_music aborted mid-fadeout (music disabled): %s",
                         os.path.basename(path))
                return

            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._music_volume)
            loops = -1 if loop else 0
            pygame.mixer.music.play(loops, fade_ms=fade_ms)
            log.info("Music playing: %s (vol=%.0f%%, loop=%s)",
                     os.path.basename(path), self._music_volume * 100, loop)
        except Exception as e:
            log.error("Error playing music: %s", e, exc_info=True)

    def disable_music(self) -> None:
        """Permanently silence future play_music() calls and stop the current
        stream. Used by the server when a TUI client takes over playback."""
        self._music_disabled = True
        log.info("Music disabled on this AudioMixer instance")
        if self._initialized:
            try:
                import pygame.mixer
                pygame.mixer.music.stop()
            except Exception as e:
                log.warning("disable_music: pygame stop failed: %s", e)

    def enable_music(self) -> None:
        """Re-enable play_music() after a prior disable_music()."""
        self._music_disabled = False
        log.info("Music re-enabled on this AudioMixer instance")

    def stop_music(self, fade_ms=2000):
        """Stop music with optional fade-out."""
        if not self._initialized:
            return
        import pygame.mixer
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms)
        except Exception as e:
            log.debug("Error stopping music: %s", e)

    def set_music_volume(self, volume):
        """Set music volume (0.0–1.0). Takes effect immediately."""
        self._music_volume = max(0.0, min(1.0, volume))
        if not self._initialized:
            return
        import pygame.mixer
        try:
            pygame.mixer.music.set_volume(self._music_volume)
            log.debug("Music volume: %.0f%%", self._music_volume * 100)
        except Exception:
            pass

    def is_music_playing(self):
        """Check if music is currently playing."""
        if not self._initialized:
            return False
        import pygame.mixer
        try:
            return pygame.mixer.music.get_busy()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Sound effects (cached pygame.mixer.Sound on named channels)
    # ------------------------------------------------------------------

    def play_sound(self, path, channel="effect", volume=None):
        """Play a sound on a named channel. Returns duration in seconds.

        The sound is cached after first load. Volume defaults to the
        channel's current volume if not specified.
        """
        if not self._initialized:
            return 0.0
        try:
            sound = self._load_sound(path)
            if sound is None:
                return 0.0

            ch = self._get_channel(channel)
            vol = volume if volume is not None else self._channel_volumes.get(channel, 1.0)
            sound.set_volume(vol)
            ch.play(sound)

            duration = sound.get_length()
            log.debug("Playing sound: %s on '%s' (vol=%.0f%%, dur=%.1fs)",
                      os.path.basename(path), channel, vol * 100, duration)
            return duration
        except Exception as e:
            log.error("Error playing sound: %s", e, exc_info=True)
            return 0.0

    def set_channel_volume(self, channel, volume):
        """Set volume for a named channel (0.0–1.0). Affects next play_sound."""
        self._channel_volumes[channel] = max(0.0, min(1.0, volume))
        log.debug("Channel '%s' volume: %.0f%%", channel, volume * 100)

    def is_channel_busy(self, channel):
        """Check if a named channel is currently playing."""
        if not self._initialized or channel not in self._channels:
            return False
        try:
            return self._channels[channel].get_busy()
        except Exception:
            return False

    def wait_channel(self, channel, poll_interval=0.1):
        """Block until a named channel finishes playing."""
        if not self._initialized or channel not in self._channels:
            return
        ch = self._channels[channel]
        while ch.get_busy():
            time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_sound(self, path):
        """Load and cache a pygame.mixer.Sound."""
        if path in self._sound_cache:
            return self._sound_cache[path]
        if not os.path.exists(path):
            log.debug("Sound file not found: %s", path)
            return None
        import pygame.mixer
        try:
            sound = pygame.mixer.Sound(path)
            self._sound_cache[path] = sound
            log.debug("Cached sound: %s", os.path.basename(path))
            return sound
        except Exception as e:
            log.error("Failed to load sound %s: %s", path, e)
            return None

    def _get_channel(self, name):
        """Get or allocate a named pygame channel."""
        if name in self._channels:
            return self._channels[name]
        import pygame.mixer
        with self._lock:
            if name in self._channels:
                return self._channels[name]
            # Ensure enough channels exist
            needed = self._next_channel_id + 1
            if pygame.mixer.get_num_channels() < needed:
                pygame.mixer.set_num_channels(needed + 4)
            ch = pygame.mixer.Channel(self._next_channel_id)
            self._next_channel_id += 1
            self._channels[name] = ch
            self._channel_volumes.setdefault(name, 1.0)
            log.debug("Allocated channel '%s' (id=%d)", name, self._next_channel_id - 1)
            return ch

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop_all(self):
        """Stop all sound and music."""
        if not self._initialized:
            return
        import pygame.mixer
        try:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
        except Exception as e:
            log.debug("Error stopping all: %s", e)

    def cleanup(self):
        """Shut down the mixer."""
        self.stop_all()
        self._sound_cache.clear()
        self._channels.clear()
        if self._initialized:
            import pygame.mixer
            try:
                pygame.mixer.quit()
            except Exception:
                pass
            self._initialized = False


# Module-level singleton — lazy-initialized
_mixer = None
_mixer_lock = threading.Lock()


def get_mixer(**kwargs):
    """Get or create the singleton AudioMixer instance."""
    global _mixer
    if _mixer is not None:
        return _mixer
    with _mixer_lock:
        if _mixer is None:
            _mixer = AudioMixer(**kwargs)
    return _mixer
