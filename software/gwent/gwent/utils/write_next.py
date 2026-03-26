#!/usr/bin/env python3
"""Write the next unchipped card to an RFID tag.

Iterates through all card JSON files by faction, finds cards without an
"rfid" field, and writes them one at a time. Completes an entire faction
before moving to the next. 5 second delay between cards to swap.
"""

import json
import os
import signal
import sys
import time

from gwent.utils.logging import configure_logging, get_logger, DEBUG

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


def main():
    configure_logging(level=DEBUG, log_file="/tmp/logs/write_next.log")
    log = get_logger("write_next")

    # Lazy import — hardware init happens here
    import gwent.cards.util
    from gwent.poc.util.read_write_cards import write_card

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
    try:
        for i, (faction, filepath, data) in enumerate(unchipped, 1):
            if shutting_down:
                break

            if faction != current_faction:
                current_faction = faction
                print(f"\n{'='*60}")
                print(f"  FACTION: {faction} ({faction_counts[faction]} cards)")
                print(f"{'='*60}")

            name = data.get("name", os.path.basename(filepath))

            print(f"\n  [{i}/{total}] {name}")
            print(f"  {'─' * 40}")
            print(f"  Faction:   {data.get('faction', '—')}")
            if data.get("strength") is not None:
                print(f"  Strength:  {data['strength']}")
            if data.get("specialty"):
                print(f"  Specialty: {data['specialty']}")
            if data.get("abilities"):
                print(f"  Abilities: {', '.join(data['abilities'])}")
            if data.get("ability"):
                print(f"  Ability:   {data['ability']}")
            if data.get("ranges"):
                print(f"  Ranges:    {', '.join(data['ranges'])}")
            if data.get("leader"):
                leader = data["leader"]
                if leader.get("instructions"):
                    print(f"  Leader:    {leader['instructions']}")
                if leader.get("commander_ranges"):
                    print(f"  Cmd Rows:  {', '.join(leader['commander_ranges'])}")
                if leader.get("weather_ranges"):
                    print(f"  Wth Rows:  {', '.join(leader['weather_ranges'])}")
            if data.get("owner"):
                print(f"  Owner:     {data['owner']}")
            if data.get("starter"):
                print(f"  Starter:   yes")
            print(f"  File:      {os.path.basename(filepath)}")
            print(f"\n  Place card on writer, writing automatically...")

            log.info("Writing [%d/%d] %s from %s", i, total, name, os.path.basename(filepath))

            # Load as card Message and write
            card = gwent.cards.util.read_card(filepath)
            rfid = write_card(card, filepath)

            if rfid is not None:
                print(f"\n  ✓ {name} written successfully! RFID: {rfid}")
                print(f"  Waiting 5 seconds — swap card for next...")
                log.info("✓ %s written. RFID: %s", name, rfid)
                time.sleep(5)
            else:
                print(f"\n  ✗ FAILED to write {name}. Skipping.")
                log.warning("✗ FAILED %s. Skipping.", name)
                time.sleep(2)
    except KeyboardInterrupt:
        print("\nAborted by user.")
        log.info("Aborted by user.")
        return

    print(f"\n{'='*60}")
    print(f"  Done! All {total} cards processed.")
    print(f"{'='*60}\n")
    log.info("Done! All %d cards processed.", total)


if __name__ == "__main__":
    main()
