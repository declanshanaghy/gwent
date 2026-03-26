"""Deck persistence — save, load, and select pre-built decks.

Owned decks are stored as JSON files under data/decks/{owner_slug}/{faction_slug}.json.
Starter decks are built dynamically from data/cards/{Faction}/*.json (no disk files).
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

# Canonical faction name → card data directory name
FACTION_TO_DIR = {
    "Monsters": "Monsters",
    "Nilfgaardian": "Nilfgaardian",
    "Northern Realms": "NorthernRealms",
    "Scoia'tael": "Scoiatael",
    "Skellige": "Skellige",
}

# Reverse: directory name → canonical faction name
DIR_TO_FACTION = {v: k for k, v in FACTION_TO_DIR.items()}


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


def load_starter_cards(faction):
    """Load all starter cards for a faction by scanning card data files.

    Reads data/cards/{FactionDir}/*.json and returns cards with starter: true.

    Args:
        faction: Canonical faction name (e.g. "Northern Realms", "Scoia'tael").

    Returns:
        List of card Messages, or empty list if faction not found.
    """
    faction_dir = FACTION_TO_DIR.get(faction)
    if not faction_dir:
        log.warning(f"Unknown faction: {faction}")
        return []

    cards_path = os.path.join(CARDS_DIR, faction_dir)
    if not os.path.isdir(cards_path):
        log.warning(f"Card directory not found: {cards_path}")
        return []

    cards = []
    for fname in os.listdir(cards_path):
        if not fname.endswith(".json"):
            continue
        filepath = os.path.join(cards_path, fname)
        try:
            with open(filepath) as f:
                card_data = json.load(f)
            if card_data.get("starter"):
                cards.append(
                    gwent.messaging.card.Message.from_properties(card_data))
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Skipping invalid card file {filepath}: {e}")

    log.info(f"Loaded {len(cards)} starter cards for {faction}")
    return cards


def _list_starter_factions():
    """List all factions that have starter cards.

    Returns:
        List of canonical faction names.
    """
    factions = []
    for faction, dirname in FACTION_TO_DIR.items():
        cards_path = os.path.join(CARDS_DIR, dirname)
        if not os.path.isdir(cards_path):
            continue
        # Check if at least one card has starter: true
        for fname in os.listdir(cards_path):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(cards_path, fname)) as f:
                    card_data = json.load(f)
                if card_data.get("starter"):
                    factions.append(faction)
                    break
            except (json.JSONDecodeError, KeyError):
                continue
    return factions


def list_decks():
    """List all available decks (owned + starter).

    Returns:
        List of (owner, faction, source) tuples.
        source is a filepath for owned decks, or "starter" for starter decks.
    """
    results = []

    # Owned decks from disk
    if os.path.isdir(DECKS_DIR):
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

    # Virtual starter deck entries
    for faction in _list_starter_factions():
        results.append((STARTER_OWNER, faction, STARTER_OWNER))

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
    for owner, faction, source in all_entries:
        by_faction.setdefault(faction, []).append((owner, source))

    factions = list(by_faction.keys())
    if len(factions) < 2:
        return None

    # Pick 2 different factions at random
    f1, f2 = random.sample(factions, 2)

    def _load_entry(faction, entries):
        # Prefer owned decks over starter decks
        owned = [(o, s) for o, s in entries if s != STARTER_OWNER]
        pick_from = owned if owned else entries
        owner, source = random.choice(pick_from)
        if source == STARTER_OWNER:
            return {
                "owner": STARTER_OWNER,
                "faction": faction,
                "cards": load_starter_cards(faction),
            }
        return load_deck(source)

    return _load_entry(f1, by_faction[f1]), _load_entry(f2, by_faction[f2])
