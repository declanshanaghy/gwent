"""TTS provider factory."""

from gwent.hal.tts.base import TTSProvider
from gwent.hal.tts.gtts_provider import GTTSProvider
from gwent.hal.tts.elevenlabs_provider import ElevenLabsProvider
from gwent.hal.tts.openai_provider import OpenAIProvider

PROVIDERS = {
    "gtts": GTTSProvider,
    "elevenlabs": ElevenLabsProvider,
    "openai": OpenAIProvider,
}

DEFAULT_PROVIDER = "elevenlabs"


def get_provider(name: str = DEFAULT_PROVIDER) -> TTSProvider:
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown TTS provider '{name}'. "
            f"Available: {', '.join(PROVIDERS)}"
        )
    return cls()
