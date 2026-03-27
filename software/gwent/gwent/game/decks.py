"""Deck management — derive decks from card ownership in data/cards/.

A player's deck for a faction is the set of cards in data/cards/{Faction}/*.json
where card.owner matches the player's name. Starter cards (starter: true, no owner)
form the base deck available to all players.

No separate deck files — ownership is the source of truth.
"""

import json
import os
import random
import re

import gwent.messaging.card
from gwent.utils.logging import get_logger

log = get_logger("gwent.game.decks")

CARDS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "cards"))

STARTER_OWNER = "starter"

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
    """Convert a name to a filesystem-safe slug (lowercase, no special chars)."""
    s = re.sub(r'[^a-zA-Z0-9]', '', name)
    return s.lower()


def _load_faction_cards(faction):
    """Load all card JSONs for a faction.

    Returns list of (filepath, card_data_dict) tuples.
    """
    faction_dir = FACTION_TO_DIR.get(faction)
    if not faction_dir:
        return []

    cards_path = os.path.join(CARDS_DIR, faction_dir)
    if not os.path.isdir(cards_path):
        return []

    results = []
    for fname in os.listdir(cards_path):
        if not fname.endswith(".json"):
            continue
        filepath = os.path.join(cards_path, fname)
        try:
            with open(filepath) as f:
                data = json.load(f)
            results.append((filepath, data))
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Skipping invalid card file {filepath}: {e}")

    return results


def load_starter_cards(faction):
    """Load all starter cards for a faction.

    Returns list of card Messages with starter: true.
    """
    cards = []
    for filepath, data in _load_faction_cards(faction):
        if data.get("starter"):
            cards.append(gwent.messaging.card.Message.from_properties(data))

    log.info(f"Loaded {len(cards)} starter cards for {faction}")
    return cards


def load_owner_cards(faction, owner):
    """Load all cards owned by a specific player for a faction.

    Returns list of card Messages.
    """
    cards = []
    for filepath, data in _load_faction_cards(faction):
        if data.get("owner") == owner:
            cards.append(gwent.messaging.card.Message.from_properties(data))

    log.info(f"Loaded {len(cards)} cards for {owner} in {faction}")
    return cards


def save_deck(owner, faction, cards):
    """Save a deck by setting the owner field on each card's JSON file.

    Args:
        owner: Owner name (e.g. "Declan Shanaghy").
        faction: Faction name (e.g. "Northern Realms").
        cards: List of card Message objects.

    Returns:
        Number of cards updated.
    """
    updated = 0
    faction_dir = FACTION_TO_DIR.get(faction)
    if not faction_dir:
        log.warning(f"Unknown faction: {faction}")
        return 0

    cards_path = os.path.join(CARDS_DIR, faction_dir)
    card_rfids = {c.rfid for c in cards if c.rfid}

    for fname in os.listdir(cards_path):
        if not fname.endswith(".json"):
            continue
        filepath = os.path.join(cards_path, fname)
        try:
            with open(filepath) as f:
                data = json.load(f)

            rfid = data.get("rfid")
            if rfid and rfid in card_rfids:
                if data.get("owner") != owner:
                    data["owner"] = owner
                    with open(filepath, "w") as f:
                        json.dump(data, f, indent=4)
                    updated += 1
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Skipping {filepath}: {e}")

    log.info(f"Deck saved: set owner={owner} on {updated} cards in {faction}")
    return updated


def list_decks():
    """List all available decks derived from card ownership.

    Scans all card JSONs and groups by owner + faction.

    Returns:
        List of (owner, faction) tuples.
        Includes (STARTER_OWNER, faction) for factions with starter cards.
    """
    results = []
    seen = set()

    for faction, dirname in FACTION_TO_DIR.items():
        has_starters = False

        for filepath, data in _load_faction_cards(faction):
            owner = data.get("owner", "")
            if data.get("starter"):
                has_starters = True

            if owner:
                key = (owner, faction)
                if key not in seen:
                    seen.add(key)
                    results.append((owner, faction))

        if has_starters:
            results.append((STARTER_OWNER, faction))

    return results


def _match_owner(card_data, owner_filter):
    """Check if a card matches the owner filter by name or nickname."""
    if not owner_filter:
        return True
    filt = owner_filter.lower()
    name = (card_data.get("owner") or "").lower()
    nickname = (card_data.get("owner_nickname") or "").lower()
    return filt == name or filt == nickname


def list_decks(owner_filter=None):
    """List all available decks derived from card ownership.

    Args:
        owner_filter: If set, only include decks for this owner (matches name or nickname).

    Returns:
        List of (owner, faction) tuples.
        Includes (STARTER_OWNER, faction) for factions with starter cards.
    """
    results = []
    seen = set()

    for faction, dirname in FACTION_TO_DIR.items():
        has_starters = False

        for filepath, data in _load_faction_cards(faction):
            if data.get("starter"):
                has_starters = True

            owner = data.get("owner", "")
            if owner and _match_owner(data, owner_filter):
                key = (owner, faction)
                if key not in seen:
                    seen.add(key)
                    results.append((owner, faction))

        if has_starters:
            results.append((STARTER_OWNER, faction))

    return results


def pick_two_random_decks(owner_filter=None):
    """Select 2 random decks with different factions.

    Args:
        owner_filter: If set, only use decks owned by this player (name or nickname).

    Returns:
        Tuple of (deck1_dict, deck2_dict) or None if not enough valid decks.
        Each dict has keys: owner, faction, cards.
    """
    all_entries = list_decks(owner_filter=owner_filter)
    if len(all_entries) < 2:
        return None

    # Group by faction
    by_faction = {}
    for owner, faction in all_entries:
        by_faction.setdefault(faction, []).append(owner)

    factions = list(by_faction.keys())
    if len(factions) < 2:
        return None

    f1, f2 = random.sample(factions, 2)

    def _build_deck(faction, owners):
        # Prefer owned decks over starter
        owned = [o for o in owners if o != STARTER_OWNER]
        pick_from = owned if owned else owners
        owner = random.choice(pick_from)

        if owner == STARTER_OWNER:
            cards = load_starter_cards(faction)
        else:
            cards = load_owner_cards(faction, owner)

        return {
            "owner": owner,
            "faction": faction,
            "cards": cards,
        }

    return _build_deck(f1, by_faction[f1]), _build_deck(f2, by_faction[f2])
