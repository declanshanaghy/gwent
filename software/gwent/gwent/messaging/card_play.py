from typing import List, Iterable

import gwent.messaging.base

import gwent.messaging.card

KIND = 'card_play'

PLAYER = 'player'
CARD = 'card'
ROW = 'row'
TARGET_PLAYER = 'target_player'
REASON = 'reason'
WEATHER_ROWS = 'weather_rows'
RETURNED_CARD = 'returned_card'
OLD_CARD = 'old_card'
NEW_CARD = 'new_card'

ADD_TO_DECK = 'add_to_deck'
DEAL_LEADER = 'deal_leader'
DEAL_TO_HAND = 'deal_to_hand'
UPDATE_SCORE = 'update_score'
UPDATE_GEMS = 'update_gems'
PLAY_CARD = 'play_card'
REMOVE_CARD = 'remove_card'
WEATHER_CHANGE = 'weather_change'
COMMANDER_HORN = 'commander_horn'
MUSTER = 'muster'
SPY_DRAW = 'spy_draw'
MEDIC_RESURRECT = 'medic_resurrect'
DECOY_SWAP = 'decoy_swap'
TRANSFORM = 'transform'
ROUND_CLEAR = 'round_clear'

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

    @staticmethod
    def with_play_card(player: str, card, row: str, target_player: str = None):
        instance = {PLAYER: player, CARD: card._instance, ROW: row}
        if target_player:
            instance[TARGET_PLAYER] = target_player
        return Message(instance, subkind=PLAY_CARD)

    @staticmethod
    def with_remove_card(player: str, card, row: str, reason: str = ""):
        instance = {PLAYER: player, CARD: card._instance, ROW: row, REASON: reason}
        return Message(instance, subkind=REMOVE_CARD)

    @staticmethod
    def with_weather_change(player: str, weather_rows: list):
        instance = {PLAYER: player, WEATHER_ROWS: weather_rows}
        return Message(instance, subkind=WEATHER_CHANGE)

    @staticmethod
    def with_commander_horn(player: str, row: str):
        instance = {PLAYER: player, ROW: row}
        return Message(instance, subkind=COMMANDER_HORN)

    @staticmethod
    def with_muster(player: str, card, row: str):
        instance = {PLAYER: player, CARD: card._instance, ROW: row}
        return Message(instance, subkind=MUSTER)

    @staticmethod
    def with_spy_draw(player: str, card):
        instance = {PLAYER: player, CARD: card._instance}
        return Message(instance, subkind=SPY_DRAW)

    @staticmethod
    def with_medic_resurrect(player: str, card, row: str):
        instance = {PLAYER: player, CARD: card._instance, ROW: row}
        return Message(instance, subkind=MEDIC_RESURRECT)

    @staticmethod
    def with_decoy_swap(player: str, decoy_card, returned_card, row: str):
        instance = {
            PLAYER: player, CARD: decoy_card._instance,
            RETURNED_CARD: returned_card._instance, ROW: row,
        }
        return Message(instance, subkind=DECOY_SWAP)

    @staticmethod
    def with_transform(player: str, old_card, new_card, row: str):
        instance = {
            PLAYER: player, OLD_CARD: old_card._instance,
            NEW_CARD: new_card._instance, ROW: row,
        }
        return Message(instance, subkind=TRANSFORM)

    @staticmethod
    def with_round_clear(player: str):
        instance = {PLAYER: player}
        return Message(instance, subkind=ROUND_CLEAR)

    @property
    def kind(self):
        return KIND

    @property
    def card(self):
        return gwent.messaging.card.Message.from_properties(self._instance[CARD])
