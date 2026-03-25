from typing import Callable, List

import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice

from gwent.game.constants import PLAYER


class PlayRound(gwent.game.stages.base.GameStage):
    """Placeholder stage for playing a round. Not yet implemented."""

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_PLAY_ROUND

    def activate(self, complete: Callable, cancel: Callable,
                 deck1, hand1, deck2, hand2):
        super().activate(complete, cancel)
        self._log.info({
            'action': 'play_round_placeholder',
            'deck1_size': len(deck1),
            'hand1_size': len(hand1),
            'deck2_size': len(deck2),
            'hand2_size': len(hand2),
        })
        self.publish_prompt(
            "Play Round — not yet implemented. Press OK to return to menu.",
            ok=True, cancel=True, clear_choices=True)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)
        if choice.id == 'y' and choice.text == 'ok':
            self.complete()
        elif choice.id == 'n' and choice.text == 'cancel':
            self.cancel()

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
        self.publish_error("Play Round not yet implemented")
