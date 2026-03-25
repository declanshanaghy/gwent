"""DisplayWinner stage — game over screen.

Shows the match winner and returns to main menu on OK.
"""

from typing import Callable

import gwent.game
import gwent.game.stages.base
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card
import gwent.messaging.card_play

from gwent.game.constants import PLAYER
from gwent.game.board import Board


class DisplayWinner(gwent.game.stages.base.GameStage):

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_DISPLAY_WINNER

    def activate(self, complete: Callable, cancel: Callable, board: Board):
        super().activate(complete, cancel)

        p1_gems = board.players[PLAYER.ONE].gems
        p2_gems = board.players[PLAYER.TWO].gems
        p1_score = board.calculate_player_score(PLAYER.ONE)
        p2_score = board.calculate_player_score(PLAYER.TWO)

        if p1_gems > 0 and p2_gems <= 0:
            msg = f"Player 1 wins the match! Final score: {p1_score} to {p2_score}."
        elif p2_gems > 0 and p1_gems <= 0:
            msg = f"Player 2 wins the match! Final score: {p2_score} to {p1_score}."
        else:
            msg = f"The match is a draw! Final score: {p1_score} to {p2_score}."

        self._log.info({
            'action': 'display_winner',
            'p1_gems': p1_gems,
            'p2_gems': p2_gems,
            'p1_score': p1_score,
            'p2_score': p2_score,
            'message': msg,
        })

        # Publish final gem state to player displays
        for player in (PLAYER.ONE, PLAYER.TWO):
            gems = board.players[player].gems
            gem_msg = gwent.messaging.card_play.Message.with_update_gems(str(player), gems)
            topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
            self.publish(topic, gem_msg)

        self.publish_prompt(
            f"Game Over! {msg}",
            ok=True, cancel=False, clear_choices=True,
            ok_text="Main Menu")

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)
        if choice.id == 'y':
            self.complete()

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
