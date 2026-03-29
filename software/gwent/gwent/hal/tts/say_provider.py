"""macOS `say` TTS provider — native, no API key required.

Uses the built-in macOS `say` command. Only available on Darwin.

Faction voices use different macOS system voices:
  Northern Realms → Daniel   (British male — noble, authoritative)
  Skellige        → Moira    (Irish female — Celtic warrior)
  Scoia'tael      → Samantha (American female — light, precise)
  Monsters        → Tom      (American male — deep, ominous)
  Nilfgaardian    → Oliver   (British male — imperial, controlled)
  default         → Daniel
"""

import subprocess

from gwent.hal.tts.base import TTSProvider


FACTION_VOICE = {
    "Northern Realms": "Daniel",
    "Skellige":        "Moira",
    "Scoia'tael":      "Samantha",
    "Monsters":        "Tom",
    "Nilfgaardian":    "Oliver",
}

DEFAULT_VOICE = "Daniel"


class SayProvider(TTSProvider):
    native_wav = True

    def synthesize(self, text: str, faction: str | None, dest: str) -> None:
        voice = (
            FACTION_VOICE.get(faction, DEFAULT_VOICE)
            if faction else DEFAULT_VOICE
        )

        result = subprocess.run(
            ["say", "-v", voice, "-r", "180", "-o", dest, "--data-format=LEI16@22050"],
            input=text,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise RuntimeError(f"say failed (rc={result.returncode})")
