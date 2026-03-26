#!/usr/bin/env python3
"""Import Gwent cards from the GWENTcards public database.

Reads JSON files from the Rowan-Paul/GWENTcards repo and creates/updates
card JSON files in software/data/cards/. Fuzzy-matches existing cards to
avoid duplicates.

Usage:
    import_cards --source /tmp/GWENTcards/public
    import_cards --source /tmp/GWENTcards/public --dry-run
"""

import argparse
import json
import os
import re
import sys
import unicodedata

CARDS_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "cards"
))

# Source file → our faction name
SOURCE_FILES = {
    "monsters.json": "Monsters",
    "nilfgaard.json": "Nilfgaardian",
    "northern-realms.json": "Northern Realms",
    "scoiatael.json": "Scoia'tael",
    "skellige.json": "Skellige",
    "neutral.json": "Neutral",
}

# Faction name → directory name
FACTION_TO_DIR = {
    "Monsters": "Monsters",
    "Nilfgaardian": "Nilfgaardian",
    "Northern Realms": "NorthernRealms",
    "Scoia'tael": "Scoiatael",
    "Skellige": "Skellige",
    "Neutral": "Neutral",
}

# Ability name mapping (source → ours)
ABILITY_MAP = {
    "Muster": "muster",
    "Tight Bond": "bond",
    "tight bond": "bond",
    "Medic": "medic",
    "medic": "medic",
    "Morale boost": "morale",
    "morale boost": "morale",
    "spy": "spy",
    "Spy": "spy",
}

# Weather card → affected rows
WEATHER_ROWS = {
    "Biting Frost": ["close"],
    "Impenetrable Fog": ["ranged"],
    "Torrential Rain": ["siege"],
    "Clear Weather": ["close", "ranged", "siege"],
    "Skellige Storm": ["ranged", "siege"],
}


def normalize_name(name):
    """Normalize a card name for fuzzy matching."""
    s = unicodedata.normalize("NFKD", name)
    # Remove variant suffixes like ": 1", " (1 of 3)"
    s = re.sub(r'\s*[:(]\s*\d.*$', '', s)
    # Normalize separators
    s = s.replace(" - ", " ").replace(": ", " ").replace(":", " ")
    # Lowercase, strip, collapse whitespace
    s = re.sub(r'\s+', ' ', s.lower().strip())
    return s


def fs_safe(name):
    """Convert a card name to a filesystem-safe filename."""
    s = name.replace("'", "").replace(":", "").replace(",", "")
    s = re.sub(r'[^a-zA-Z0-9]', '', s.title().replace(" ", ""))
    return s


def load_existing_cards():
    """Load all existing card JSONs keyed by normalized name → list of (filepath, data)."""
    cards = {}
    for faction_dir in os.listdir(CARDS_DIR):
        dirpath = os.path.join(CARDS_DIR, faction_dir)
        if not os.path.isdir(dirpath) or faction_dir in ("tmp",):
            continue
        for fname in os.listdir(dirpath):
            if not fname.endswith(".json"):
                continue
            filepath = os.path.join(dirpath, fname)
            with open(filepath) as f:
                data = json.load(f)
            key = normalize_name(data.get("name", fname))
            cards.setdefault(key, []).append((filepath, data))
    return cards


def convert_card(src, faction):
    """Convert a GWENTcards card dict to our schema."""
    card = {"kind": "card", "faction": faction}

    card["name"] = src["name"]

    # Strength
    if "strength" in src and src["strength"] is not None:
        card["strength"] = src["strength"]

    # Determine specialty and abilities
    src_abilities = src.get("abilities", [])
    abilities = []
    specialty = None

    for a in src_abilities:
        if a == "Hero":
            specialty = "hero"
        elif a in ABILITY_MAP:
            abilities.append(ABILITY_MAP[a])

    # Effect-based specialties (Neutral cards)
    effect = src.get("effect", "")
    if effect == "weather":
        specialty = "weather"
    elif effect == "scorch":
        if "strength" in src and src.get("strength"):
            # Unit card with scorch ability (like Villentretenmerth)
            abilities.append("scorch")
        else:
            specialty = "scorch"
    elif effect == "decoy":
        specialty = "decoy"
    elif effect == "commander's horn":
        if "strength" in src and src.get("strength"):
            # Unit card with commander ability (like Dandelion)
            abilities.append("commander")
        else:
            specialty = "commander"
    elif effect == "summon avenger":
        pass  # Cow card — special, skip specialty

    # Row → ranges
    row = src.get("row", "")
    if row == "leader":
        specialty = "leader"
        # Parse leader notes for instructions
        notes = src.get("notes", "")
        if notes:
            card["leader"] = {"instructions": notes.rstrip(".")}
    elif row == "agile":
        card["ranges"] = ["close", "ranged"]
        abilities.append("agile")
    elif row in ("close", "ranged", "siege"):
        card["ranges"] = [row]
    elif specialty == "weather":
        # Weather cards get ranges from their type
        card["ranges"] = WEATHER_ROWS.get(src["name"], [])

    if specialty:
        card["specialty"] = specialty
    if abilities:
        card["abilities"] = abilities

    # Starter detection
    locations = src.get("locations", [])
    if any(loc.get("type") == "base deck" for loc in locations):
        card["starter"] = True

    return card


