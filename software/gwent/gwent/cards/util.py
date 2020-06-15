import logging
import os.path
import shutil

import random

import gwent.cards.all
import gwent.messaging.card
import gwent.cards.scoiatael
import gwent.cards.skellige
import gwent.cards.monsters
import gwent.cards.nilfgaardian
import gwent.cards.northern_realms

import gwent.log


def random_card_details() -> dict:
    factions = [f for f in gwent.cards.all.CARDS_BY_FACTION.keys()]
    faction = random.choice(factions)
    names = [c for c in gwent.cards.all.CARDS_BY_FACTION[faction].keys()]
    name = random.choice(names)
    # faction = gwent.card.NORTHERN_REALMS
    # name = 'Trebuchet: 1'

    details = gwent.cards.all.CARDS_BY_FACTION[faction][name]
    details[gwent.messaging.card.NAME] = name
    details[gwent.messaging.card.FACTION] = faction
    return details


def random_card() -> gwent.messaging.card.Message:
    return gwent.messaging.card.Message(random_card_details())

def fs_safe(s: str) -> str:
    return "".join([c for c in s if c.isalpha() or c.isdigit()]).rstrip()

def write_all_to_disk():
    log = logging.getLogger(os.path.basename(__file__))
    dir = os.path.abspath(os.path.join(__file__, '..', '../messaging', '..',
                                       '..', '..', 'data', 'cards'))
    if os.path.exists(dir):
        shutil.rmtree(dir)

    for faction, cards in gwent.cards.all.CARDS_BY_FACTION.items():
        facdir = os.path.join(dir, fs_safe(faction))
        if not os.path.exists(facdir):
            log.info(f'creating {facdir}')
            os.makedirs(facdir)

        for name, details in cards.items():
            card = gwent.messaging.card.Message.from_properties(
                details, name=name, faction=faction)
            file = f'{fs_safe(card.full_name)}.json'
            fpath = os.path.join(facdir, file)
            with open(fpath, 'w') as f:
                log.info(f'writing {file} to {facdir}')
                f.write(card.body_pretty)

if __name__ == '__main__':
    gwent.log.setup()
    write_all_to_disk()
