"""TTS provider factory."""

import platform

from gwent.hal.tts.base import TTSProvider
from gwent.hal.tts.gtts_provider import GTTSProvider
from gwent.hal.tts.elevenlabs_provider import ElevenLabsProvider
from gwent.hal.tts.openai_provider import OpenAIProvider
from gwent.hal.tts.piper_provider import PiperProvider
from gwent.hal.tts.say_provider import SayProvider

PROVIDERS = {
    "gtts": GTTSProvider,
    "elevenlabs": ElevenLabsProvider,
    "openai": OpenAIProvider,
    "piper": PiperProvider,
    "say": SayProvider,
}

DEFAULT_PROVIDER = "elevenlabs"

# Platform-local provider (no API key, no network)
LOCAL_PROVIDER = "say" if platform.system() == "Darwin" else "piper"


def get_provider(name: str = DEFAULT_PROVIDER) -> TTSProvider:
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown TTS provider '{name}'. "
            f"Available: {', '.join(PROVIDERS)}"
        )
    return cls()
