#!/usr/bin/env python3
"""Write the next unchipped card to an RFID tag.

Iterates through all card JSON files by faction, finds cards without an
"rfid" field, and writes them one at a time. Completes an entire faction
before moving to the next. 5 second delay between cards to swap.

Non-starter cards require an owner — presents a selectable list.
Esc to skip a card.
"""

import glob
import json
import os
import signal
import sys
import time

from gwent.utils.logging import configure_logging, get_logger, DEBUG

# ANSI color codes for factions
FACTION_COLORS = {
    "Monsters":        "\033[31m",   # red
    "Nilfgaardian":    "\033[33m",   # yellow
    "NorthernRealms":  "\033[34m",   # blue
    "Northern Realms": "\033[34m",
    "Scoiatael":       "\033[32m",   # green
    "Scoia'tael":      "\033[32m",
    "Skellige":        "\033[36m",   # cyan
}
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"

# Emoji for card attributes
E_FACTION = {
    "Monsters":        "👹🔥",
    "Nilfgaardian":    "🌑☀️",
    "NorthernRealms":  "🦁⚖️",
    "Northern Realms": "🦁⚖️",
    "Scoiatael":       "🌿🏹",
    "Scoia'tael":      "🌿🏹",
    "Skellige":        "⚓🪓",
}
E_STRENGTH = "⚡"
E_SPECIALTY = {
    "hero": "🛡️",
    "leader": "👑",
    "scorch": "🔥",
    "decoy": "🎭",
    "commander": "📯",
    "weather": "🌧️",
    "mardroeme": "🐻",
}
E_ABILITY = {
    "spy": "🕵️",
    "medic": "🩺",
    "muster": "👥",
    "bond": "🤝",
    "morale": "💪",
    "commander": "📯",
    "agile": "🏃",
    "scorch": "🔥",
    "berserker": "🐻",
    "mardroeme": "🐻",
}
E_ROW = {
    "close": "⚔️",
    "ranged": "🏹",
    "siege": "🏰",
}
E_OWNER = "👤"
E_STARTER = "⭐"
E_FILE = "📄"
E_LEADER = "👑"

# Card read sound effect
CARD_READ_WAV = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "hal", "effects", "card_read.wav"
))


def _init_audio():
    """Initialize pygame mixer if needed."""
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()


def _play_card_fx():
    """Play the card read sound effect."""
    try:
        import pygame
        _init_audio()
        sound = pygame.mixer.Sound(CARD_READ_WAV)
        sound.play()
    except Exception:
        print("\a", end="", flush=True)


def _speak(text):
    """Speak text using gTTS and pygame. Non-blocking."""
    try:
        import hashlib
        import tempfile
        import gtts
        import pydub
        import pygame

        _init_audio()

        # Cache TTS files by content hash
        h = hashlib.md5(text.encode()).hexdigest()
        tts_dir = os.path.join(tempfile.gettempdir(), "gwent_tts")
        os.makedirs(tts_dir, exist_ok=True)
        fmp3 = os.path.join(tts_dir, f"{h}.mp3")
        fwav = os.path.join(tts_dir, f"{h}.wav")

        if not os.path.exists(fmp3):
            tts = gtts.gTTS(text, lang="en")
            tts.save(fmp3)

        if not os.path.exists(fwav):
            audio = pydub.AudioSegment.from_mp3(fmp3)
            audio.export(fwav, format="wav")

        sound = pygame.mixer.Sound(fwav)
        sound.play()
        # Wait for playback to finish
        import time as _time
        _time.sleep(sound.get_length())
    except Exception as e:
        pass  # TTS is best-effort


def _describe_card(data):
    """Build a spoken description of a card."""
    name = data.get("name", "unknown card")
    parts = [name]

    strength = data.get("strength")
    if strength is not None:
        parts.append(f"strength {strength}")

    ranges = data.get("ranges", [])
    if ranges:
        parts.append(", ".join(ranges) + " combat")

    specialty = data.get("specialty", "")
    if specialty == "hero":
        parts.append("hero card")
    elif specialty == "leader":
        parts.append("leader")
    elif specialty:
        parts.append(specialty)

    return ". ".join(parts)

# Card data directory
CARDS_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "cards"
))

# Faction directory order
FACTIONS = ["Monsters", "Nilfgaardian", "NorthernRealms", "Scoiatael", "Skellige"]


