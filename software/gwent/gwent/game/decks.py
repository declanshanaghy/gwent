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


def pick_random_matchup(owner_filter=None):
    """Pick two different factions + an owner for each, WITHOUT loading cards.

    Lightweight counterpart to pick_two_random_decks — used by the startup
    wizard to preview/re-roll a matchup cheaply (no card I/O until START).

    Returns:
        ((faction1, owner1), (faction2, owner2)) or None if <2 factions.
    """
    all_entries = list_decks(owner_filter=owner_filter)
    by_faction = {}
    for owner, faction in all_entries:
        by_faction.setdefault(faction, []).append(owner)

    factions = list(by_faction.keys())
    if len(factions) < 2:
        return None

    f1, f2 = random.sample(factions, 2)

    def _pick_owner(faction):
        owners = by_faction[faction]
        owned = [o for o in owners if o != STARTER_OWNER]
        return random.choice(owned if owned else owners)

    return (f1, _pick_owner(f1)), (f2, _pick_owner(f2))


def build_deck(faction, owner):
    """Load the card list for a (faction, owner) pair.

    Returns list of card Messages — starter cards when owner is STARTER_OWNER,
    otherwise that owner's cards for the faction.
    """
    if owner == STARTER_OWNER:
        return load_starter_cards(faction)
    return load_owner_cards(faction, owner)


# -----------------------------------------------------------------------------
# Image-card index + dynamic random decks (New Game wizard)
# -----------------------------------------------------------------------------

_IMAGE_CARDS = None  # {faction: {"leaders": [dict], "units": [dict]}}


def _card_has_image(data, filepath):
    """True if the card declares an image file that exists on disk."""
    img = data.get("image")
    if not img:
        return False
    return os.path.exists(os.path.normpath(os.path.join(
        os.path.dirname(filepath), img)))


def preload_image_cards(force=False):
    """Build (and cache) an index of every card with art, grouped by faction.

    Called once at server startup so the New Game wizard can pick random decks
    instantly. Returns {faction: {"leaders": [...], "units": [...]}} of raw
    card dicts (only cards whose image file exists).
    """
    global _IMAGE_CARDS
    if _IMAGE_CARDS is not None and not force:
        return _IMAGE_CARDS
    idx = {}
    for faction in FACTION_TO_DIR:
        leaders, units = [], []
        for filepath, data in _load_faction_cards(faction):
            if not _card_has_image(data, filepath):
                continue
            (leaders if data.get("specialty") == "leader" else units).append(data)
        idx[faction] = {"leaders": leaders, "units": units}
    _IMAGE_CARDS = idx
    log.info("preloaded image cards: " + ", ".join(
        f"{f}:{len(v['leaders'])}L/{len(v['units'])}U" for f, v in idx.items()))
    return idx


def image_factions():
    """Factions that have at least one image leader and one image unit."""
    idx = preload_image_cards()
    return [f for f, v in idx.items() if v["leaders"] and v["units"]]


def pick_random_side(faction, deck_size=20):
    """Build one side dynamically: a random image leader + `deck_size` random
    image units from `faction`. Returns a dict with display fields and the full
    `deck` (raw card dicts incl. leader). None if the faction lacks art."""
    idx = preload_image_cards()
    pool = idx.get(faction)
    if not pool or not pool["leaders"] or not pool["units"]:
        return None
    leader = random.choice(pool["leaders"])
    units = pool["units"]
    chosen = random.sample(units, min(deck_size, len(units)))
    strength = sum(int(c["strength"]) for c in chosen
                   if isinstance(c.get("strength"), (int, float)))
    return {
        "faction": faction,
        "leader": leader.get("name", ""),
        "leader_card": {"name": leader.get("name", ""), "faction": faction,
                        "image": leader.get("image")},
        "strength": strength,
        "count": len(chosen),
        "deck": [leader] + chosen,
    }


def pick_random_matchup_sides(deck_size=20):
    """Two independently-built sides with DIFFERENT factions (avoids rfid
    collisions on the board). Returns (side1, side2) or None."""
    factions = image_factions()
    if len(factions) < 2:
        return None
    f1, f2 = random.sample(factions, 2)
    s1 = pick_random_side(f1, deck_size)
    s2 = pick_random_side(f2, deck_size)
    if not s1 or not s2:
        return None
    return s1, s2


def messages_from_dicts(dicts):
    """Convert raw card dicts to card Messages, skipping any that fail schema
    validation (so one bad card can't sink the whole deck)."""
    out = []
    for d in dicts or []:
        try:
            out.append(gwent.messaging.card.Message.from_properties(d))
        except Exception as e:
            log.warning(f"skipping invalid card {d.get('name')!r}: {e}")
    return out


def deck_summary(faction, owner):
    """Lightweight preview of a (faction, owner) deck for the New Game wizard.

    Reads raw card JSON (no Message/schema validation, so a card missing a
    required field can't crash the preview). Returns the deck's leader, a
    minimal leader card dict for image resolution, the summed strength of all
    cards, and the card count.
    """
    cards = []
    for _fp, data in _load_faction_cards(faction):
        if owner == STARTER_OWNER:
            if data.get("starter"):
                cards.append(data)
        elif data.get("owner") == owner:
            cards.append(data)

    total = 0
    for c in cards:
        s = c.get("strength")
        if isinstance(s, (int, float)):
            total += int(s)

    leader = next((c for c in cards if c.get("specialty") == "leader"), None)
    if leader is None or not leader.get("image"):
        # Owners rarely own a leader card (leaders are shared/starter and
        # supplemented at deal time) — fall back to the faction's leader card.
        # Prefer one that actually has art (ideally the starter leader) so the
        # wizard never shows a blank image (e.g. Skellige's image-less "King
        # Bran" → use "Crach an Craite" instead).
        faction_leaders = [data for _fp, data in _load_faction_cards(faction)
                           if data.get("specialty") == "leader"]
        leader = (
            next((c for c in faction_leaders
                  if c.get("image") and c.get("starter")), None)
            or next((c for c in faction_leaders if c.get("image")), None)
            or leader
            or (faction_leaders[0] if faction_leaders else None))
    leader_card = None
    if leader:
        leader_card = {
            "name": leader.get("name", ""),
            "faction": faction,
            "image": leader.get("image"),
        }

    return {
        "leader": leader.get("name", "") if leader else "",
        "leader_card": leader_card,
        "strength": total,
        "count": len(cards),
    }
