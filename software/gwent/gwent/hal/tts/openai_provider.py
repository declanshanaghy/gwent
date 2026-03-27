"""OpenAI TTS provider.

Requires OPENAI_API_KEY environment variable.

Faction voices use OpenAI's built-in voice names with per-faction speed
tuning to reinforce personality:
  Northern Realms → echo   (clear, thoughtful — knightly)     speed 1.0
  Skellige        → onyx   (deep, powerful — warrior)          speed 0.9
  Scoia'tael      → nova   (warm, lighter — elven)             speed 1.1
  Monsters        → fable  (narrative, dramatic — ominous)     speed 0.85
  Nilfgaardian    → alloy  (neutral, authoritative — imperial) speed 0.95
  default         → echo                                       speed 1.0
"""

import os

from gwent.hal.tts.base import TTSProvider


# (voice_name, speed)
FACTION_VOICE = {
    "Northern Realms": ("echo",  1.0),
    "Skellige":        ("onyx",  0.9),
    "Scoia'tael":      ("nova",  1.1),
    "Monsters":        ("fable", 0.85),
    "Nilfgaardian":    ("alloy", 0.95),
}

DEFAULT_VOICE = ("echo", 1.0)
MODEL = "tts-1"


class OpenAIProvider(TTSProvider):
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable is not set"
            )
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)

    def synthesize(self, text: str, faction: str | None, dest_mp3: str) -> None:
        voice, speed = (
            FACTION_VOICE.get(faction, DEFAULT_VOICE)
            if faction else DEFAULT_VOICE
        )
        response = self._client.audio.speech.create(
            model=MODEL,
            voice=voice,
            input=text,
            speed=speed,
        )
        with open(dest_mp3, "wb") as f:
            f.write(response.content)
