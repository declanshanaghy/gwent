import random

import gwent.cards
import gwent.cards.scoiatael
import gwent.cards.skellige
import gwent.cards.monsters
import gwent.cards.nilfgaardian
import gwent.cards.northern_realms

CARDS_BY_FACTION = {}
CARDS_BY_FACTION.update(gwent.cards.scoiatael.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(gwent.cards.skellige.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(gwent.cards.monsters.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(gwent.cards.nilfgaardian.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(gwent.cards.northern_realms.CARDS_BY_FACTION)


def random_card_details() -> dict:
    factions = [ f for f in CARDS_BY_FACTION.keys() ]
    faction = random.choice(factions)
    names = [ c for c in CARDS_BY_FACTION[faction].keys() ]
    name = random.choice(names)
    # faction = gwent.cards.NORTHERN_REALMS
    # name = 'Trebuchet: 1'

    details = CARDS_BY_FACTION[faction][name]
    details[gwent.cards.NAME] = name
    details[gwent.cards.FACTION] = faction
    return details


def random_card() -> gwent.cards.Card:
    return gwent.cards.Card(random_card_details())
