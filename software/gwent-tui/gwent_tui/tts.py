"""Text-to-speech, SFX, and music for TUI.

Uses gwent_shared.audio.AudioMixer (pygame) for channelized playback.
Announcements are queued and played sequentially on the "tts" channel.
SFX plays on the "effect" channel. Music uses pygame.mixer.music.
"""

import logging
import os
import queue
import tempfile
import threading

log = logging.getLogger("gwent_tui.tts")

_provider = None
_provider_name: str | None = None
_provider_error: str | None = None

# Sequential announcement queue
_queue: queue.Queue = queue.Queue()
_worker_thread: threading.Thread | None = None
_running = False

# Cache dir for synthesized audio
_CACHE_DIR = os.path.join(tempfile.gettempdir(), "gwent-tui-tts")

# Completion callbacks
_on_complete_callback = None
_on_music_complete_callback = None

# Volume state (0-100 percent)
_volume = 100       # music
_sfx_volume = 100   # SFX effects
_tts_volume = 100   # TTS announcements

# Current music track path (for dedup)
_music_current_path: str = ""

# Lazy mixer reference
_mixer = None


def _get_mixer():
    """Get or create the shared AudioMixer singleton."""
    global _mixer
    if _mixer is not None:
        return _mixer
    from gwent_shared.audio import get_mixer
    _mixer = get_mixer()
    # Apply initial volume levels
    _mixer.set_music_volume(_volume / 100.0)
    _mixer.set_channel_volume("effect", _sfx_volume / 100.0)
    _mixer.set_channel_volume("tts", _tts_volume / 100.0)
    return _mixer


def init(provider_name: str | None = None):
    """Set the TTS provider name. Call before first speak()."""
    global _provider_name
    _provider_name = provider_name


def _get_provider():
    """Lazy-init the TTS provider."""
    global _provider, _provider_error
    if _provider is not None:
        return _provider
    try:
        from gwent_shared.tts import LOCAL_PROVIDER, get_provider
        name = _provider_name or LOCAL_PROVIDER
        _provider = get_provider(name)
        _provider_error = None
        log.info("TTS provider: %s", name)
    except Exception as e:
        if _provider_name:
            raise SystemExit(f"TTS provider '{_provider_name}' failed: {e}")
        log.warning("TTS provider unavailable: %s", e)
        _provider_error = str(e)
        _provider = False
    return _provider


def set_on_complete(callback):
    """Set callback(content_id) called after each playback finishes."""
    global _on_complete_callback
    _on_complete_callback = callback


# ------------------------------------------------------------------
# TTS Announcements (queued, sequential)
# ------------------------------------------------------------------

def speak(text: str, faction: str | None = None, content_id: str | None = None):
    """Queue text for sequential playback."""
    if not text or _provider_name == "none":
        if _on_complete_callback and content_id:
            _on_complete_callback(content_id)
        return
    _ensure_worker()
    _queue.put((text, faction, content_id))


def clear_pending():
    """Drop any queued (not-yet-playing) announcements. Used so a New Game
    re-roll doesn't stack matchup lines — the latest one wins."""
    drained = 0
    try:
        while True:
            _queue.get_nowait()
            _queue.task_done()
            drained += 1
    except queue.Empty:
        pass
    if drained:
        log.debug("tts.clear_pending dropped %d queued items", drained)


def _ensure_worker():
    """Start the worker thread if not already running."""
    global _worker_thread, _running
    if _running:
        return
    _running = True
    _worker_thread = threading.Thread(target=_worker, daemon=True)
    _worker_thread.start()


def _worker():
    """Process announcements sequentially from the queue."""
    global _running
    while _running:
        try:
            text, faction, content_id = _queue.get(timeout=1.0)
        except queue.Empty:
            continue
        try:
            _play_one(text, faction)
        except Exception as e:
            log.debug("TTS worker error: %s", e)
        finally:
            if _on_complete_callback and content_id:
                _on_complete_callback(content_id)
            _queue.task_done()


def _play_one(text: str, faction: str | None = None):
    """Synthesize and play a single announcement via AudioMixer."""
    provider = _get_provider()
    if not provider:
        return

    mixer = _get_mixer()
    vol = _tts_volume / 100.0

    try:
        if getattr(provider, 'can_speak_direct', False):
            # Direct-speaking providers use their own subprocess
            proc = provider.speak_direct(text, faction)
            if proc:
                proc.wait()
            return

        # Synthesize to file, then play via pygame
        os.makedirs(_CACHE_DIR, exist_ok=True)
        import hashlib
        key = hashlib.md5(f"{faction}:{text}".encode()).hexdigest()

        # Always need WAV for pygame
        wav_path = os.path.join(_CACHE_DIR, f"{key}.wav")

        if not os.path.exists(wav_path):
            if provider.native_wav:
                provider.synthesize(text, faction, wav_path)
            else:
                mp3_path = os.path.join(_CACHE_DIR, f"{key}.mp3")
                if not os.path.exists(mp3_path):
                    provider.synthesize(text, faction, mp3_path)
                import pydub
                sound = pydub.AudioSegment.from_mp3(mp3_path)
                sound.export(wav_path, format="wav")

        mixer.play_sound(wav_path, channel="tts", volume=vol)
        mixer.wait_channel("tts")
    except Exception as e:
        log.debug("TTS error: %s", e)


# ------------------------------------------------------------------
# SFX Effects
# ------------------------------------------------------------------

