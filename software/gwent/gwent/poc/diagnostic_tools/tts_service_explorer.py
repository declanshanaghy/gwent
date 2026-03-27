#!/usr/bin/env python3

"""
TTS Service Explorer for Gwent

Cycles through multiple TTS providers (gTTS, Piper, Edge TTS, OpenAI, ElevenLabs,
Google Cloud, Amazon Polly), playing sample voices from each with Gwent-themed phrases.
Providers that aren't installed or configured are gracefully skipped.
"""

import abc
import asyncio
import hashlib
import itertools
import os
import shutil
import subprocess
import tempfile
import time

import pydub
import pygame.mixer
from dotenv import load_dotenv

load_dotenv()

CACHE_BASE = os.path.join(tempfile.gettempdir(), "gwent-tts-explorer")

PHRASES = [
    "A round of Gwent? Let's play.",
    "Northern Realms wins the round!",
    "Geralt plays a Spy card. Draw two cards.",
    "Scorch! Destroy the strongest cards on the battlefield.",
    "The Nilfgaardian Empire claims victory!",
    "Pass! Player ends the round.",
]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def ensure_wav(source_path: str, wav_path: str, source_format: str = "mp3"):
    """Convert source audio to WAV at 24kHz for pygame compatibility."""
    if os.path.exists(wav_path):
        return
    sound = pydub.AudioSegment.from_file(source_path, format=source_format)
    sound = sound.set_frame_rate(24000).set_channels(2).set_sample_width(2)
    sound.export(wav_path, format="wav")


def play_wav(wav_path: str):
    clip = pygame.mixer.Sound(wav_path)
    clip.play()
    time.sleep(clip.get_length() + 0.3)


def announce_label(text: str):
    """Speak a label using gTTS (always available as the baseline announcer)."""
    import gtts
    ann_dir = os.path.join(CACHE_BASE, "_announcements")
    os.makedirs(ann_dir, exist_ok=True)
    mp3 = os.path.join(ann_dir, f"{text_hash(text)}.mp3")
    wav = mp3.replace(".mp3", ".wav")
    if not os.path.exists(mp3):
        gtts.gTTS(text, lang="en", tld="com").save(mp3)
    if not os.path.exists(wav):
        ensure_wav(mp3, wav)
    play_wav(wav)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class TTSProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod
    def available(self) -> tuple[bool, str]:
        """Return (is_available, reason_if_not)."""
        ...

    @abc.abstractmethod
    def voices(self) -> list[dict]:
        ...

    @abc.abstractmethod
    def synthesize(self, text: str, voice_config: dict, cache_dir: str) -> str:
        """Generate audio, return path to a WAV file."""
        ...

    def _wav_path(self, text: str, voice_id: str, cache_dir: str) -> str:
        return os.path.join(cache_dir, f"{text_hash(text)}.wav")


# ---------------------------------------------------------------------------
# 1. gTTS (baseline)
# ---------------------------------------------------------------------------

class GTTSProvider(TTSProvider):
    name = "gTTS (Google Translate)"

    def available(self):
        try:
            import gtts  # noqa: F401
            return True, ""
        except ImportError:
            return False, "gtts not installed"

    def voices(self):
        return [
            {"id": "com", "label": "US English"},
            {"id": "co.uk", "label": "UK English"},
            {"id": "com.au", "label": "Australian English"},
        ]

    def synthesize(self, text, voice_config, cache_dir):
        import gtts
        wav = self._wav_path(text, voice_config["id"], cache_dir)
        if os.path.exists(wav):
            return wav
        mp3 = wav.replace(".wav", ".mp3")
        if not os.path.exists(mp3):
            tts = gtts.gTTS(text, lang="en", tld=voice_config["id"])
            tts.save(mp3)
        ensure_wav(mp3, wav)
        return wav


# ---------------------------------------------------------------------------
# 2. Piper TTS (local)
# ---------------------------------------------------------------------------

