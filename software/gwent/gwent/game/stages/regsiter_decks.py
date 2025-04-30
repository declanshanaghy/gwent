import collections
from typing import Callable

import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play

from software.gwent.gwent.game.controller import PLAYER

class RegisterDecks(gwent.game.stages.base.GameStage):
    _leader1 = None
    _leader2 = None
    _player1_deck = []
    _player2_deck = []

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_REGISTER_DECKS

    def activate(self, complete: Callable, cancel: Callable, leader1: gwent.messaging.card.Message, leader2: gwent.messaging.card.Message):
        super().activate(complete, cancel)
        self._leader1 = leader1
        self._leader2 = leader2
        self._player1_deck = []
        self._player2_deck = []
        self.publish_start_prompt()

    def publish_start_prompt(self):
        self.publish_prompt("Players, Register your decks",
                           ok=True, cancel=True, clear_choices=True)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)
            
        # Only complete if we have cards registered for all players
        if len(self._player1_deck) >= 3 and len(self._player2_deck) > 3:
            # Call complete with the registered decks
            self.complete(self._player1_deck, self._player1_deck)
        else:
            # If choice received but not enough cards registered, prompt again
            self.publish_prompt(f"Players, continue registering your deck")

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
        
        if self._leader1.faction == card.faction:
            self._player1_deck.append(card)
            self._publish_card_to_player(PLAYER.ONE, card)
            self.publish_prompt(f"{PLAYER.ONE} added card: {card.full_name}")        
        elif self._leader2.faction == card.faction:
            self._player2_deck.append(card)
            self._publish_card_to_player(PLAYER.TWO, card)
            self.publish_prompt(f"{PLAYER.TWO} added card: {card.full_name}")        
        else:
            self._log.error(f"Card {card.full_name} is not a valid faction in this game")
            self.publish_error(f"Card {card.full_name} is not a valid faction in this game")
    
    def _publish_card_to_player(self, player: str, card: gwent.messaging.card.Message):
        """
        Publish a card_play message to the player's topic
        
        Args:
            player: The Player
            card: The card message to publish
        """
        self._log.info(f"Publishing card to {player}: {card.full_name}")
        
        # Create a card_play message
        card_play_msg = gwent.messaging.card_play.Message.with_add_to_deck(
            player=str(player),
            card=card
        )
        
        # Publish to the player's topic
        player_topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
        self.publish(player_topic, card_play_msg)
