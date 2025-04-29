import collections
from typing import Callable

import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice


class RegisterDecks(gwent.game.stages.base.GameStage):
    _decks: dict = None
    _player_count = 2
    _current_player = 1

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_REGISTER_DECKS

    def activate(self, complete: Callable, cancel: Callable):
        super().activate(complete, cancel)
        self._decks = collections.OrderedDict()
        self._current_player = 1
        self.publish_start_prompt()

    def publish_start_prompt(self):
        self.publish_prompt("Players, Register your decks",
                           ok=True, cancel=True, clear_choices=True)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)
        # Only complete if we have decks for all players
        if len(self._decks) >= self._player_count:
            # Get the decks in order
            decks = list(self._decks.values())
            # Call complete with the collected decks
            self.complete(decks[0], decks[1])
        else:
            # If choice received but not enough decks, prompt again
            self.publish_prompt(f"Player {self._current_player}, Register your deck",
                              ok=True, cancel=True, clear_choices=True)

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
        
        # Add the card to the current player's deck
        if self._current_player not in self._decks:
            self._decks[self._current_player] = []
        
        self._decks[self._current_player].append(card)
        
        # Provide feedback
        self.publish_prompt(f"Player {self._current_player} added card: {card.full_name}",
                          ok=True, cancel=True, clear_choices=True)
        
        # Move to next player
        self._current_player += 1
        if self._current_player > self._player_count:
            # All players have registered their decks
            decks = list(self._decks.values())
            self.complete(decks[0], decks[1])
        else:
            # Prompt next player
            self.publish_prompt(f"Player {self._current_player}, Register your deck",
                              ok=True, cancel=True, clear_choices=True)
