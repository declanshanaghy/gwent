"""Text-to-speech for announcements on macOS (uses native `say` command)."""

import logging
import platform
import subprocess
import threading

log = logging.getLogger("gwent_tui.tts")

_IS_MAC = platform.system() == "Darwin"
_lock = threading.Lock()
_current: subprocess.Popen | None = None


def speak(text: str):
    """Speak text asynchronously. On macOS uses `say`; no-op elsewhere."""
    if not _IS_MAC or not text:
        return
    threading.Thread(target=_speak_sync, args=(text,), daemon=True).start()


def _speak_sync(text: str):
    global _current
    with _lock:
        # Cancel any in-progress speech
        if _current and _current.poll() is None:
            _current.terminate()
            _current.wait(timeout=2)
        try:
            _current = subprocess.Popen(
                ["say", "-r", "180", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _current.wait()
        except FileNotFoundError:
            log.debug("`say` command not found")
        except Exception as e:
            log.debug("TTS error: %s", e)


def stop():
    """Stop any in-progress speech."""
    global _current
    with _lock:
        if _current and _current.poll() is None:
            _current.terminate()
