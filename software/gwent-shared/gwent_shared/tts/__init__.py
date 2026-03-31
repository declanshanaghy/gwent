"""TTS provider factory."""

import platform

from gwent_shared.tts.base import TTSProvider
from gwent_shared.tts.gtts_provider import GTTSProvider
from gwent_shared.tts.elevenlabs_provider import ElevenLabsProvider
from gwent_shared.tts.openai_provider import OpenAIProvider
from gwent_shared.tts.piper_provider import PiperProvider
from gwent_shared.tts.say_provider import SayProvider
from gwent_shared.tts.none_provider import NoneProvider

PROVIDERS = {
    "gtts": GTTSProvider,
    "elevenlabs": ElevenLabsProvider,
    "openai": OpenAIProvider,
    "piper": PiperProvider,
    "say": SayProvider,
    "none": NoneProvider,
}

DEFAULT_PROVIDER = "gtts"

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
