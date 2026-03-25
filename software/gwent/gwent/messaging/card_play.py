from typing import List, Iterable

import gwent.messaging.base

import gwent.messaging.card

KIND = 'card_play'

PLAYER = 'player'
CARD = 'card'
ADD_TO_DECK = 'add_to_deck'
DEAL_TO_HAND = 'deal_to_hand'
UPDATE_SCORE = 'update_score'

SCORE = 'score'


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

    @staticmethod
    def with_update_score(player: str, score: int):
        instance = {
            PLAYER: player,
            SCORE: score,
        }
        return Message(instance, subkind=UPDATE_SCORE)

    @property
    def kind(self):
        return KIND

    @property
    def card(self):
        return gwent.messaging.card.Message.from_properties(self._instance[CARD])