class PiperTTSProvider(TTSProvider):
    name = "Piper TTS (local)"

    def available(self):
        if shutil.which("piper") is None:
            return False, "piper binary not found (pip install piper-tts)"
        return True, ""

    def voices(self):
        return [
            {"id": "en_US-lessac-medium", "label": "Lessac (US)"},
            {"id": "en_US-amy-medium", "label": "Amy (US)"},
            {"id": "en_GB-alan-medium", "label": "Alan (GB)"},
        ]

    def synthesize(self, text, voice_config, cache_dir):
        wav = self._wav_path(text, voice_config["id"], cache_dir)
        if os.path.exists(wav):
            return wav
        raw_wav = wav.replace(".wav", "_raw.wav")
        if not os.path.exists(raw_wav):
            print(f"    Generating with Piper (may download model on first run)...")
            result = subprocess.run(
                ["piper", "--model", voice_config["id"],
                 "--output_file", raw_wav],
                input=text, text=True, capture_output=True, timeout=180,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Piper failed: {result.stderr.strip()}")
        # Resample to 24kHz stereo for pygame
        ensure_wav(raw_wav, wav, source_format="wav")
        return wav


# ---------------------------------------------------------------------------
# 3. Edge TTS (free, no API key)
# ---------------------------------------------------------------------------

class EdgeTTSProvider(TTSProvider):
    name = "Edge TTS (Microsoft)"

    def available(self):
        try:
            import edge_tts  # noqa: F401
            return True, ""
        except ImportError:
            return False, "edge-tts not installed (pip install edge-tts)"

    def voices(self):
        return [
            {"id": "en-US-GuyNeural", "label": "Guy (US Male)"},
            {"id": "en-US-JennyNeural", "label": "Jenny (US Female)"},
            {"id": "en-GB-SoniaNeural", "label": "Sonia (GB Female)"},
        ]

    def synthesize(self, text, voice_config, cache_dir):
        import edge_tts
        wav = self._wav_path(text, voice_config["id"], cache_dir)
        if os.path.exists(wav):
            return wav
        mp3 = wav.replace(".wav", ".mp3")
        if not os.path.exists(mp3):
            async def _gen():
                comm = edge_tts.Communicate(text, voice_config["id"])
                await comm.save(mp3)
            asyncio.run(_gen())
        ensure_wav(mp3, wav)
        return wav


# ---------------------------------------------------------------------------
# 4. OpenAI TTS
# ---------------------------------------------------------------------------

class OpenAITTSProvider(TTSProvider):
    name = "OpenAI TTS"

    def available(self):
        try:
            import openai  # noqa: F401
        except ImportError:
            return False, "openai not installed (pip install openai)"
        if not os.environ.get("OPENAI_API_KEY"):
            return False, "OPENAI_API_KEY not set"
        return True, ""

    def voices(self):
        return [
            {"id": "alloy", "label": "Alloy (neutral)"},
            {"id": "nova", "label": "Nova (warm female)"},
            {"id": "onyx", "label": "Onyx (deep male)"},
        ]

    def synthesize(self, text, voice_config, cache_dir):
        from openai import OpenAI
        wav = self._wav_path(text, voice_config["id"], cache_dir)
        if os.path.exists(wav):
            return wav
        mp3 = wav.replace(".wav", ".mp3")
        if not os.path.exists(mp3):
            client = OpenAI()
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice_config["id"],
                input=text,
            )
            response.stream_to_file(mp3)
        ensure_wav(mp3, wav)
        return wav


# ---------------------------------------------------------------------------
# 5. ElevenLabs
# ---------------------------------------------------------------------------

class ElevenLabsProvider(TTSProvider):
    name = "ElevenLabs"

    def available(self):
        try:
            import elevenlabs  # noqa: F401
        except ImportError:
            return False, "elevenlabs not installed (pip install elevenlabs)"
        if not os.environ.get("ELEVENLABS_API_KEY"):
            return False, "ELEVENLABS_API_KEY not set"
        return True, ""

    def voices(self):
        # Hardcoded premade voice IDs (no voices_read permission needed)
        return [
            {"id": "21m00Tcm4TlvDq8ikWAM", "label": "Rachel (calm female)"},
            {"id": "pNInz6obpgDQGcFmaJgB", "label": "Adam (deep male)"},
            {"id": "EXAVITQu4vr4xnSDxMaL", "label": "Bella (soft female)"},
        ]

    def synthesize(self, text, voice_config, cache_dir):
        from elevenlabs.client import ElevenLabs as ELClient
        wav = self._wav_path(text, voice_config["id"], cache_dir)
        if os.path.exists(wav):
            return wav
        mp3 = wav.replace(".wav", ".mp3")
        if not os.path.exists(mp3):
            client = ELClient(api_key=os.environ["ELEVENLABS_API_KEY"])
            audio_bytes = client.text_to_speech.convert(
                text=text,
                voice_id=voice_config["id"],
                model_id="eleven_monolingual_v1",
            )
            # convert() may return bytes or an iterator of bytes
            if isinstance(audio_bytes, (bytes, bytearray)):
                data = audio_bytes
            else:
                data = b"".join(audio_bytes)
            if not data:
                raise RuntimeError("ElevenLabs returned empty audio")
            with open(mp3, "wb") as f:
                f.write(data)
        ensure_wav(mp3, wav)
        return wav


# ---------------------------------------------------------------------------
# 6. Google Cloud TTS
# ---------------------------------------------------------------------------

