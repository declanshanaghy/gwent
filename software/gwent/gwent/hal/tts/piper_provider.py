"""Piper TTS provider — local neural TTS, no API key required.

Requires piper-tts pip package and pre-downloaded ONNX voice models
in ~/.local/share/piper-voices/. Models are installed by
scripts/install-system.sh.

Faction voices use different piper English models for personality:
  Northern Realms → en_GB-alan-medium      (British male — noble)
  Skellige        → en_GB-northern_english_male-medium  (gruff Northern — warrior)
  Scoia'tael      → en_US-ryan-medium      (American male — light, precise)
  Monsters        → en_US-joe-medium       (American male — low, ominous)
  Nilfgaardian    → en_US-bryce-medium     (American male — commanding)
  default         → en_US-ryan-medium
"""

import os
import subprocess

from gwent.hal.tts.base import TTSProvider


MODEL_DIR = os.path.expanduser("~/.local/share/piper-voices")

FACTION_VOICE = {
    "Northern Realms": "en_GB-alan-medium",
    "Skellige":        "en_GB-northern_english_male-medium",
    "Scoia'tael":      "en_US-ryan-medium",
    "Monsters":        "en_US-joe-medium",
    "Nilfgaardian":    "en_US-bryce-medium",
}

DEFAULT_VOICE = "en_US-ryan-medium"


class PiperProvider(TTSProvider):
    native_wav = True

    def synthesize(self, text: str, faction: str | None, dest: str) -> None:
        model_name = (
            FACTION_VOICE.get(faction, DEFAULT_VOICE)
            if faction else DEFAULT_VOICE
        )
        model_path = os.path.join(MODEL_DIR, f"{model_name}.onnx")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Piper model not found: {model_path}\n"
                f"Run: bash scripts/install-system.sh"
            )

        result = subprocess.run(
            ["piper", "--model", model_path, "--output-file", dest],
            input=text.encode(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Piper synthesis failed (rc={result.returncode})")