def find_unchipped_cards():
    """Yield (faction, filepath, card_data) for cards without an rfid field."""
    for faction in FACTIONS:
        faction_dir = os.path.join(CARDS_DIR, faction)
        if not os.path.isdir(faction_dir):
            continue

        for filename in sorted(os.listdir(faction_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(faction_dir, filename)
            with open(filepath) as f:
                data = json.load(f)
            if "rfid" not in data:
                yield faction, filepath, data


def find_all_owners():
    """Collect all unique owner names from existing card files."""
    owners = set()
    for filepath in glob.glob(os.path.join(CARDS_DIR, "**", "*.json"), recursive=True):
        with open(filepath) as f:
            data = json.load(f)
        owner = data.get("owner", "")
        if owner:
            owners.add(owner)
    return sorted(owners)


def prompt_owner(name, owners):
    """Prompt user to select an owner for a non-starter card.

    Returns the owner name, or None to skip the card.
    """
    print(f"\n  {name} is unowned — assign an owner?")
    print(f"  Select owner (Esc to skip):\n")
    for idx, owner in enumerate(owners, 1):
        print(f"    {idx}. {owner}")
    print(f"    n. New owner")
    print(f"    Esc. Skip this card")
    print()

    while True:
        try:
            choice = input("  Choice: ").strip()
        except (KeyboardInterrupt, EOFError):
            return None

        if choice == "\x1b" or choice.lower() == "esc":
            return None

        if choice.lower() == "n":
            try:
                new_owner = input("  Enter owner name: ").strip()
            except (KeyboardInterrupt, EOFError):
                return None
            if new_owner:
                return new_owner
            print("  Owner name cannot be empty.")
            continue

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(owners):
                return owners[idx - 1]

        print(f"  Invalid choice. Enter 1-{len(owners)}, 'n', or Esc.")


def main():
    configure_logging(level=DEBUG, log_file="/tmp/logs/write_next.log")
    log = get_logger("write_next")

    # Lazy import — hardware init happens here
    import gwent.cards.util
    from gwent.poc.util.read_write_cards import write_card

    # Collect existing owners
    owners = find_all_owners()
    log.info("Known owners: %s", owners)

    # Count unchipped cards
    unchipped = list(find_unchipped_cards())
    if not unchipped:
        print("All cards have been chipped!")
        return

    total = len(unchipped)
    print(f"\n{total} unchipped cards found:\n")

    # Show summary by faction
    from collections import Counter
    faction_counts = Counter(faction for faction, _, _ in unchipped)
    for faction in FACTIONS:
        count = faction_counts.get(faction, 0)
        if count > 0:
            print(f"  {faction}: {count} cards")
    print()

    # Signal handling for clean shutdown
    shutting_down = False

    def _shutdown(signum, frame):
        nonlocal shutting_down
        if shutting_down:
            print("\nForce quit.")
            sys.exit(1)
        shutting_down = True
        print("\nShutting down (Ctrl+C again to force)...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    current_faction = None
    written = 0
    skipped = 0

    try:
        for i, (faction, filepath, data) in enumerate(unchipped, 1):
            if shutting_down:
                break

            if faction != current_faction:
                current_faction = faction
                fc = FACTION_COLORS.get(faction, "")
                fe = E_FACTION.get(faction, "")
                print(f"\n{'='*60}")
                print(f"  {fe} {fc}{BOLD}{faction}{RESET} ({faction_counts[faction]} cards)")
                print(f"{'='*60}")

            card_faction = data.get("faction", "—")
            fc = FACTION_COLORS.get(card_faction, "")
            fe = E_FACTION.get(card_faction, "")
            name = data.get("name", os.path.basename(filepath))
            is_starter = data.get("starter", False)

            print(f"\n  [{i}/{total}] {fc}{BOLD}{name}{RESET}")
            print(f"  {'─' * 40}")

            # Helper: emoji + right-aligned label + value
            # Each emoji renders ~2 terminal columns; spaces are 1 column.
            # Target: emoji block + label should fill 16 visual columns.
            LABEL_COL = 16
            def _emoji_width(s):
                """Estimate visual width: each non-space char is 2 cols (emoji), space is 1."""
                w = 0
                for ch in s:
                    w += 1 if ch == ' ' else 2
                return w

            def _row(emoji, label, value):
                ew = _emoji_width(emoji)
                pad = max(LABEL_COL - ew - 1, 0)  # -1 for space after emoji
                print(f"  {emoji} {label:>{pad}s}   {value}")

            _row(fe, "Faction:", f"{fc}{card_faction}{RESET}")
            if data.get("strength") is not None:
                _row(E_STRENGTH, "Strength:", str(data["strength"]))
            if data.get("specialty"):
                se = E_SPECIALTY.get(data["specialty"], "❓")
                _row(se, "Specialty:", data["specialty"])
            if data.get("abilities"):
                emojis = " ".join(E_ABILITY.get(a, "❓") for a in data["abilities"])
                _row(emojis, "Abilities:", ", ".join(data["abilities"]))
            if data.get("ability"):
                ae = E_ABILITY.get(data["ability"], "❓")
                _row(ae, "Ability:", data["ability"])
            if data.get("ranges"):
                emojis = " ".join(E_ROW.get(r, "❓") for r in data["ranges"])
                _row(emojis, "Ranges:", ", ".join(data["ranges"]))
            if data.get("leader"):
                leader = data["leader"]
                if leader.get("instructions"):
                    _row(E_LEADER, "Leader:", leader["instructions"])
                if leader.get("commander_ranges"):
                    _row("📯", "Cmd Rows:", ", ".join(leader["commander_ranges"]))
                if leader.get("weather_ranges"):
                    _row("🌧️", "Wth Rows:", ", ".join(leader["weather_ranges"]))
            if is_starter:
                _row(E_STARTER, "Owner:", "(starter)")
            elif data.get("owner"):
                _row(E_OWNER, "Owner:", data["owner"])
            else:
                _row(E_OWNER, "Owner:", "(unowned)")
            _row(E_FILE, "File:", os.path.basename(filepath))

            # Non-starter unowned cards — must assign an owner or skip
            if not is_starter and not data.get("owner"):
                owner = prompt_owner(name, owners)
                if owner is None:
                    print(f"  {RED}⏭ Skipping {name}.{RESET}")
                    log.info("Skipped %s (no owner selected)", name)
                    skipped += 1
                    continue
                if owner:
                    data["owner"] = owner
                    with open(filepath, "w") as f:
                        json.dump(data, f, indent=4)
                    print(f"  {GREEN}Owner set to: {owner}{RESET}")
                    log.info("Set owner=%s for %s", owner, name)
                    if owner not in owners:
                        owners.append(owner)
                        owners.sort()

            # Announce the card via TTS
            _speak(_describe_card(data))

            print(f"\n  Place card on writer, writing automatically...")

            log.info("Writing [%d/%d] %s from %s", i, total, name, os.path.basename(filepath))

            # Load as card Message and write (with Esc to skip)
            card = gwent.cards.util.read_card(filepath)
            rfid = None
            skip_pressed = False

            import threading
            import select

            write_result = [None, None]  # [rfid, error]

            def _do_write():
                try:
                    write_result[0] = write_card(card, filepath)
                except Exception as e:
                    write_result[1] = e

            write_thread = threading.Thread(target=_do_write, daemon=True)
            write_thread.start()

            # Poll for Esc while write is in progress
            while write_thread.is_alive():
                write_thread.join(timeout=0.2)
                # Check for Esc key (non-blocking stdin read)
                try:
                    if select.select([sys.stdin], [], [], 0)[0]:
                        ch = sys.stdin.read(1)
                        if ch == "\x1b":  # Esc
                            skip_pressed = True
                            break
                except Exception:
                    pass

            if skip_pressed:
                print(f"\n  {RED}⏭ Skipping {name} (Esc pressed).{RESET}")
                log.info("Skipped %s (Esc pressed during write)", name)
                skipped += 1
                continue

            rfid = write_result[0]
            error = write_result[1]

            if error:
                print(f"\n  {RED}✗ Error writing {name}: {error}{RESET}")
                log.error("Error writing %s: %s", name, error)

            if rfid is not None:
                _play_card_fx()
                print(f"\n  {GREEN}✓ {name} written successfully! RFID: {rfid}{RESET}\a")
                _speak("Write successful, next card is")
                log.info("✓ %s written. RFID: %s", name, rfid)
                written += 1
            else:
                if not error:
                    print(f"\n  {RED}✗ FAILED to write {name}. Skipping.{RESET}")
                log.warning("✗ FAILED %s. Skipping.", name)
                skipped += 1
    except KeyboardInterrupt:
        print("\nAborted by user.")
        log.info("Aborted by user.")

    print(f"\n{'='*60}")
    print(f"  Done! Written: {written}, Skipped: {skipped}, Total: {total}")
    print(f"{'='*60}\n")
    log.info("Done! Written: %d, Skipped: %d, Total: %d", written, skipped, total)


if __name__ == "__main__":
    main()
