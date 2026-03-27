#!/usr/bin/env python3

"""
TTS Voice Explorer for Gwent

Cycles through available voices for a given TTS provider, announces each
voice/faction, then speaks a Gwent-themed test phrase.

Usage:
    tts-voice-explorer                    # explore all gTTS accent variants
    tts-voice-explorer --provider gtts
    tts-voice-explorer --provider elevenlabs
    tts-voice-explorer --provider openai
"""

import argparse
import os
import tempfile
import time

import pydub
import pygame.mixer


GWENT_PHRASES = [
    "A round of Gwent? Let's play.",
    "Northern Realms wins the round!",
    "Geralt plays a Spy card. Draw two cards.",
    "Pass! Player ends the round.",
    "Scorch! Destroy the strongest cards on the battlefield.",
    "The Nilfgaardian Empire claims victory!",
]

FACTIONS = [
    "Northern Realms",
    "Skellige",
    "Scoia'tael",
    "Monsters",
    "Nilfgaardian",
]

# All gTTS accent TLDs (for --provider gtts full tour)
GTTS_ALL_VOICES = [
    ("com",    "US English",          None),
    ("co.uk",  "UK English",          "Northern Realms"),
    ("com.au", "Australian English",  "Nilfgaardian"),
    ("co.in",  "Indian English",      "Skellige"),
    ("ca",     "Canadian English",    None),
    ("co.za",  "South African English", None),
    ("ie",     "Irish English",       "Scoia'tael"),
    ("co.nz",  "New Zealand English", None),
    ("com.ng", "Nigerian English",    "Monsters"),
    ("com.gh", "Ghanaian English",    None),
    ("com.ph", "Philippine English",  None),
    ("com.sg", "Singaporean English", None),
    ("com.hk", "Hong Kong English",   None),
]


def speak_wav(wav_path: str):
    clip = pygame.mixer.Sound(wav_path)
    clip.play()
    time.sleep(clip.get_length() + 0.3)


def synthesize_and_play(provider, text: str, faction, tmpdir: str, label: str):
    safe = (label + "_" + text[:30]).replace(" ", "_").replace("'", "")
    safe = "".join(c for c in safe if c.isalnum() or c == "_")
    mp3_path = os.path.join(tmpdir, f"{safe}.mp3")
    wav_path = os.path.join(tmpdir, f"{safe}.wav")

    if not os.path.exists(mp3_path):
        provider.synthesize(text, faction, mp3_path)

    if not os.path.exists(wav_path):
        audio = pydub.AudioSegment.from_mp3(mp3_path)
        audio.export(wav_path, format="wav")

    speak_wav(wav_path)


def explore_gtts(tmpdir: str):
    """Cycle all 13 gTTS accent variants."""
    import gtts as _gtts

    print(f"Exploring {len(GTTS_ALL_VOICES)} gTTS accent variants\n")

    phrase_iter = iter(GWENT_PHRASES * 3)

    for i, (tld, accent, faction) in enumerate(GTTS_ALL_VOICES, 1):
        phrase = next(phrase_iter)
        tag = f"[gwent faction: {faction}]" if faction else ""
        print(f"[{i}/{len(GTTS_ALL_VOICES)}] {accent} (tld={tld}) {tag}")
        print(f"  Phrase: {phrase}")

        # Synthesize announcement + phrase using raw gtts (bypass provider for accent tour)
        def _synth(text, dest):
            _gtts.gTTS(text, lang="en", tld=tld).save(dest)

        for text, lbl in [(f"{accent} voice.", f"{tld}_announce"),
                          (phrase, f"{tld}_phrase")]:
            safe = lbl.replace(".", "_")
            mp3 = os.path.join(tmpdir, f"{safe}.mp3")
            wav = os.path.join(tmpdir, f"{safe}.wav")
            if not os.path.exists(mp3):
                _synth(text, mp3)
            if not os.path.exists(wav):
                pydub.AudioSegment.from_mp3(mp3).export(wav, format="wav")
            speak_wav(wav)

        print()


def explore_provider(provider_name: str, tmpdir: str):
    """Test a provider with each Gwent faction voice."""
    from gwent.hal.tts import get_provider
    provider = get_provider(provider_name)

    print(f"Exploring {provider_name} provider — {len(FACTIONS)} faction voices\n")

    for i, faction in enumerate(FACTIONS, 1):
        phrase = GWENT_PHRASES[(i - 1) % len(GWENT_PHRASES)]
        print(f"[{i}/{len(FACTIONS)}] {faction}")
        print(f"  Phrase: {phrase}")

        label = f"{provider_name}_{faction}"
        synthesize_and_play(provider, f"{faction} voice.", faction, tmpdir, label + "_announce")
        synthesize_and_play(provider, phrase, faction, tmpdir, label + "_phrase")
        print()


def main():
    parser = argparse.ArgumentParser(description="Gwent TTS Voice Explorer")
    parser.add_argument("-p", "--provider",
                        choices=["gtts", "elevenlabs", "openai"],
                        default="gtts",
                        help="TTS provider to explore (default: gtts)")
    args = parser.parse_args()

    tmpdir = os.path.join(tempfile.gettempdir(), "gwent-tts-explorer")
    os.makedirs(tmpdir, exist_ok=True)

    pygame.mixer.init(frequency=24000, size=-16, channels=2)

    if args.provider == "gtts":
        explore_gtts(tmpdir)
    else:
        explore_provider(args.provider, tmpdir)

    pygame.mixer.quit()
    print("Done! Audio cached in:", tmpdir)


if __name__ == "__main__":
    main()
