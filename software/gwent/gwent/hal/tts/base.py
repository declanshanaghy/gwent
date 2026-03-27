"""Abstract base class for TTS providers."""

import abc


class TTSProvider(abc.ABC):
    """Synthesize text to an MP3 file on disk."""

    @abc.abstractmethod
    def synthesize(self, text: str, faction: str | None, dest_mp3: str) -> None:
        """Generate speech for *text* and save it to *dest_mp3*.

        Args:
            text:      The announcement text.
            faction:   Current player's faction name, or None for default voice.
            dest_mp3:  Absolute path where the MP3 file should be written.
        """
