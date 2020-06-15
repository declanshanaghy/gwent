import gwent.cards
import gwent.cards.monsters
import gwent.cards.nilfgaardian
import gwent.cards.northern_realms
import gwent.cards.scoiatael
import gwent.cards.skellige


CARDS_BY_FACTION = {}
CARDS_BY_FACTION.update(
    gwent.cards.scoiatael.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(
    gwent.cards.skellige.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(
    gwent.cards.monsters.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(
    gwent.cards.nilfgaardian.CARDS_BY_FACTION)
CARDS_BY_FACTION.update(
    gwent.cards.northern_realms.CARDS_BY_FACTION)