def count_copies_needed(src):
    """Determine how many copies of a card should exist based on locations."""
    locations = src.get("locations", [])
    # Multiple base deck entries or buy locations suggest multiple copies
    base_deck_count = sum(1 for loc in locations if loc.get("type") == "base deck")
    if base_deck_count > 1:
        return base_deck_count
    # Cards like Arachas have 3 buy locations = 3 copies
    buy_count = sum(1 for loc in locations if loc.get("type") == "buy")
    if buy_count > 1 and src.get("abilities") and "Muster" in src.get("abilities", []):
        return buy_count
    return 1


def main():
    parser = argparse.ArgumentParser(description="Import Gwent cards from GWENTcards database")
    parser.add_argument("--source", required=True, help="Path to GWENTcards/public directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    args = parser.parse_args()

    existing = load_existing_cards()
    print(f"Existing cards: {sum(len(v) for v in existing.values())} files, {len(existing)} unique names\n")

    created = 0
    skipped = 0
    updated = 0

    for src_file, faction in SOURCE_FILES.items():
        filepath = os.path.join(args.source, src_file)
        if not os.path.exists(filepath):
            print(f"  SKIP {src_file}: not found")
            continue

        with open(filepath) as f:
            data = json.load(f)
        cards = data.get("cards", data) if isinstance(data, dict) else data

        faction_dir = os.path.join(CARDS_DIR, FACTION_TO_DIR[faction])

        print(f"\n{'='*60}")
        print(f"  {faction} ({len(cards)} cards in source)")
        print(f"{'='*60}")

        for src_card in cards:
            name = src_card["name"]
            key = normalize_name(name)
            copies_needed = count_copies_needed(src_card)

            # Check if we already have this card
            existing_copies = existing.get(key, [])

            if existing_copies:
                copies_have = len(existing_copies)
                if copies_have >= copies_needed:
                    print(f"  SKIP  {name} (have {copies_have}/{copies_needed})")
                    skipped += 1
                    continue
                else:
                    # Need more copies
                    copies_to_add = copies_needed - copies_have
                    print(f"  ADD   {name} ({copies_to_add} more copies, have {copies_have}/{copies_needed})")
                    card_data = convert_card(src_card, faction)
                    for n in range(copies_have + 1, copies_needed + 1):
                        copy_name = f"{name}: {n}"
                        card_data_copy = dict(card_data)
                        card_data_copy["name"] = copy_name
                        fname = fs_safe(copy_name) + ".json"
                        out_path = os.path.join(faction_dir, fname)
                        if not args.dry_run:
                            os.makedirs(faction_dir, exist_ok=True)
                            with open(out_path, "w") as f:
                                json.dump(card_data_copy, f, indent=4)
                        print(f"        → {fname}")
                        created += 1
            else:
                # New card
                card_data = convert_card(src_card, faction)
                if copies_needed == 1:
                    fname = fs_safe(name) + ".json"
                    out_path = os.path.join(faction_dir, fname)
                    if not args.dry_run:
                        os.makedirs(faction_dir, exist_ok=True)
                        with open(out_path, "w") as f:
                            json.dump(card_data, f, indent=4)
                    print(f"  NEW   {name} → {fname}")
                    created += 1
                else:
                    print(f"  NEW   {name} ({copies_needed} copies)")
                    for n in range(1, copies_needed + 1):
                        copy_name = f"{name}: {n}"
                        card_data_copy = dict(card_data)
                        card_data_copy["name"] = copy_name
                        fname = fs_safe(copy_name) + ".json"
                        out_path = os.path.join(faction_dir, fname)
                        if not args.dry_run:
                            os.makedirs(faction_dir, exist_ok=True)
                            with open(out_path, "w") as f:
                                json.dump(card_data_copy, f, indent=4)
                        print(f"        → {fname}")
                        created += 1

    print(f"\n{'='*60}")
    action = "Would create" if args.dry_run else "Created"
    print(f"  {action}: {created}, Skipped: {skipped}, Updated: {updated}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
