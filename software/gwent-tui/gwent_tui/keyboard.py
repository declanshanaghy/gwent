"""Non-blocking keyboard input reader for the TUI.

Reads raw terminal input in a daemon thread and dispatches
keystrokes to a callback.
"""

import logging
import sys
import termios
import threading
import tty

log = logging.getLogger("gwent_tui.keyboard")

# Key constants
KEY_CTRL_S = "\x13"
KEY_ENTER = "\r"
KEY_NEWLINE = "\n"
KEY_ESCAPE = "\x1b"
KEY_TAB = "\t"
KEY_BACKSPACE = "\x7f"
KEY_BACKSPACE2 = "\x08"
KEY_ARROW_UP = "UP"
KEY_ARROW_DOWN = "DOWN"


class KeyboardReader:
    """Reads raw keypresses in a background thread."""

    def __init__(self, callback):
        """
        Args:
            callback: Called with each key character (or escape sequence).
        """
        self._callback = callback
        self._running = False
        self._thread = None
        self._old_settings = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, name="keyboard", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        fd = sys.stdin.fileno()
        try:
            self._old_settings = termios.tcgetattr(fd)
            # cbreak mode: read keys one at a time but preserve output processing
            # (unlike setraw which breaks Rich's terminal output)
            tty.setcbreak(fd)
            # Disable XON/XOFF flow control so Ctrl+S reaches us
            # instead of being swallowed by the terminal as XOFF
            new_settings = termios.tcgetattr(fd)
            new_settings[0] &= ~termios.IXON  # iflag: disable XOFF on Ctrl+S
            termios.tcsetattr(fd, termios.TCSANOW, new_settings)
            log.debug("Keyboard reader started (cbreak mode, IXON disabled)")

            while self._running:
                ch = sys.stdin.read(1)
                if not ch:
                    break
                # Decode escape sequences for arrow keys
                if ch == "\x1b":
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        if ch3 == "A":
                            self._callback(KEY_ARROW_UP)
                            continue
                        elif ch3 == "B":
                            self._callback(KEY_ARROW_DOWN)
                            continue
                    # Not an arrow — pass Esc through
                    self._callback(ch)
                    continue
                self._callback(ch)
        except Exception as e:
            log.error("Keyboard reader error: %s", e)
        finally:
            if self._old_settings:
                termios.tcsetattr(fd, termios.TCSADRAIN, self._old_settings)
            log.debug("Keyboard reader stopped")
