import collections
from typing import Callable

import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play

from gwent.game.constants import PLAYER

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
        
        self._log.info({
            'action': 'process_choice_details',
            'player1_deck_size': len(self._player1_deck),
            'player2_deck_size': len(self._player2_deck),
            'choice_id': choice.id,
            'choice_text': choice.text
        })
            
        # Determine if either player needs to register more cards
        required_cards = 3
        plr1_needs = required_cards - len(self._player1_deck)
        plr2_needs = required_cards - len(self._player2_deck)
        complete = plr1_needs <= 0 and plr2_needs <= 0

        # Only complete if we have cards registered for all players
        if complete:
            self._log.info("Both players have enough cards, completing stage")
            # Call complete with the registered decks
            self.complete(self._player1_deck, self._player2_deck)
        elif choice.id == 'y' and choice.text == 'ok':
            self._log.info("User clicked OK, checking deck registrations", 
                           extra={"plr1_needs": plr1_needs, "plr2_needs": plr2_needs})

            if plr1_needs > 0:
                self.publish_prompt(f"Player 1, you need to register {plr1_needs} more cards")
            elif plr1_needs > 3:
                self.publish_prompt(f"Player 2, you need to register {plr2_needs} more cards")
            else:

                self.publish_prompt(f"Players, continue registering your deck")

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
        
        if self._leader1.faction == card.faction:
            self._player1_deck.append(card)
            self._publish_card_to_player(PLAYER.ONE, card)
            self.publish_prompt(f"{PLAYER.ONE.display_name} added card: {card.full_name}")        
        elif self._leader2.faction == card.faction:
            self._player2_deck.append(card)
            self._publish_card_to_player(PLAYER.TWO, card)
            self.publish_prompt(f"{PLAYER.TWO.display_name} added card: {card.full_name}")        
        else:
            self._log.error(f"Card {card.full_name} is not a valid faction in this game")
            self.publish_error(f"Card {card.full_name} is not a valid faction in this game")
    
    def _publish_card_to_player(self, player: PLAYER, card: gwent.messaging.card.Message):
        """
        Publish a card_play message to the player's topic
        
        Args:
            player: The Player
            card: The card message to publish
        """
        self._log.info(f"Publishing card to {player}: {card.full_name}")
        
        # Create a card_play message
        card_play_msg = gwent.messaging.card_play.Message.with_add_to_deck(str(player), card)
        
        # Publish to the player's topic
        player_topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, player.topic)
        self.publish(player_topic, card_play_msg)
