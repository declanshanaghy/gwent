"""Deck persistence — save, load, and select pre-built decks.

Decks are stored as JSON files under software/data/decks/{owner_slug}/{faction_slug}.json.
"""

import json
import os
import random
import re
from datetime import datetime, timezone

import gwent.messaging.card
from gwent.utils.logging import get_logger

log = get_logger("gwent.game.decks")

CARDS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "cards"))

DECKS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "decks"))

STARTER_OWNER = "starter"
DECK_VERSION = 1


def slugify(name):
    """Convert a name to a filesystem-safe slug (lowercase, no spaces/special chars).

    Strips all non-alphanumeric characters so that 'Declan Shanaghy' and
    'DeclanShanaghy' both produce 'declanshanaghy'.
    """
    s = re.sub(r'[^a-zA-Z0-9]', '', name)
    return s.lower()


def _cards_to_dicts(cards):
    return [c._instance for c in cards] if cards else []


def _dicts_to_cards(dicts):
    if not dicts:
        return []
    return [gwent.messaging.card.Message.from_properties(d) for d in dicts]


def save_deck(owner, faction, cards):
    """Save a deck to disk.

    Args:
        owner: Owner name (e.g. "Declan Shanaghy").
        faction: Faction name (e.g. "Northern Realms").
        cards: List of card Message objects.

    Returns:
        The filepath written.
    """
    deck = {
        "version": DECK_VERSION,
        "owner": owner,
        "faction": faction,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cards": _cards_to_dicts(cards),
    }

    dirpath = os.path.join(DECKS_DIR, slugify(owner))
    os.makedirs(dirpath, exist_ok=True)
    filepath = os.path.join(dirpath, slugify(faction) + ".json")

    with open(filepath, "w") as f:
        json.dump(deck, f, indent=2)

    log.info(f"Deck saved: {filepath} ({len(cards)} cards)")
    return filepath


def load_deck(filepath):
    """Load a deck from a JSON file.

    Returns:
        Dict with keys: owner, faction, cards (list of card Messages).
    """
    with open(filepath) as f:
        data = json.load(f)

    cards = _dicts_to_cards(data.get("cards", []))
    return {
        "owner": data["owner"],
        "faction": data["faction"],
        "cards": cards,
    }


def list_decks():
    """List all saved decks.

    Returns:
        List of (owner, faction, filepath) tuples.
    """
    results = []
    if not os.path.isdir(DECKS_DIR):
        return results

    for owner_dir in os.listdir(DECKS_DIR):
        owner_path = os.path.join(DECKS_DIR, owner_dir)
        if not os.path.isdir(owner_path):
            continue
        for fname in os.listdir(owner_path):
            if not fname.endswith(".json"):
                continue
            filepath = os.path.join(owner_path, fname)
            try:
                with open(filepath) as f:
                    data = json.load(f)
                results.append((data["owner"], data["faction"], filepath))
            except (json.JSONDecodeError, KeyError) as e:
                log.warning(f"Skipping invalid deck file {filepath}: {e}")

    return results


def pick_two_random_decks():
    """Select 2 random saved decks with different factions.

    Returns:
        Tuple of (deck1_dict, deck2_dict) or None if not enough valid decks.
        Each dict has keys: owner, faction, cards.
    """
    all_entries = list_decks()
    if len(all_entries) < 2:
        return None

    # Group by faction
    by_faction = {}
    for owner, faction, filepath in all_entries:
        by_faction.setdefault(faction, []).append(filepath)

    factions = list(by_faction.keys())
    if len(factions) < 2:
        return None

    # Pick 2 different factions at random
    f1, f2 = random.sample(factions, 2)
    path1 = random.choice(by_faction[f1])
    path2 = random.choice(by_faction[f2])

    return load_deck(path1), load_deck(path2)


def load_starter_cards(faction):
    """Load all starter cards for a given faction.

    Returns:
        List of card Messages, or empty list if no starter deck found.
    """
    path = os.path.join(DECKS_DIR, STARTER_OWNER, slugify(faction) + ".json")
    if not os.path.exists(path):
        log.warning(f"No starter deck for {faction}: {path}")
        return []
    deck = load_deck(path)
    return deck['cards']


def ensure_starter_decks():
    """Generate starter deck files from card data if they don't already exist.

    Scans data/cards/{Faction}/*.json for cards with starter: true,
    groups by faction, and saves to data/decks/starter/{faction_slug}.json.
    """
    if not os.path.isdir(CARDS_DIR):
        log.warning(f"Cards directory not found: {CARDS_DIR}")
        return

    # Collect starter cards per faction
    by_faction = {}
    for faction_dir in os.listdir(CARDS_DIR):
        faction_path = os.path.join(CARDS_DIR, faction_dir)
        if not os.path.isdir(faction_path):
            continue
        for fname in os.listdir(faction_path):
            if not fname.endswith(".json"):
                continue
            filepath = os.path.join(faction_path, fname)
            try:
                with open(filepath) as f:
                    card_data = json.load(f)
                if card_data.get("starter"):
                    faction = card_data.get("faction", faction_dir)
                    by_faction.setdefault(faction, []).append(card_data)
            except (json.JSONDecodeError, KeyError) as e:
                log.warning(f"Skipping invalid card file {filepath}: {e}")

    # Save a starter deck per faction
    starter_dir = os.path.join(DECKS_DIR, STARTER_OWNER)
    os.makedirs(starter_dir, exist_ok=True)

    for faction, cards_data in by_faction.items():
        deck_path = os.path.join(starter_dir, slugify(faction) + ".json")
        if os.path.exists(deck_path):
            continue

        deck = {
            "version": DECK_VERSION,
            "owner": STARTER_OWNER,
            "faction": faction,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cards": cards_data,
        }
        with open(deck_path, "w") as f:
            json.dump(deck, f, indent=2)
        log.info(f"Starter deck created: {deck_path} ({len(cards_data)} cards)")
