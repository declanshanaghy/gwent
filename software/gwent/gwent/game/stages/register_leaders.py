import collections
from typing import Callable

import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play

from gwent.game.constants import PLAYER


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
        self.publish_start_prompt()

    def publish_start_prompt(self):
        self.publish_prompt("Players, Register your leaders",
            ok=True, cancel=True, clear_choices=True)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

        if choice.id == gwent.messaging.choice.OK_ID:
            if self._leader1 and self._leader2:
                self.complete(self._leader1, self._leader2)
            else:
                self.publish_error('2 Leaders are not registered yet!')
        elif choice.id == gwent.messaging.choice.CANCEL_ID:
            self.cancel()

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)

        if not card.is_leader:
            self.publish_error(f'{card.name} is not a leader')
            return

        # Publish card_play message to the current player's topic
        self._publish_card_to_player(self._current_player, card)

        if self._current_player == PLAYER.ONE:
            self._leader1 = card
            self.publish_prompt(f'Player 1 new leader: {card.name}')
            self._current_player = PLAYER.TWO
        elif self._current_player == PLAYER.TWO:
            self._leader2 = card
            self.publish_prompt(f'Player 2 new leader: {card.name}')
            
        return
    
    def _publish_card_to_player(self, player: PLAYER, card: gwent.messaging.card.Message):
        """
        Publish a card_play message to the player's topic
        
        Args:
            player: The player
            card: The card message to publish
        """
        self._log.info(f"Publishing leader card to {player}: {card.name}")
        
        # Create a card_play message
        card_play_msg = gwent.messaging.card_play.Message.with_add_to_deck(
            player=str(player),
            card=card
        )
        
        # Publish to the player's topic
        player_topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
        self.publish(player_topic, card_play_msg)
