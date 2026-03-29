from typing import List, Iterable

import gwent.messaging.base

import gwent.messaging.card

KIND = 'card_play'

PLAYER = 'player'
CARD = 'card'
ADD_TO_DECK = 'add_to_deck'
DEAL_LEADER = 'deal_leader'
DEAL_TO_HAND = 'deal_to_hand'
UPDATE_SCORE = 'update_score'
UPDATE_GEMS = 'update_gems'

SCORE = 'score'
GEMS = 'gems'
ACTIVE_TURN = 'active_turn'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_add_to_deck(player:str, card: gwent.messaging.card.Message):
        instance = {
            PLAYER: player,
            CARD: card._instance
        }
        return Message(instance, subkind=ADD_TO_DECK)

    @staticmethod
    def with_deal_leader(player: str, card: gwent.messaging.card.Message):
        instance = {
            PLAYER: player,
            CARD: card._instance
        }
        return Message(instance, subkind=DEAL_LEADER)

    @staticmethod
    def with_deal_to_hand(player: str, card: gwent.messaging.card.Message):
        instance = {
            PLAYER: player,
            CARD: card._instance
        }
        return Message(instance, subkind=DEAL_TO_HAND)

    @staticmethod
    def with_update_score(player: str, score: int, active_turn: bool = False):
        instance = {
            PLAYER: player,
            SCORE: score,
            ACTIVE_TURN: active_turn,
        }
        return Message(instance, subkind=UPDATE_SCORE)

    @staticmethod
    def with_update_gems(player: str, gems: int):
        instance = {
            PLAYER: player,
            GEMS: gems,
        }
        return Message(instance, subkind=UPDATE_GEMS)

    @property
    def kind(self):
        return KIND

    @property
    def card(self):
        return gwent.messaging.card.Message.from_properties(self._instance[CARD])
