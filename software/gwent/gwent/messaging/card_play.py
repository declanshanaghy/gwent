from typing import List, Iterable

import gwent.messaging.base

import gwent.messaging.card

KIND = 'card_play'

PLAYER = 'player'
CARD = 'card'
ADD_TO_DECK = 'add_to_deck'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_add_to_deck(player:str, card: gwent.messaging.card.Message):
        instance = {
            PLAYER: player,
            CARD: card._instance
        }
        return Message(instance, subkind=ADD_TO_DECK)

    @property
    def kind(self):
        return KIND

    @property
    def card(self):
        return gwent.messaging.card.Message.from_properties(self._instance[CARD])
