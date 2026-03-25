import random
from typing import Callable, List

import gwent.game
import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play

from gwent.game.constants import PLAYER


class DealCards(gwent.game.stages.base.GameStage):
    HAND_SIZE = 3  # Minimum cards to deal per player

    _player1_deck = []
    _player2_deck = []
    _player1_hand = []
    _player2_hand = []

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_DEAL_CARDS

    def activate(self, complete: Callable, cancel: Callable,
                 deck1: List[gwent.messaging.card.Message],
                 deck2: List[gwent.messaging.card.Message]):
        super().activate(complete, cancel)
        self._player1_deck = list(deck1)
        self._player2_deck = list(deck2)
        self._player1_hand = []
        self._player2_hand = []
        self._deal_hands()

    def _deal_hands(self):
        """Randomly deal cards from each deck into each player's hand."""
        self._player1_hand = self._deal_from_deck(self._player1_deck, PLAYER.ONE)
        self._player2_hand = self._deal_from_deck(self._player2_deck, PLAYER.TWO)

        p1_names = [c.name for c in self._player1_hand]
        p2_names = [c.name for c in self._player2_hand]
        self._log.info({
            'action': 'hands_dealt',
            'player1_hand_size': len(self._player1_hand),
            'player1_hand': p1_names,
            'player2_hand_size': len(self._player2_hand),
            'player2_hand': p2_names,
        })

        # Publish each dealt card to the player's topic
        for card in self._player1_hand:
            self._publish_deal_to_player(PLAYER.ONE, card)
        for card in self._player2_hand:
            self._publish_deal_to_player(PLAYER.TWO, card)

        self.publish_prompt(
            f"Cards dealt! Player 1: {len(self._player1_hand)} cards, "
            f"Player 2: {len(self._player2_hand)} cards. Press OK to continue.",
            ok=True, cancel=True, clear_choices=True)

    def _deal_from_deck(self, deck, player):
        """Randomly select HAND_SIZE cards from the deck."""
        # Exclude the leader from the deal pool — leader is played separately
        non_leader = [c for c in deck if not c.is_leader]
        hand_size = min(self.HAND_SIZE, len(non_leader))

        if hand_size < self.HAND_SIZE:
            self._log.warning(
                f"{player}: only {len(non_leader)} non-leader cards in deck, "
                f"dealing {hand_size} instead of {self.HAND_SIZE}")

        hand = random.sample(non_leader, hand_size)
        self._log.info(f"Dealt {len(hand)} cards to {player}")
        return hand

    def _publish_deal_to_player(self, player: PLAYER, card: gwent.messaging.card.Message):
        """Publish a deal_to_hand message for a card."""
        self._log.info(f"Dealing {card.name} to {player}")
        msg = gwent.messaging.card_play.Message.with_deal_to_hand(str(player), card)
        topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
        self.publish(topic, msg)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

        if choice.id == 'y' and choice.text == 'ok':
            self._log.info("Deal confirmed, completing stage")
            self.complete(
                self._player1_deck, self._player1_hand,
                self._player2_deck, self._player2_hand)
        elif choice.id == 'n' and choice.text == 'cancel':
            self._log.info("Deal canceled")
            self.cancel()

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
        self.publish_error("Cards already dealt — press OK to continue")
