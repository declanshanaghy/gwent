"""No-op TTS provider — skips synthesis and playback.

Announcements still flow through MQTT and fire announcement_complete
so the game state machine advances normally. Use GWENT_TTS_DELAY env
var to add a fake delay per announcement for debugging timing issues.
"""

import os
import time

from gwent_shared.tts.base import TTSProvider


class NoneProvider(TTSProvider):
    native_wav = True

    def __init__(self):
        self._delay = float(os.environ.get("GWENT_TTS_DELAY", "0"))

    def synthesize(self, text, faction, dest):
        if self._delay > 0:
            time.sleep(self._delay)
