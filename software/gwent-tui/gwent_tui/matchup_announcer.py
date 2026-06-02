"""Witcher-flavored matchup announcements for the New Game screen.

Given the two rolled factions, produce a short, spoken-style line naming the
factions and their iconic leaders — and, for colour, the odd location, hero or
famous card. The intro varies: sometimes one leader is named, sometimes the
other, sometimes both, sometimes neither. A pile of templates keeps it fresh.

Pure presentation — the TUI speaks the result via the announcer voice
(tts.speak with faction=None) when the wizard is first shown or re-rolled.
"""
from __future__ import annotations

import random

# Per-faction lore banks. Leaders are the canonical Gwent leader cards; heroes
# are famous units/characters; locations anchor the flavour; `epithet` is a
# stand-in when a leader isn't named.
FACTIONS = {
    "Monsters": {
        "leaders": [
            "Eredin, King of the Wild Hunt",
            "Eredin Bréacc Glas, the Treacherous",
            "Imlerith of the Wild Hunt",
        ],
        "heroes": ["Imlerith", "Caranthir", "the Crones of Crookback Bog",
                   "a Fiend of the deep woods", "the Leshen"],
        "locations": ["the frozen wastes beyond the worlds",
                      "the spectral ranks of the Wild Hunt",
                      "the mists of Crookback Bog"],
        "epithet": "the relentless horde",
    },
    "Nilfgaardian": {
        "leaders": [
            "Emhyr var Emreis, the White Flame",
            "Emhyr var Emreis, Emperor of Nilfgaard",
            "Emhyr var Emreis, Invader of the North",
        ],
        "heroes": ["Menno Coehoorn", "Morvran Voorhis", "Tibor Eggebracht",
                   "Cahir", "the Impera Brigade"],
        "locations": ["the golden towers of the City of Nilfgaard",
                      "the conquered lands south of the Yaruga",
                      "the Great Sun's empire"],
        "epithet": "the legions of the Great Sun",
    },
    "Northern Realms": {
        "leaders": [
            "Foltest, King of Temeria",
            "Foltest, the Steel-Forged",
            "Foltest, Lord Commander of the North",
        ],
        "heroes": ["Vernon Roche", "Ves", "John Natalis", "the Blue Stripes",
                   "the Dun Banner"],
        "locations": ["the walls of Vizima",
                      "the united banners of Temeria, Redania and Kaedwen",
                      "the fortress of Kaer Morhen"],
        "epithet": "the kings of the North",
    },
    "Scoia'tael": {
        "leaders": [
            "Francesca Findabair, Queen of Dol Blathanna",
            "Francesca Findabair, the Beautiful",
            "Francesca Findabair, Hope of the Aen Seidhe",
        ],
        "heroes": ["Iorveth", "Isengrim Faoiltiarna", "Saskia the Dragonslayer",
                   "Yaevinn", "the Vrihedd Brigade"],
        "locations": ["the hidden glades of Dol Blathanna",
                      "the free elven forests",
                      "the Blue Mountains"],
        "epithet": "the Squirrels of the deep wood",
    },
    "Skellige": {
        "leaders": [
            "Crach an Craite, Jarl of the Isles",
            "King Bran of Skellige",
            "Crach an Craite, An Craite's pride",
        ],
        "heroes": ["Hjalmar an Craite", "Cerys an Craite", "Madman Lugos",
                   "the Clan an Craite warriors", "Birna Bran"],
        "locations": ["the storm-lashed isles of Skellige",
                      "the longhouses of Kaer Trolde",
                      "the raging Great Sea"],
        "epithet": "the storm-born raiders",
    },
}

_DEFAULT = {
    "leaders": ["an unknown commander"],
    "heroes": ["a nameless champion"],
    "locations": ["a far-off land"],
    "epithet": "an unproven host",
}

# {l1}/{l2} = leader, {p1}/{p2} = faction, {loc1}/{loc2} = location,
# {h1}/{h2} = hero, {e1}/{e2} = epithet.
_TEMPLATES_BOTH = [
    "From {loc1}, {l1} leads {p1} to the table — and across it waits {l2}, "
    "marshalling {p2}. Let the Gwent begin!",
    "{l1} of {p1} faces {l2} of {p2}. Steel, sorcery and stratagem — the "
    "board is set!",
    "A reckoning at the gaming table: {l1} rallies {p1}, while {l2} answers "
    "with {p2}. May the best hand prevail.",
    "Hear ye! {p1} under {l1} meets {p2} under {l2}. Even {h1} and {h2} hold "
    "their breath.",
    "Two banners rise — {l1} for {p1}, {l2} for {p2}. The whole inn falls "
    "silent. Deal the cards!",
    "The wheel of fortune turns: {l1} brings the might of {p1}; {l2} summons "
    "{p2} from {loc2}. To arms!",
]

_TEMPLATES_P1 = [
    "{l1} of {p1} takes the field against {e2} of {p2}. Deal the cards!",
    "All hail {l1}! {p1} marches to war — and {p2} must answer, with {h2} "
    "waiting in the wings.",
    "From {loc1}, {l1} commands {p1}. The {p2} stand ready across the table. "
    "Begin!",
    "{l1} leads {p1} into the fray, {h1} at the vanguard. {p2}, your move.",
]

_TEMPLATES_P2 = [
    "Across the board, {l2} raises the banner of {p2} against {e1} of {p1}. "
    "Begin!",
    "Beware — {l2} leads {p2} this day, and {p1} must answer. {h1} sharpens "
    "his blade.",
    "From {loc2}, {l2} brings {p2} to bear. {p1}, the first move is yours.",
    "{l2} marshals {p2}, {h2} at their side. The {p1} host braces for the "
    "clash.",
]

_TEMPLATES_NONE = [
    "{e1} of {p1} meets {e2} of {p2}. From {loc1} to {loc2}, the cards will "
    "settle it. Begin!",
    "{p1} against {p2} — {h1} versus {h2}. Place your bets and deal!",
]


def _bank(faction: str) -> dict:
    return FACTIONS.get(faction, _DEFAULT)


def announce_matchup(p1_faction: str, p2_faction: str) -> str:
    """Build a varied, Witcher-styled matchup line for the two factions."""
    a, b = _bank(p1_faction), _bank(p2_faction)
    ctx = {
        "p1": p1_faction or "the North",
        "p2": p2_faction or "the South",
        "l1": random.choice(a["leaders"]),
        "l2": random.choice(b["leaders"]),
        "h1": random.choice(a["heroes"]),
        "h2": random.choice(b["heroes"]),
        "loc1": random.choice(a["locations"]),
        "loc2": random.choice(b["locations"]),
        "e1": a["epithet"],
        "e2": b["epithet"],
    }
    # Bias toward naming leaders: both is most common, neither is rare.
    bucket = random.choice(
        [_TEMPLATES_BOTH] * 4
        + [_TEMPLATES_P1] * 2
        + [_TEMPLATES_P2] * 2
        + [_TEMPLATES_NONE]
    )
    return random.choice(bucket).format(**ctx)
