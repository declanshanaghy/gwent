"""Abstract base class for TTS providers."""

import abc


class TTSProvider(abc.ABC):
    """Synthesize text to an audio file on disk."""

    # Whether this provider outputs WAV directly (True) or MP3 (False).
    # Providers that output MP3 need a pydub conversion step.
    native_wav = False

    @abc.abstractmethod
    def synthesize(self, text: str, faction: str | None, dest: str) -> None:
        """Generate speech for *text* and save it to *dest*.

        Args:
            text:     The announcement text.
            faction:  Current player's faction name, or None for default voice.
            dest:     Absolute path where the audio file should be written.
                      Extension is .wav if native_wav is True, .mp3 otherwise.
        """
