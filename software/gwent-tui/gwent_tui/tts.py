"""Text-to-speech for TUI announcements.

Uses the shared gwent_shared TTS provider system.
On macOS uses the `say` provider, on Linux uses `piper`.
Falls back to no-op if provider is unavailable.
"""

import logging
import os
import subprocess
import tempfile
import threading

log = logging.getLogger("gwent_tui.tts")

_lock = threading.Lock()
_provider = None
_provider_name: str | None = None  # set via init() from CLI --tts flag
_player_proc: subprocess.Popen | None = None

# Cache dir for synthesized audio
_CACHE_DIR = os.path.join(tempfile.gettempdir(), "gwent-tui-tts")


def init(provider_name: str | None = None):
    """Set the TTS provider name. Call before first speak()."""
    global _provider_name
    _provider_name = provider_name


def _get_provider():
    """Lazy-init the TTS provider."""
    global _provider
    if _provider is not None:
        return _provider
    try:
        from gwent_shared.tts import LOCAL_PROVIDER, get_provider
        name = _provider_name or LOCAL_PROVIDER
        _provider = get_provider(name)
        log.info("TTS provider: %s", name)
    except Exception as e:
        log.warning("TTS provider unavailable: %s", e)
        _provider = False  # sentinel: tried and failed
    return _provider


def speak(text: str, faction: str | None = None):
    """Speak text asynchronously using the local platform TTS provider."""
    if not text:
        return
    threading.Thread(
        target=_speak_sync, args=(text, faction), daemon=True
    ).start()


def _speak_sync(text: str, faction: str | None = None):
    global _player_proc
    provider = _get_provider()
    if not provider:
        return

    with _lock:
        # Stop any in-progress playback
        if _player_proc and _player_proc.poll() is None:
            _player_proc.terminate()
            try:
                _player_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                _player_proc.kill()

        try:
            # Fast path: provider can speak directly (e.g. macOS say)
            if getattr(provider, 'can_speak_direct', False):
                _player_proc = provider.speak_direct(text, faction)
                _player_proc.wait()
                return

            # File-based path: synthesize then play
            os.makedirs(_CACHE_DIR, exist_ok=True)
            import hashlib
            key = hashlib.md5(f"{faction}:{text}".encode()).hexdigest()
            ext = ".wav" if provider.native_wav else ".mp3"
            cached = os.path.join(_CACHE_DIR, f"{key}{ext}")

            if not os.path.exists(cached):
                provider.synthesize(text, faction, cached)

            _player_proc = _play_audio(cached)
            if _player_proc:
                _player_proc.wait()

        except Exception as e:
            log.debug("TTS error: %s", e)


def _play_audio(path: str) -> subprocess.Popen | None:
    """Play an audio file, returning the subprocess."""
    import platform
    try:
        if platform.system() == "Darwin":
            return subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            if path.endswith(".wav"):
                return subprocess.Popen(
                    ["aplay", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                return subprocess.Popen(
                    ["mpg123", "-q", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError as e:
        log.debug("Audio player not found: %s", e)
        return None


def stop():
    """Stop any in-progress speech."""
    global _player_proc
    with _lock:
        if _player_proc and _player_proc.poll() is None:
            _player_proc.terminate()
