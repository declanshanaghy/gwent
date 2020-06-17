import json
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

log = logging.getLogger('card.util')


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
    return gwent.messaging.card.Message.from_properties(
        random_card_details())


def fs_safe(s: str) -> str:
    return "".join([c for c in s if c.isalpha() or c.isdigit()]).rstrip()


def read_card(f: str) -> gwent.messaging.card.Message:
    with open(f) as fb:
        details = json.load(fb)
        return gwent.messaging.card.Message.from_properties(details)


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


def validate_cards() -> gwent.messaging.card.Message:
    biggest_card = None
    total_cards = 0
    cards_by_faction = gwent.cards.all.CARDS_BY_FACTION
    cards_by_faction_by_owner = {}
    starters_by_faction = {}

    for faction, cards in cards_by_faction.items():
        if not faction in cards_by_faction_by_owner:
            cards_by_faction_by_owner[faction] = {}
        if not faction in starters_by_faction:
            starters_by_faction[faction] = {}

        total_cards += len(cards.keys())
        for name, details in cards.items():
            card = gwent.messaging.card.Message.from_properties(
                rfid=None, details=details, name=name, faction=faction)

            if card.is_starter:
                starters_by_faction[faction][card.name] = card

            if card.has_owner:
                if not card.owner in cards_by_faction_by_owner[
                    faction]:
                    cards_by_faction_by_owner[faction][card.owner] = {}
                cards_by_faction_by_owner[faction][card.owner][
                    card.name] = card

            if biggest_card is None or card.bytes > biggest_card.bytes:
                biggest_card = card

    for faction, cards in starters_by_faction.items():
        log.info({
            'action': 'starters',
            'faction': faction,
            'count': len(cards),
        })

    totals_by_owner = {}
    for faction, cards_by_owner in cards_by_faction_by_owner.items():
        for owner, cards in cards_by_owner.items():
            if not owner in totals_by_owner:
                totals_by_owner[owner] = 0
            totals_by_owner[owner] += len(cards)
            log.info({
                'owner': owner,
                'faction': faction,
                'count': len(cards),
            })

    for owner, total in totals_by_owner.items():
        log.info({
            'owner': owner,
            'total': total,
        })

    log.info({
        'action': 'biggest_card',
        'total_cards': total_cards,
        'name': biggest_card.name,
        'bytes': biggest_card.bytes,
        'blocks': biggest_card.blocks,
        'body_sectors': biggest_card.body_sectors
    })

    return biggest_card


if __name__ == '__main__':
    gwent.log.setup(level='debug')
    write_all_to_disk()
