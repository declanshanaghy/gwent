#!/usr/bin/env python3

"""
TTS Voice Explorer for Gwent

Cycles through available voices for a given TTS provider, announces each
voice/faction, then speaks a Gwent-themed test phrase.

Usage:
    tts-voice-explorer                    # explore all gTTS accent variants
    tts-voice-explorer --tts gtts
    tts-voice-explorer --tts elevenlabs
    tts-voice-explorer --tts openai
    tts-voice-explorer --tts say          # macOS native voices
    tts-voice-explorer --tts piper        # local neural TTS (Linux)
    tts-voice-explorer --tts piper --show # show mapping without audio
"""

import argparse
import os
import platform
import subprocess
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


def _get_say_voices():
    """Parse `say -v '?'` output into list of (name, lang, description)."""
    try:
        result = subprocess.run(
            ["say", "-v", "?"], capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    voices = []
    for line in result.stdout.strip().splitlines():
        # Format: "Name                lang   # description"
        parts = line.split("#", 1)
        desc = parts[1].strip() if len(parts) > 1 else ""
        left = parts[0].strip()
        # Name and lang are separated by whitespace; lang is like "en_US"
        tokens = left.rsplit(None, 1)
        if len(tokens) == 2:
            name, lang = tokens
            voices.append((name.strip(), lang.strip(), desc))
    return voices


def explore_say(tmpdir: str):
    """Assign a random macOS voice to each faction and audition them."""
    import random

    if platform.system() != "Darwin":
        print("The 'say' provider is only available on macOS.")
        return

    all_voices = _get_say_voices()
    # Filter to English voices
    en_voices = [(n, l, d) for n, l, d in all_voices if l.startswith("en")]

    if not en_voices:
        print("No English voices found. Install voices in System Settings > "
              "Accessibility > Spoken Content > System Voice > Manage Voices.")
        return

    # Assign a random voice per faction (like other providers)
    shuffled = list(en_voices)
    random.shuffle(shuffled)
    assignments = {}
    for i, faction in enumerate(FACTIONS):
        assignments[faction] = shuffled[i % len(shuffled)]

    print(f"macOS `say` — {len(en_voices)} English voices available")
    print(f"Random voice assigned per faction:\n")

    for i, faction in enumerate(FACTIONS, 1):
        name, lang, desc = assignments[faction]
        phrase = GWENT_PHRASES[(i - 1) % len(GWENT_PHRASES)]
        print(f"[{i}/{len(FACTIONS)}] {faction} → {name} ({lang})")
        if desc:
            print(f"  Sample: {desc}")
        print(f"  Phrase: {phrase}")

        for text in [f"{faction} voice. {name}.", phrase]:
            subprocess.run(
                ["say", "-v", name, "-r", "180", text],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print()

    print("\nAll English voices on this system:")
    for name, lang, desc in en_voices:
        print(f"  {name:20s} {lang:8s}  {desc}")


PIPER_MODEL_DIR = os.path.expanduser("~/.local/share/piper-voices")

# Piper voices installed by scripts/install-system.sh
PIPER_VOICES = [
    "en_US-ryan-medium",
    "en_GB-northern_english_male-medium",
    "en_GB-alan-medium",
    "en_US-joe-medium",
    "en_US-bryce-medium",
]


def explore_piper(tmpdir: str):
    """Assign a random piper voice to each faction and audition them."""
    import random

    # Find installed models
    installed = []
    for name in PIPER_VOICES:
        onnx = os.path.join(PIPER_MODEL_DIR, f"{name}.onnx")
        if os.path.exists(onnx):
            installed.append((name, onnx))

    if not installed:
        print(f"No piper models found in {PIPER_MODEL_DIR}")
        print("Run: bash scripts/install-system.sh  to download models.")
        return

    # Assign a random voice per faction
    shuffled = list(installed)
    random.shuffle(shuffled)
    assignments = {}
    for i, faction in enumerate(FACTIONS):
        assignments[faction] = shuffled[i % len(shuffled)]

    print(f"Piper TTS — {len(installed)} voices installed")
    print(f"Random voice assigned per faction:\n")

    pygame.mixer.init(frequency=22050, size=-16, channels=1)

    for i, faction in enumerate(FACTIONS, 1):
        name, onnx = assignments[faction]
        phrase = GWENT_PHRASES[(i - 1) % len(GWENT_PHRASES)]
        print(f"[{i}/{len(FACTIONS)}] {faction} → {name}")
        print(f"  Phrase: {phrase}")

        for text in [f"{faction} voice. {name}.", phrase]:
            safe = f"piper_{name}_{text[:30]}".replace(" ", "_").replace("'", "")
            safe = "".join(c for c in safe if c.isalnum() or c == "_")
            wav_path = os.path.join(tmpdir, f"{safe}.wav")

            if not os.path.exists(wav_path):
                result = subprocess.run(
                    ["piper", "--model", onnx, "--output-file", wav_path],
                    input=text.encode(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if result.returncode != 0:
                    print(f"  Error synthesizing: {text[:40]}")
                    continue

            clip = pygame.mixer.Sound(wav_path)
            clip.play()
            time.sleep(clip.get_length() + 0.3)

        print()

    pygame.mixer.quit()

    print("\nInstalled piper voices:")
    for name, onnx in installed:
        print(f"  {name}")


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


def show_mapping(provider_name: str):
    """Print the current faction→voice mapping for a provider."""
    from gwent.hal.tts import piper_provider, say_provider
    from gwent.hal.tts import elevenlabs_provider, openai_provider, gtts_provider

    maps = {
        "piper": (piper_provider.FACTION_VOICE, piper_provider.DEFAULT_VOICE),
        "say": (say_provider.FACTION_VOICE, say_provider.DEFAULT_VOICE),
        "elevenlabs": (elevenlabs_provider.FACTION_VOICE_ID, elevenlabs_provider.DEFAULT_VOICE_ID),
        "openai": ({k: v[0] for k, v in openai_provider.FACTION_VOICE.items()},
                   openai_provider.DEFAULT_VOICE[0]),
        "gtts": ({k: v[0] for k, v in gtts_provider.FACTION_VOICE.items()},
                 gtts_provider.DEFAULT_VOICE[0]),
    }
    fv, default = maps.get(provider_name, ({}, "?"))

    print(f"\n{provider_name} faction mapping:")
    print(f"  {'Faction':<20s} Voice")
    print(f"  {'─' * 20} {'─' * 30}")
    for faction in FACTIONS:
        voice = fv.get(faction, default)
        print(f"  {faction:<20s} {voice}")
    print(f"  {'(default)':<20s} {default}")


def main():
    parser = argparse.ArgumentParser(description="Gwent TTS Voice Explorer")
    parser.add_argument("-t", "--tts",
                        choices=["gtts", "elevenlabs", "openai", "say", "piper"],
                        default="gtts",
                        help="TTS provider to explore (default: gtts)")
    parser.add_argument("--show", action="store_true",
                        help="Show current faction mapping without playing audio")
    args = parser.parse_args()

    if args.show:
        show_mapping(args.tts)
        return

    tmpdir = os.path.join(tempfile.gettempdir(), "gwent-tts-explorer")
    os.makedirs(tmpdir, exist_ok=True)

    if args.tts == "say":
        explore_say(tmpdir)
    elif args.tts == "piper":
        explore_piper(tmpdir)
    else:
        pygame.mixer.init(frequency=24000, size=-16, channels=2)
        if args.tts == "gtts":
            explore_gtts(tmpdir)
        else:
            explore_provider(args.tts, tmpdir)
        pygame.mixer.quit()
    print("Done! Audio cached in:", tmpdir)


if __name__ == "__main__":
    main()
