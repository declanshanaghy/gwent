#!/usr/bin/env python3
"""Build synergy-optimized faction decks and generate matchup recordings.

Usage:
    python3 .claude/skills/super-victory/scripts/build-decks.py
    python3 .claude/skills/super-victory/scripts/build-decks.py --factions skellige,monsters
    python3 .claude/skills/super-victory/scripts/build-decks.py --hand 10
"""

import argparse
import glob
import hashlib
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..', '..'))
CARDS_DIR = os.path.join(REPO_ROOT, 'software', 'data', 'cards')
RECORDINGS_DIR = os.path.join(REPO_ROOT, 'software', 'data', 'recordings')

FACTIONS = ["Monsters", "Nilfgaardian", "Northern Realms", "Scoia'tael", "Skellige"]
FACTION_SLUGS = {
    "Monsters": "monsters", "Nilfgaardian": "nilfgaardian",
    "Northern Realms": "northernrealms", "Scoia'tael": "scoiatael",
    "Skellige": "skellige",
}

MAX_SPIES = 2
DECK_SIZE = 20


# ---------------------------------------------------------------------------
# Card loading
# ---------------------------------------------------------------------------

def load_eligible_cards():
    """Load all cards with BOTH rfid AND image fields."""
    cards = []
    for f in sorted(glob.glob(os.path.join(CARDS_DIR, '**', '*.json'), recursive=True)):
        if 'CardReport' in f:
            continue
        with open(f) as fh:
            c = json.load(fh)
            if c.get('rfid') and c.get('image'):
                cards.append(c)
    return cards


def group_by_faction(cards):
    by_faction = {}
    for c in cards:
        by_faction.setdefault(c['faction'], []).append(c)
    return by_faction


# ---------------------------------------------------------------------------
# Card dict helpers
# ---------------------------------------------------------------------------

