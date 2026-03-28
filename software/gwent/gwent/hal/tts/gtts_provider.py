"""gTTS (Google Translate TTS) provider — free, no API key required.

Faction voices are selected by Google Translate top-level domain, which
changes the regional accent.  Per-faction slow flag adds gravitas where
it fits the faction personality:
  Northern Realms → co.uk  (UK English)          normal speed
  Skellige        → co.in  (Indian English)       normal speed
  Scoia'tael      → ie     (Irish English)         normal speed
  Monsters        → com.ng (Nigerian English)      slow — menacing
  Nilfgaardian    → com.au (Australian English)    normal speed
"""

import gtts

from gwent.hal.tts.base import TTSProvider


# (tld, slow)
FACTION_VOICE = {
    "Northern Realms": ("co.uk",  False),
    "Skellige":        ("co.in",  False),
    "Scoia'tael":      ("ie",     False),
    "Monsters":        ("com.au", False),
    "Nilfgaardian":    ("com.au", False),
}

DEFAULT_VOICE = ("com", False)  # US English, normal speed


class GTTSProvider(TTSProvider):
    def synthesize(self, text: str, faction: str | None, dest_mp3: str) -> None:
        tld, slow = (
            FACTION_VOICE.get(faction, DEFAULT_VOICE)
            if faction else DEFAULT_VOICE
        )
        gtts.gTTS(text, lang="en", tld=tld, slow=slow).save(dest_mp3)
