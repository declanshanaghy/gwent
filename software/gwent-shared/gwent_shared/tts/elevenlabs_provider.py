"""ElevenLabs TTS provider.

Requires ELEVENLABS_API_KEY environment variable.

Faction voices use ElevenLabs premade voice IDs chosen to match each
faction's personality.  Per-faction VoiceSettings tune delivery style:
  Northern Realms → Antoni   (warm British male — noble, chivalric)
                    high stability, moderate style — steady & commanding
  Skellige        → Freya    (American female — fierce shieldmaiden)
                    low stability, high style — wild & unpredictable
  Scoia'tael      → Charlotte (British female — lighter, elvish grace)
                    high stability, low style — calm & precise
  Monsters        → Daniel   (formal British male — menacing authority)
                    low stability, high style — dark & dramatic
  Nilfgaardian    → Ethan    (confident American male — imperial authority)
                    very high stability, moderate style — cold & controlled
  default         → Rachel   (neutral American female)
"""

import os

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from gwent_shared.tts.base import TTSProvider


FACTION_VOICE_ID = {
    "Northern Realms": "ErXwobaYiN019PkySvjV",  # Antoni
    "Skellige":        "jsCqWAovK2LkecY7zXl4",  # Freya
    "Scoia'tael":      "XB0fDUnXU5powFXDhCwa",  # Charlotte
    "Monsters":        "onwK4e9ZLuTAKqWW03F9",  # Daniel
    "Nilfgaardian":    "N2lVS1w4EtoT3dr4eOWO",  # Ethan
}

# Per-faction voice tuning: (stability, similarity_boost, style)
# stability:        0=variable/dramatic, 1=steady/consistent
# similarity_boost: 0=more creative, 1=closer to original voice
# style:            0=neutral delivery, 1=exaggerated expressiveness
FACTION_VOICE_SETTINGS = {
    "Northern Realms": (0.70, 0.75, 0.40),  # steady, commanding
    "Skellige":        (0.35, 0.60, 0.80),  # wild, unpredictable
    "Scoia'tael":      (0.80, 0.70, 0.20),  # calm, precise
    "Monsters":        (0.30, 0.50, 0.90),  # dark, dramatic
    "Nilfgaardian":    (0.85, 0.80, 0.45),  # cold, controlled
}

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
DEFAULT_SETTINGS = (0.50, 0.75, 0.00)
MODEL_ID = "eleven_monolingual_v1"


class ElevenLabsProvider(TTSProvider):
    native_wav = False  # WAV output requires Pro tier; use MP3 + convert

    def __init__(self):
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY environment variable is not set"
            )
        self._client = ElevenLabs(api_key=api_key)

    def synthesize(self, text: str, faction: str | None, dest: str) -> None:
        voice_id = FACTION_VOICE_ID.get(faction, DEFAULT_VOICE_ID) if faction else DEFAULT_VOICE_ID
        stability, similarity, style = (
            FACTION_VOICE_SETTINGS.get(faction, DEFAULT_SETTINGS)
            if faction else DEFAULT_SETTINGS
        )

        audio_iter = self._client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=MODEL_ID,
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=stability,
                similarity_boost=similarity,
                style=style,
                use_speaker_boost=True,
            ),
        )
        with open(dest, "wb") as f:
            for chunk in audio_iter:
                f.write(chunk)
