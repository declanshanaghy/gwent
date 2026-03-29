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

from gwent_shared.tts.base import TTSProvider


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
    can_speak_direct = True  # can speak without file synthesis

    def _voice_for(self, faction: str | None) -> str:
        if faction:
            return FACTION_VOICE.get(faction, DEFAULT_VOICE)
        return DEFAULT_VOICE

    def synthesize(self, text: str, faction: str | None, dest: str) -> None:
        voice = self._voice_for(faction)
        result = subprocess.run(
            ["say", "-v", voice, "-o", dest,
             "--file-format=WAVE", "--data-format=LEI16@22050"],
            input=text,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise RuntimeError(f"say failed (rc={result.returncode})")

    def speak_direct(self, text: str, faction: str | None = None) -> subprocess.Popen:
        """Speak directly without writing to a file. Returns the process."""
        voice = self._voice_for(faction)
        return subprocess.Popen(
            ["say", "-v", voice, text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