class GoogleCloudTTSProvider(TTSProvider):
    name = "Google Cloud TTS"

    def available(self):
        try:
            from google.cloud import texttospeech  # noqa: F401
        except ImportError:
            return False, "google-cloud-texttospeech not installed"
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            return False, "GOOGLE_APPLICATION_CREDENTIALS not set"
        return True, ""

    def voices(self):
        return [
            {"id": "en-US-Neural2-D", "label": "Neural2-D (US Male)"},
            {"id": "en-US-Neural2-F", "label": "Neural2-F (US Female)"},
            {"id": "en-GB-Neural2-A", "label": "Neural2-A (GB Female)"},
        ]

    def synthesize(self, text, voice_config, cache_dir):
        from google.cloud import texttospeech
        wav = self._wav_path(text, voice_config["id"], cache_dir)
        if os.path.exists(wav):
            return wav
        client = texttospeech.TextToSpeechClient()
        voice_id = voice_config["id"]
        lang_code = "-".join(voice_id.split("-")[:2])
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=lang_code, name=voice_id)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000)
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice_params,
            audio_config=audio_config)
        with open(wav, "wb") as f:
            f.write(response.audio_content)
        return wav


# ---------------------------------------------------------------------------
# 7. Amazon Polly
# ---------------------------------------------------------------------------

class AmazonPollyProvider(TTSProvider):
    name = "Amazon Polly"

    def available(self):
        try:
            import boto3  # noqa: F401
        except ImportError:
            return False, "boto3 not installed (pip install boto3)"
        if not os.environ.get("AWS_ACCESS_KEY_ID"):
            return False, "AWS_ACCESS_KEY_ID not set"
        # Verify credentials work
        try:
            client = boto3.client("polly", region_name="us-east-1")
            client.describe_voices(LanguageCode="en-US")
            return True, ""
        except Exception as e:
            return False, f"AWS auth failed: {e}"

    def voices(self):
        return [
            {"id": "Matthew", "label": "Matthew (US Male)", "engine": "neural"},
            {"id": "Joanna", "label": "Joanna (US Female)", "engine": "neural"},
            {"id": "Amy", "label": "Amy (GB Female)", "engine": "neural"},
        ]

    def synthesize(self, text, voice_config, cache_dir):
        import boto3
        wav = self._wav_path(text, voice_config["id"], cache_dir)
        if os.path.exists(wav):
            return wav
        mp3 = wav.replace(".wav", ".mp3")
        if not os.path.exists(mp3):
            client = boto3.client("polly", region_name="us-east-1")
            response = client.synthesize_speech(
                Text=text,
                VoiceId=voice_config["id"],
                Engine=voice_config.get("engine", "neural"),
                OutputFormat="mp3",
                SampleRate="24000",
            )
            with open(mp3, "wb") as f:
                f.write(response["AudioStream"].read())
        ensure_wav(mp3, wav)
        return wav


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_PROVIDERS = [
    GTTSProvider,
    PiperTTSProvider,
    EdgeTTSProvider,
    OpenAITTSProvider,
    ElevenLabsProvider,
    GoogleCloudTTSProvider,
    AmazonPollyProvider,
]


def main():
    os.makedirs(CACHE_BASE, exist_ok=True)
    pygame.mixer.init(frequency=24000, size=-16, channels=2)

    phrase_cycle = itertools.cycle(PHRASES)
    results = []

    providers = [cls() for cls in ALL_PROVIDERS]

    print(f"TTS Service Explorer — testing {len(providers)} providers")
    print(f"Cache: {CACHE_BASE}\n")

    for provider in providers:
        print(f"{'=' * 60}")
        print(f"Provider: {provider.name}")
        print(f"{'=' * 60}")

        ok, reason = provider.available()
        if not ok:
            print(f"  SKIPPED — {reason}\n")
            results.append((provider.name, "—", f"SKIPPED: {reason}"))
            continue

        for voice in provider.voices():
            phrase = next(phrase_cycle)
            label = voice["label"]
            vid = voice["id"]
            print(f"\n  Voice: {label}")
            print(f"  Phrase: \"{phrase}\"")

            try:
                cache_dir = os.path.join(
                    CACHE_BASE,
                    provider.name.lower().replace(" ", "_").replace("(", "").replace(")", ""),
                    vid.replace("/", "_"),
                )
                os.makedirs(cache_dir, exist_ok=True)
                print(f"  Generating...", end=" ", flush=True)
                wav_path = provider.synthesize(phrase, voice, cache_dir)
                print(f"Playing...")
                announce_label(f"{provider.name}. {label}.")
                play_wav(wav_path)
                results.append((provider.name, label, "OK"))
            except Exception as e:
                print(f"  ERROR: {e}")
                results.append((provider.name, label, f"ERROR: {e}"))

        print()

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"{'Provider':<28} {'Voice':<28} {'Status':<10}")
    print(f"{'-' * 28} {'-' * 28} {'-' * 10}")
    for pname, vlabel, status in results:
        # Truncate long error messages in summary
        if len(status) > 40:
            status = status[:37] + "..."
        print(f"{pname:<28} {vlabel:<28} {status}")

    pygame.mixer.quit()
    print(f"\nAudio cached in: {CACHE_BASE}")


if __name__ == "__main__":
    main()