def make_card(c):
    """Build a card dict for recordings with content_id."""
    d = {"kind": "card", "faction": c["faction"], "name": c["name"]}
    for key in ("rfid", "strength", "ranges", "abilities", "musters_with",
                "specialty", "starter", "owner", "owner_nickname", "leader", "image"):
        if c.get(key) is not None:
            d[key] = c[key]
    cid = hashlib.md5(json.dumps(d, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    d["content_id"] = cid
    return d


def pick(cards, **criteria):
    """Filter cards by criteria."""
    results = []
    for c in cards:
        match = True
        for k, v in criteria.items():
            if k == 'ability':
                if v not in (c.get('abilities') or []):
                    match = False
            elif k == 'name_contains':
                if v.lower() not in c.get('name', '').lower():
                    match = False
            elif k == 'name':
                if c.get('name') != v:
                    match = False
            elif k == 'specialty':
                if c.get('specialty') != v:
                    match = False
            elif k == 'min_strength':
                if (c.get('strength') or 0) < v:
                    match = False
            else:
                if c.get(k) != v:
                    match = False
        if match:
            results.append(c)
    return results


# ---------------------------------------------------------------------------
# Deck builder
# ---------------------------------------------------------------------------

def build_deck(faction_name, cards, hand_size=10):
    """Build a 20-card deck + leader for a faction.

    Returns (leader_card, hand_list, deck_list).
    """
    leaders = pick(cards, specialty='leader')
    units = [c for c in cards if c.get('specialty') != 'leader']

    deck_cards = []
    spy_count = 0

    def add(card):
        nonlocal spy_count
        if len(deck_cards) >= DECK_SIZE:
            return False
        if 'spy' in (card.get('abilities') or []):
            if spy_count >= MAX_SPIES:
                return False
            spy_count += 1
        deck_cards.append(card)
        return True

    def add_all(card_list, limit=None):
        count = 0
        for c in card_list:
            if limit and count >= limit:
                break
            if add(c):
                count += 1
        return count

    # --- Leader selection ---
    leader_prefs = {
        "Monsters": "Eredin - King of the Wild Hunt",
        "Nilfgaardian": "Emhyr var Emreis - His Imperial Majesty",
        "Northern Realms": "Foltest: the Siegemaster",
        "Scoia'tael": "Francesca Findabair - The Beautiful",
        "Skellige": None,  # Only one leader
    }
    pref = leader_prefs.get(faction_name)
    leader = None
    if pref:
        matches = pick(leaders, name=pref)
        leader = matches[0] if matches else None
    if not leader and leaders:
        leader = leaders[0]

    # --- Ensure leader ability has required cards in deck ---
    if leader:
        ld = leader.get('leader', {})
        weather_ranges = ld.get('weather_ranges')
        if weather_ranges:
            # Leader draws weather from deck — ensure matching weather cards exist.
            # Must match by ranges field, not just name (some weather cards have ranges=[])
            for wr in weather_ranges:
                matching = [c for c in units
                            if c.get('specialty') == 'weather'
                            and wr in (c.get('ranges') or [])]
                add_all(matching, limit=1)

    # --- Faction-specific core ---
    if faction_name == "Monsters":
        add_all(pick(units, ability='muster', name_contains='arachas'))
        add_all(pick(units, ability='muster', name_contains='crone'))
        add_all(pick(units, ability='muster', name_contains='vampire'))
        add_all(pick(units, name="Geralt of Rivia"))
        add_all(pick(units, name="Imlerith"))
        add_all(pick(units, name="Draug"))
        add_all(pick(units, specialty='hero', name_contains='kayran'))
        add_all(pick(units, ability='commander', name_contains='dandelion'), limit=1)
        add_all(pick(units, ability='spy'), limit=MAX_SPIES)
        add_all(pick(units, ability='scorch', name_contains='villentretenmerth'), limit=1)

    elif faction_name == "Nilfgaardian":
        add_all(pick(units, name="Avallac'h"), limit=1)
        add_all(pick(units, name="Stefan Skellen"), limit=1)
        add_all(pick(units, ability='bond', name_contains='impera'))
        add_all(pick(units, ability='bond', name_contains='young emissary'))
        add_all(pick(units, ability='medic', specialty='hero'), limit=2)
        add_all(pick(units, name="Morvran Voorhis"))
        add_all(pick(units, name="Tibor Eggebracht"))
        add_all(pick(units, ability='commander', name_contains='dandelion'), limit=1)
        add_all(pick(units, specialty='decoy'), limit=1)

    elif faction_name == "Northern Realms":
        add_all(pick(units, name="Cirilla Fiona Elen Riannon"), limit=1)
        add_all(pick(units, name="Geralt of Rivia"))
        add_all(pick(units, name="Philippa Eilhart"))
        add_all(pick(units, name="John Natalis: 2"))
        add_all(pick(units, name="Avallac'h"), limit=1)
        add_all(pick(units, name="Prince Stennis"), limit=1)
        add_all(pick(units, name_contains='ballista'))
        add_all(pick(units, name_contains='trebuchet'))
        add_all(pick(units, name_contains='siege tower'))
        add_all(pick(units, ability='morale', name_contains='kaedweni'))
        add_all(pick(units, name="Dun Banner Medic"))

    elif faction_name == "Scoia'tael":
        add_all(pick(units, name="Geralt of Rivia"))
        add_all(pick(units, name="Cirilla Fiona Elen Riannon"))
        add_all(pick(units, name="Isengrim Faoiltiarna: 2"))
        add_all(pick(units, ability='agile', name_contains='dol blathanna scout'))
        add_all(pick(units, ability='agile', name_contains='filavandrel'))
        add_all(pick(units, ability='agile', name_contains='vrihedd brigade vet'))
        add_all(pick(units, ability='muster', name_contains='dwarven skirmisher'))
        add_all(pick(units, ability='muster', name_contains='elven skirmisher'))
        add_all(pick(units, specialty='decoy'), limit=2)
        add_all(pick(units, name="Havekar Healer"))

    elif faction_name == "Skellige":
        add_all(pick(units, ability='bond', name_contains='clan an craite warrior'))
        add_all(pick(units, ability='bond', name_contains='transformed young vildkaarl'))
        add_all(pick(units, ability='bond', name_contains='war longship'))
        add_all(pick(units, name="Cirilla Fiona Elen Riannon"))
        add_all(pick(units, name="Olaf"))
        add_all(pick(units, name="Hemdall"))
        add_all(pick(units, name="Hjalmar"))
        add_all(pick(units, ability='commander', name_contains='dandelion'), limit=1)
        add_all(pick(units, specialty='commander', name_contains="commander's horn"), limit=1)
        add_all(pick(units, ability='spy'), limit=MAX_SPIES)
        add_all(pick(units, name="Birna Bran"))
        add_all(pick(units, specialty='decoy'), limit=1)

    # --- Common support cards ---
    add_all(pick(units, specialty='weather', name_contains='frost'), limit=1)
    add_all(pick(units, specialty='weather', name_contains='clear'), limit=1)

    # --- Fill remaining slots with highest-strength units ---
    remaining = sorted(
        [c for c in units if c not in deck_cards and c.get('specialty') != 'leader'],
        key=lambda x: -(x.get('strength') or 0))
    add_all(remaining)

    # --- Validate ---
    actual_spies = sum(1 for c in deck_cards if 'spy' in (c.get('abilities') or []))
    if actual_spies > MAX_SPIES:
        raise ValueError(f"{faction_name}: {actual_spies} spies (max {MAX_SPIES})")
    if len(deck_cards) != DECK_SIZE:
        raise ValueError(f"{faction_name}: {len(deck_cards)} cards (need {DECK_SIZE})")

    # --- Split into hand and deck ---
    # Prioritize: spies, muster triggers, heroes in hand
    hand_priority = []
    deck_rest = []
    for c in deck_cards:
        abilities = c.get('abilities') or []
        if 'spy' in abilities or 'muster' in abilities or c.get('specialty') == 'hero':
            hand_priority.append(c)
        else:
            deck_rest.append(c)

    # Identify cards that MUST stay in deck (leader weather targets)
    must_stay_in_deck = set()
    if leader:
        ld = leader.get('leader', {})
        if ld.get('weather_ranges'):
            for wr in ld['weather_ranges']:
                for c in deck_cards:
                    if c.get('specialty') == 'weather' and wr in (c.get('ranges') or []):
                        must_stay_in_deck.add(id(c))
                        break  # one per range is enough

    hand = hand_priority[:hand_size]
    deck = deck_rest + hand_priority[hand_size:]

    # Ensure leader's weather cards are in deck (not hand) — leader draws from deck
    if leader:
        ld = leader.get('leader', {})
        if ld.get('weather_ranges'):
            for wr in ld['weather_ranges']:
                # Find matching weather card in hand and move it to deck
                for c in list(hand):
                    if c.get('specialty') == 'weather' and wr in (c.get('ranges') or []):
                        hand.remove(c)
                        deck.insert(0, c)
                        # Backfill hand from deck (pick a non-weather card)
                        for dc in list(deck):
                            if dc.get('specialty') != 'weather':
                                deck.remove(dc)
                                hand.append(dc)
                                break
                        break
                # Also check: is the required weather in the deck at all?
                in_deck = any(c.get('specialty') == 'weather' and wr in (c.get('ranges') or [])
                              for c in deck)
                if not in_deck:
                    print(f"  WARNING: No weather card with range '{wr}' in deck for leader ability")
    if len(hand) < hand_size:
        # Backfill hand from deck, but never pull leader-critical weather cards
        needed = hand_size - len(hand)
        backfill = []
        remaining_deck = []
        for c in deck:
            if needed > 0 and id(c) not in must_stay_in_deck:
                backfill.append(c)
                needed -= 1
            else:
                remaining_deck.append(c)
        hand.extend(backfill)
        deck = remaining_deck

    total_str = sum(c.get('strength', 0) for c in deck_cards)
    print(f"  {faction_name}: {len(hand)}h+{len(deck)}d, "
          f"{actual_spies} spies, total_str={total_str}")

    return make_card(leader), [make_card(c) for c in hand], [make_card(c) for c in deck]


# ---------------------------------------------------------------------------
# Recording generation
# ---------------------------------------------------------------------------

def make_recording(f1, f2, d1, d2):
    """Generate a recording JSON dict."""
    return {
        "version": 1,
        "saved_at": datetime.now().isoformat(),
        "active_stage": "PlayRound",
        "state": {
            "board": {
                "players": {
                    "PLAYER.ONE": {"rows": {"close": [], "ranged": [], "siege": []},
                                   "discard": [], "gems": 2, "passed": False, "leader_used": False},
                    "PLAYER.TWO": {"rows": {"close": [], "ranged": [], "siege": []},
                                   "discard": [], "gems": 2, "passed": False, "leader_used": False},
                },
                "leaders": {"PLAYER.ONE": d1["leader"], "PLAYER.TWO": d2["leader"]},
                "factions": {"PLAYER.ONE": f1, "PLAYER.TWO": f2},
                "hands": {"PLAYER.ONE": list(d1["hand"]), "PLAYER.TWO": list(d2["hand"])},
                "decks": {"PLAYER.ONE": list(d1["deck"]), "PLAYER.TWO": list(d2["deck"])},
                "weather_rows": [],
                "commander_horn_rows": {"PLAYER.ONE": [], "PLAYER.TWO": []},
                "current_player": "PLAYER.ONE",
                "round_number": 1,
                "spy_doubling": False,
                "medic_random": False,
                "half_weather_penalty": {"PLAYER.ONE": 0, "PLAYER.TWO": 0},
                "scores": {
                    "PLAYER.ONE": {"total": 0, "close": 0, "ranged": 0, "siege": 0},
                    "PLAYER.TWO": {"total": 0, "close": 0, "ranged": 0, "siege": 0},
                },
            }
        }
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build super-victory decks and recordings")
    parser.add_argument("--factions", default=None,
                        help="Comma-separated faction subset (default: all 5)")
    parser.add_argument("--hand", type=int, default=10,
                        help="Cards dealt to hand (default: 10)")
    args = parser.parse_args()

    if args.factions:
        slug_to_name = {v: k for k, v in FACTION_SLUGS.items()}
        selected = []
        for s in args.factions.split(','):
            s = s.strip().lower()
            if s in slug_to_name:
                selected.append(slug_to_name[s])
            else:
                # Try direct match
                for f in FACTIONS:
                    if f.lower().replace("'", "").replace(" ", "") == s:
                        selected.append(f)
                        break
                else:
                    print(f"Unknown faction: {s}", file=sys.stderr)
                    sys.exit(1)
    else:
        selected = list(FACTIONS)

    # Load cards
    all_cards = load_eligible_cards()
    by_faction = group_by_faction(all_cards)
    print(f"Loaded {len(all_cards)} eligible cards (rfid + image)")

    # Build decks
    print("\nBuilding decks:")
    decks = {}
    for f in selected:
        leader, hand, deck = build_deck(f, by_faction.get(f, []), hand_size=args.hand)
        decks[f] = {"leader": leader, "hand": hand, "deck": deck}

    # Delete old super-victory recordings
    old = glob.glob(os.path.join(RECORDINGS_DIR, '*-super-victory-*.json'))
    for f in old:
        os.remove(f)
    if old:
        print(f"\nRemoved {len(old)} old super-victory recordings")

    # Find next number prefix
    existing = sorted(glob.glob(os.path.join(RECORDINGS_DIR, '*.json')))
    if existing:
        last_name = os.path.basename(existing[-1])
        try:
            num = int(last_name.split('-')[0]) + 1
        except ValueError:
            num = 1
    else:
        num = 1

    # Generate matchups
    print(f"\n## Generated Matchups\n")
    print(f"| # | File | P1 | P2 | P1 Str | P2 Str |")
    print(f"|---|------|----|----|--------|--------|")

    matchup_num = 0
    faction_list = [f for f in FACTIONS if f in selected]

    for i, f1 in enumerate(faction_list):
        for f2 in faction_list[i + 1:]:
            for p1_faction, p2_faction in [(f1, f2), (f2, f1)]:
                recording = make_recording(
                    p1_faction, p2_faction, decks[p1_faction], decks[p2_faction])
                slug1 = FACTION_SLUGS[p1_faction]
                slug2 = FACTION_SLUGS[p2_faction]
                fname = f"{num:03d}-super-victory-{slug1}-vs-{slug2}.json"
                path = os.path.join(RECORDINGS_DIR, fname)
                with open(path, 'w') as fh:
                    json.dump(recording, fh, indent=2)

                p1_str = sum(c.get('strength', 0)
                             for c in decks[p1_faction]["hand"] + decks[p1_faction]["deck"])
                p2_str = sum(c.get('strength', 0)
                             for c in decks[p2_faction]["hand"] + decks[p2_faction]["deck"])
                matchup_num += 1
                print(f"| {matchup_num} | {fname} | {p1_faction} | {p2_faction} | {p1_str} | {p2_str} |")
                num += 1

    print(f"\n{matchup_num} recordings generated in {RECORDINGS_DIR}")


if __name__ == "__main__":
    main()
