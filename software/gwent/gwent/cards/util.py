"""Card utility functions — works from JSON files in data/cards/."""

import json
import os
import random

import gwent.messaging.card

from gwent.utils.logging import get_logger, configure_logging, INFO

log = get_logger("card.util")

CARDS_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "cards"
))


def read_card(f: str) -> gwent.messaging.card.Message:
    """Load a card from a JSON file."""
    with open(f) as fb:
        details = json.load(fb)
        return gwent.messaging.card.Message.from_properties(details)


def load_all_cards():
    """Load all card JSON files. Returns list of (filepath, card_data) tuples."""
    cards = []
    for faction_dir in sorted(os.listdir(CARDS_DIR)):
        dirpath = os.path.join(CARDS_DIR, faction_dir)
        if not os.path.isdir(dirpath) or faction_dir in ("tmp",):
            continue
        for fname in sorted(os.listdir(dirpath)):
            if not fname.endswith(".json"):
                continue
            filepath = os.path.join(dirpath, fname)
            with open(filepath) as f:
                data = json.load(f)
            cards.append((filepath, data))
    return cards


def load_card_by_name(name):
    """Load a card from the data directory by name (prefix match before ':').
    Returns a Card Message or None."""
    for _, data in load_all_cards():
        card_name = data.get("name", "")
        base_name = card_name.split(":")[0].strip()
        if base_name == name or card_name == name:
            return gwent.messaging.card.Message.from_properties(data)
    return None


def random_card() -> gwent.messaging.card.Message:
    """Return a random card from the JSON database."""
    cards = load_all_cards()
    if not cards:
        raise RuntimeError("No card files found")
    filepath, data = random.choice(cards)
    return gwent.messaging.card.Message.from_properties(data)


def validate_cards() -> gwent.messaging.card.Message:
    """Validate all card JSON files. Returns the biggest card."""
    cards = load_all_cards()
    biggest_card = None
    total = 0
    starters_by_faction = {}
    cards_by_owner = {}

    for filepath, data in cards:
        total += 1
        card = gwent.messaging.card.Message.from_properties(data)
        faction = data.get("faction", "Unknown")

        if data.get("starter"):
            starters_by_faction.setdefault(faction, []).append(card.name)

        owner = data.get("owner", "")
        if owner:
            cards_by_owner.setdefault(owner, {}).setdefault(faction, []).append(card.name)

        if biggest_card is None or card.bytes > biggest_card.bytes:
            biggest_card = card

    for faction, starters in sorted(starters_by_faction.items()):
        log.info({"action": "starters", "faction": faction, "count": len(starters)})

    for owner, factions in sorted(cards_by_owner.items()):
        total_owned = sum(len(c) for c in factions.values())
        log.info({"owner": owner, "total": total_owned})
        for faction, names in sorted(factions.items()):
            log.info({"owner": owner, "faction": faction, "count": len(names)})

    log.info({
        "action": "validate_complete",
        "total_cards": total,
        "biggest_card": biggest_card.name if biggest_card else None,
        "biggest_bytes": biggest_card.bytes if biggest_card else 0,
    })

    return biggest_card


# CLI entry points

def validate_cards_main():
    """Command-line entry point for validating cards."""
    configure_logging(level=INFO, log_file="/tmp/logs/cards_util.log")
    print("Validating cards...")
    biggest_card = validate_cards()
    print(f"Total cards validated. Biggest card: {biggest_card.name} ({biggest_card.bytes} bytes)")
    return 0


def read_card_main():
    """Command-line entry point for reading a card file."""
    import sys
    configure_logging(level=INFO, log_file="/tmp/logs/cards_util.log")

    if len(sys.argv) < 2:
        print("Usage: read-card-file <path_to_card_file>")
        return 1

    try:
        card = read_card(sys.argv[1])
        print(f"Card: {card.name}")
        print(f"Faction: {card.faction}")
        print(f"Details: {card.body_pretty}")
        return 0
    except Exception as e:
        print(f"Error reading card file: {e}")
        return 1


def random_card_main():
    """Command-line entry point for getting a random card."""
    configure_logging(level=INFO, log_file="/tmp/logs/cards_util.log")
    card = random_card()
    print(f"Random Card: {card.name}")
    print(f"Faction: {card.faction}")
    print(f"Details: {card.body_pretty}")
    return 0
