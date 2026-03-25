"""DisplayWinner stage — game over screen.

Shows the match winner and returns to main menu on OK.
"""

from typing import Callable

import gwent.game.stages.base
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card

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

        if p1_gems > 0 and p2_gems <= 0:
            msg = "Player 1 wins the match!"
        elif p2_gems > 0 and p1_gems <= 0:
            msg = "Player 2 wins the match!"
        else:
            msg = "The match is a draw!"

        self._log.info({
            'action': 'display_winner',
            'p1_gems': p1_gems,
            'p2_gems': p2_gems,
            'message': msg,
        })

        self.publish_prompt(
            f"Game Over! {msg} Press OK to return to menu.",
            ok=True, cancel=False, clear_choices=True)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)
        if choice.id == 'y' and choice.text == 'ok':
            self.complete()

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
        self.publish_error("Game is over — press OK")
