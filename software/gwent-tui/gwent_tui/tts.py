"""Text-to-speech for TUI announcements.

Uses the shared gwent_shared TTS provider system.
Announcements are queued and played sequentially.
"""

import logging
import os
import queue
import subprocess
import tempfile
import threading

log = logging.getLogger("gwent_tui.tts")

_provider = None
_provider_name: str | None = None
_provider_error: str | None = None
_player_proc: subprocess.Popen | None = None
_play_lock = threading.Lock()

# Sequential announcement queue
_queue: queue.Queue = queue.Queue()
_worker_thread: threading.Thread | None = None
_running = False

# Cache dir for synthesized audio
_CACHE_DIR = os.path.join(tempfile.gettempdir(), "gwent-tui-tts")

# Completion callback
_on_complete_callback = None


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


def speak(text: str, faction: str | None = None, content_id: str | None = None):
    """Queue text for sequential playback."""
    if not text or _provider_name == "none":
        if _on_complete_callback and content_id:
            _on_complete_callback(content_id)
        return
    _ensure_worker()
    _queue.put((text, faction, content_id))


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
    """Synthesize and play a single announcement."""
    global _player_proc
    provider = _get_provider()
    if not provider:
        return

    with _play_lock:
        try:
            if getattr(provider, 'can_speak_direct', False):
                _player_proc = provider.speak_direct(text, faction)
            else:
                os.makedirs(_CACHE_DIR, exist_ok=True)
                import hashlib
                key = hashlib.md5(f"{faction}:{text}".encode()).hexdigest()
                ext = ".wav" if provider.native_wav else ".mp3"
                cached = os.path.join(_CACHE_DIR, f"{key}{ext}")

                if not os.path.exists(cached):
                    provider.synthesize(text, faction, cached)

                _player_proc = _play_audio(cached)
        except Exception as e:
            log.debug("TTS error: %s", e)
            return

    # Wait outside lock so stop() can terminate
    if _player_proc:
        _player_proc.wait()


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


_music_proc: subprocess.Popen | None = None
_music_current_path: str = ""
_on_music_complete_callback = None


def set_on_music_complete(callback):
    """Set callback() called when a music track finishes playing."""
    global _on_music_complete_callback
    _on_music_complete_callback = callback


def play_music(path: str):
    """Play a music file in the background. Fires on_music_complete when done."""
    global _music_proc, _music_current_path
    if _provider_name == "none":
        return
    # Don't restart if already playing the same track
    if path == _music_current_path and _music_proc and _music_proc.poll() is None:
        log.debug("Already playing %s, skipping restart", os.path.basename(path))
        return
    stop_music()
    _music_current_path = path
    import platform
    try:
        if platform.system() == "Darwin":
            _music_proc = subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            _music_proc = subprocess.Popen(
                ["mpg123", "-q", path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log.info("Music playing: %s (pid=%s)", os.path.basename(path), _music_proc.pid)
        # Monitor for completion in background thread
        t = threading.Thread(target=_music_monitor, args=(_music_proc,), daemon=True)
        t.start()
    except FileNotFoundError as e:
        log.debug("Music player not found: %s", e)


def _music_monitor(proc):
    """Wait for music to finish, then fire completion callback."""
    proc.wait()
    if _on_music_complete_callback:
        log.debug("Music track finished, firing completion")
        _on_music_complete_callback()


def stop_music():
    """Stop background music."""
    global _music_proc, _music_current_path
    if _music_proc and _music_proc.poll() is None:
        _music_proc.terminate()
    _music_proc = None
    _music_current_path = ""


def stop():
    """Stop any in-progress speech and clear the queue. Music continues."""
    global _player_proc, _running
    _running = False
    # Clear pending items
    while not _queue.empty():
        try:
            _queue.get_nowait()
            _queue.task_done()
        except queue.Empty:
            break
    # Kill current playback
    with _play_lock:
        if _player_proc and _player_proc.poll() is None:
            _player_proc.terminate()
