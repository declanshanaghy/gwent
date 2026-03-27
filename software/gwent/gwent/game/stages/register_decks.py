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
        # Seed each deck with its leader
        self._player1_deck = [leader1]
        self._player2_deck = [leader2]
        self._publish_card_to_player(PLAYER.ONE, leader1)
        self._publish_card_to_player(PLAYER.TWO, leader2)
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
            
        if choice.id == 'y':
            # OK pressed — complete with whatever cards are registered
            p1_count = len(self._player1_deck)
            p2_count = len(self._player2_deck)
            if p1_count < 2 or p2_count < 2:
                # Need at least leader + 1 card per player
                self.publish_error(
                    f"Need more cards! P1: {p1_count}, P2: {p2_count}. "
                    f"Each player needs at least 2 cards (leader + 1).")
            else:
                self._log.info(f"Completing registration: P1={p1_count}, P2={p2_count}")
                self.complete(self._player1_deck, self._player2_deck)
        elif choice.id == 'n':
            # Cancel
            self.cancel()

    MAX_DECK_SIZE = 20

    def _find_card_in_deck(self, deck, card):
        return any(c.rfid == card.rfid for c in deck)

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)

        # Reject blank cards
        if card.is_blank:
            self.publish_error("Blank card — write card data first")
            return

        # Reject leader cards
        if card.is_leader:
            self.publish_error(f"{card.name} is a leader, not a deck card")
            return

        # Reject if this card is already registered as either leader
        if ((self._leader1 and self._leader1.rfid == card.rfid) or
                (self._leader2 and self._leader2.rfid == card.rfid)):
            self.publish_error(f"{card.name} is already registered as a leader")
            return

        # Determine which player this card belongs to by faction
        if self._leader1.faction == card.faction:
            player = PLAYER.ONE
            deck = self._player1_deck
            player_label = "Player 1"
        elif self._leader2.faction == card.faction:
            player = PLAYER.TWO
            deck = self._player2_deck
            player_label = "Player 2"
        else:
            self.publish_error(f"{card.faction} is not a valid faction in this game")
            return

        # Reject duplicates across both decks
        if self._find_card_in_deck(self._player1_deck, card):
            self.publish_error(f"{card.name} is already in Player 1's deck")
            return
        if self._find_card_in_deck(self._player2_deck, card):
            self.publish_error(f"{card.name} is already in Player 2's deck")
            return

        if len(deck) >= self.MAX_DECK_SIZE:
            self.publish_error(f"{player_label}'s deck is full ({self.MAX_DECK_SIZE} cards)")
            return

        deck.append(card)
        self._publish_card_to_player(player, card)
        remaining = self.MAX_DECK_SIZE - len(deck)
        self.publish_prompt(
            f"{player_label} added {card.full_name} ({len(deck)} cards, {remaining} slots left)")
    
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
        player_topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
        self.publish(player_topic, card_play_msg)
