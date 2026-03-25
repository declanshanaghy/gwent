from typing import List, Iterable

import gwent.messaging.base

import gwent.messaging.card

KIND = 'card_play'

PLAYER = 'player'
CARD = 'card'
ADD_TO_DECK = 'add_to_deck'
DEAL_TO_HAND = 'deal_to_hand'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_add_to_deck(player:str, card: gwent.messaging.card.Message):
        instance = {
            PLAYER: player,
            CARD: card._instance
        }
        return Message(instance, subkind=ADD_TO_DECK)

    @staticmethod
    def with_deal_to_hand(player: str, card: gwent.messaging.card.Message):
        instance = {
            PLAYER: player,
            CARD: card._instance
        }
        return Message(instance, subkind=DEAL_TO_HAND)

    @property
    def kind(self):
        return KIND

    @property
    def card(self):
        return gwent.messaging.card.Message.from_properties(self._instance[CARD])
