import random

import gwent.game.cards
import gwent.game.cards.scoiatael
import gwent.game.cards.skellige
import gwent.game.cards.monsters
import gwent.game.cards.nilfgaardian
import gwent.game.cards.northern_realms

CARDS_BY_FACTION = {}
CARDS_BY_FACTION.update(gwent.game.cards.scoiatael.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(gwent.game.cards.skellige.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(gwent.game.cards.monsters.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(gwent.game.cards.nilfgaardian.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(gwent.game.cards.northern_realms.CARDS_BY_FACTION)


def random_card_details() -> dict:
    factions = [ f for f in CARDS_BY_FACTION.keys() ]
    faction = random.choice(factions)
    names = [ c for c in CARDS_BY_FACTION[faction].keys() ]
    name = random.choice(names)
    # faction = gwent.game.cards.NORTHERN_REALMS
    # name = 'Trebuchet: 1'

    details = CARDS_BY_FACTION[faction][name]
    details[gwent.game.cards.NAME] = name
    details[gwent.game.cards.FACTION] = faction
    return details


def random_card() -> gwent.game.cards.Card:
    return gwent.game.cards.Card(random_card_details())
