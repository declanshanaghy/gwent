"""Splash screen — shows the Gwent logo image on startup."""

import os

from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Static
from textual_image.widget import TGPImage

# Logo image path — relative to this file
_LOGO_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "..", "design", "logo", "gwent_logo_v9.png"))

_TITLE = """\
[bold bright_yellow]C A R D S   &   C I R C U I T S[/]
[dim]♠  RFID-Powered Gwent Companion  ♠[/]
[dim]Scan your cards. Play your hand. Claim victory.[/]\
"""


class SplashScreen(ModalScreen):
    CSS = """
    SplashScreen {
        align: center middle;
        background: $background 90%;
    }
    #splash-box {
        width: 90%;
        height: 90%;
        max-width: 80;
        max-height: 34;
        align: center middle;
        background: black;
        border: round yellow;
    }
    #splash-image {
        width: 100%;
        height: 1fr;
    }
    #splash-title {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-align: center;
        padding: 1 0;
    }
    """

    def __init__(self, duration: float = 3.0):
        super().__init__()
        self._duration = duration

    def compose(self):
        with Vertical(id="splash-box"):
            yield TGPImage(_LOGO_PATH, id="splash-image")
            yield Static(_TITLE, id="splash-title")

    def on_mount(self):
        self.set_timer(self._duration, self._do_dismiss)

    def _do_dismiss(self):
        """Dismiss via call_later to avoid ScreenError in message handlers."""
        self.app.call_later(self.dismiss)

    def on_key(self, event):
        """Any key dismisses immediately."""
        self._do_dismiss()
