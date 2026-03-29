import random
from typing import Callable

import gwent.game
import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play

from gwent.game.constants import PLAYER

_REGISTER_PROMPTS = [
    "Players, register your leaders. Scan Player 1's leader card.",
    "The battle awaits. Scan Player 1's leader to begin.",
    "Choose your commanders. Player 1, scan your leader.",
    "Destiny calls. Player 1, present your leader card.",
    "The winds of war stir. Scan Player 1's leader card.",
    "Steel yourselves. Player 1, scan your leader to start.",
]

_LEADERS_DONE_PROMPTS = [
    "Leaders registered. Press OK to continue.",
    "Your commanders are set. Press OK to proceed.",
    "Both leaders stand ready. Press OK to begin.",
    "The stage is set. Press OK when ready.",
    "Commanders chosen. Press OK to march forward.",
    "Leaders locked in. Press OK to enter the fray.",
]


class RegisterLeaders(gwent.game.stages.base.GameStage):
    _leader1 = None
    _leader2 = None
    _current_player = PLAYER.ONE

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_REGISTER_LEADERS

    def activate(self, complete: Callable, cancel: Callable):
        super().activate(complete, cancel)
        self._current_player = PLAYER.ONE
        self._leader1 = None
        self._leader2 = None

        self._publish_prompt_then(
            random.choice(_REGISTER_PROMPTS),
            self._ready_for_card)

    def _ready_for_card(self):
        self._awaiting = 'card'

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

        if choice.id == gwent.messaging.choice.OK_ID:
            if self._leader1 and self._leader2:
                self.complete(self._leader1, self._leader2)
            else:
                remaining = 2 - (1 if self._leader1 else 0) - (1 if self._leader2 else 0)
                self.publish_error(f'{remaining} leader(s) not registered yet!')

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)

        if self._awaiting != 'card':
            return

        if not card.is_leader:
            self.publish_error(f'{card.name} is not a leader')
            return

        if self._current_player == PLAYER.TWO and self._leader1 and self._leader1.rfid == card.rfid:
            self.publish_error(f'{card.name} is already Player 1\'s leader')
            return
        if self._current_player == PLAYER.ONE and self._leader2 and self._leader2.rfid == card.rfid:
            self.publish_error(f'{card.name} is already Player 2\'s leader')
            return

        self._publish_card_to_player(self._current_player, card)

        if self._current_player == PLAYER.ONE:
            self._leader1 = card
            self._current_player = PLAYER.TWO
            self._publish_prompt_then(
                f'Player 1 leader: {card.name}. Now scan Player 2\'s leader.',
                self._ready_for_card)
        elif self._current_player == PLAYER.TWO:
            self._leader2 = card
            self._publish_prompt_then(
                f'Player 2 leader: {card.name}. Both leaders registered.',
                self._both_registered)

    def _both_registered(self):
        self._awaiting = 'card'
        self.publish_prompt(
            random.choice(_LEADERS_DONE_PROMPTS),
            ok=True, cancel=False, clear_choices=True,
            ok_text="Continue")

    def _publish_card_to_player(self, player: PLAYER, card: gwent.messaging.card.Message):
        card_play_msg = gwent.messaging.card_play.Message.with_add_to_deck(
            player=str(player), card=card)
        player_topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
        self.publish(player_topic, card_play_msg)