def play_effect(effect_name: str):
    """Play a sound effect WAV file (non-blocking, fire-and-forget)."""
    from pathlib import Path
    import glob as _glob
    import random as _random

    sfx_dir = Path(__file__).resolve().parent.parent.parent / "data" / "sfx"

    # 1. Subdirectory with random WAV (e.g. "close" -> sfx/close/*.wav)
    subdir = sfx_dir / effect_name
    if subdir.is_dir():
        files = list(subdir.glob("*.wav"))
        if files:
            path = str(_random.choice(files))
        else:
            log.debug("No WAV files in SFX dir: %s", subdir)
            return
    else:
        # 2. Direct file at root
        path = str(sfx_dir / f"{effect_name}.wav")
        if not os.path.exists(path):
            # 3. Search subdirs
            matches = _glob.glob(str(sfx_dir / "*" / f"{effect_name}.wav"))
            if matches:
                path = matches[0]
            else:
                log.debug("SFX file not found for effect: %s", effect_name)
                return

    log.info("Playing SFX effect: %s -> %s", effect_name, os.path.basename(path))
    mixer = _get_mixer()
    mixer.play_sound(path, channel="effect", volume=_sfx_volume / 100.0)


# ------------------------------------------------------------------
# Volume Control
# ------------------------------------------------------------------

def adjust_volume(delta: int) -> int:
    """Adjust music volume by delta percent. Takes effect immediately."""
    return set_volume(_volume + delta)


def adjust_sfx_volume(delta: int) -> int:
    """Adjust SFX effects volume by delta percent."""
    return set_sfx_volume(_sfx_volume + delta)


def adjust_tts_volume(delta: int) -> int:
    """Adjust TTS announcement volume by delta percent."""
    return set_tts_volume(_tts_volume + delta)


def set_volume(value: int) -> int:
    """Set music volume to an absolute percent (0..100). Returns clamped value."""
    global _volume
    _volume = max(0, min(100, int(value)))
    _get_mixer().set_music_volume(_volume / 100.0)
    log.info("Music volume: %d%%", _volume)
    return _volume


def set_sfx_volume(value: int) -> int:
    """Set SFX volume to an absolute percent (0..100). Returns clamped value."""
    global _sfx_volume
    _sfx_volume = max(0, min(100, int(value)))
    _get_mixer().set_channel_volume("effect", _sfx_volume / 100.0)
    log.info("SFX volume: %d%%", _sfx_volume)
    return _sfx_volume


def set_tts_volume(value: int) -> int:
    """Set TTS volume to an absolute percent (0..100). Returns clamped value."""
    global _tts_volume
    _tts_volume = max(0, min(100, int(value)))
    _get_mixer().set_channel_volume("tts", _tts_volume / 100.0)
    log.info("TTS volume: %d%%", _tts_volume)
    return _tts_volume


def get_volume() -> int:
    return _volume


def get_sfx_volume() -> int:
    return _sfx_volume


def get_tts_volume() -> int:
    return _tts_volume


# ------------------------------------------------------------------
# Music
# ------------------------------------------------------------------

def set_on_music_complete(callback):
    """Set callback() called when a music track finishes playing."""
    global _on_music_complete_callback
    _on_music_complete_callback = callback


def play_music(path: str, seek_seconds: float = 0):
    """Play a music file in the background."""
    global _music_current_path
    if _provider_name == "none":
        return

    mixer = _get_mixer()

    # Don't restart if already playing the same track
    if path == _music_current_path and mixer.is_music_playing():
        log.debug("Already playing %s, skipping restart", os.path.basename(path))
        return

    _music_current_path = path
    # Don't pass volume — let the mixer's stored _music_volume persist
    # (set by adjust_volume via set_music_volume)
    mixer.play_music(path)

    # Monitor for completion in a background thread
    _start_music_monitor()


def _start_music_monitor():
    """Start a thread that watches for music completion."""
    def _monitor():
        import time as _time
        mixer = _get_mixer()
        # Wait a moment for playback to actually start
        _time.sleep(1.0)
        while mixer.is_music_playing():
            _time.sleep(0.5)
        # Small delay for crossfade overlap
        _time.sleep(0.5)
        if _on_music_complete_callback:
            log.debug("Music track finished, firing completion")
            _on_music_complete_callback()

    t = threading.Thread(target=_monitor, daemon=True)
    t.start()


def stop_music():
    """Stop background music."""
    global _music_current_path
    mixer = _get_mixer()
    mixer.stop_music()
    _music_current_path = ""


_paused_music_path: str = ""


def pause_music() -> None:
    """Stop music but remember the track so resume_music() can restart it."""
    global _paused_music_path, _music_current_path
    _paused_music_path = _music_current_path or ""
    log.info("pause_music: saving path %r", _paused_music_path)
    stop_music()


def resume_music() -> None:
    """Restart the last paused track (no-op if nothing was paused)."""
    path = _paused_music_path
    log.info("resume_music: path=%r", path)
    if path:
        play_music(path)


def stop():
    """Stop any in-progress speech and clear the queue. Music continues."""
    global _running
    _running = False
    # Clear pending items
    while not _queue.empty():
        try:
            _queue.get_nowait()
            _queue.task_done()
        except queue.Empty:
            break
    # Stop TTS channel
    mixer = _get_mixer()
    if mixer._initialized and "tts" in mixer._channels:
        mixer._channels["tts"].stop()
