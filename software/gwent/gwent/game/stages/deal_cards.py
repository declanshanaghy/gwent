import random
from typing import Callable, List

import gwent.game
import gwent.game.decks
import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play

from gwent.game.constants import PLAYER

DEAL_ANNOUNCEMENTS = [
    "{l1}, leader of {f1}, musters {n1} soldiers for Player 1. "
    "Across the field, {l2} of {f2} rallies {n2} warriors for Player 2. "
    "Let the battle begin!",

    "{l1} of {f1} draws {n1} cards to the fray for Player 1. "
    "{l2} of {f2} answers the call with {n2} for Player 2. "
    "Who will prevail?",

    "The {f1} banner rises! {l1} commands {n1} troops for Player 1. "
    "But {l2} of {f2} stands ready with {n2} for Player 2. "
    "Only one shall triumph!",

    "War drums sound as {l1}, champion of {f1}, marshals {n1} for Player 1. "
    "{l2} of {f2} counters with {n2} for Player 2. "
    "The clash begins!",

    "From the halls of {f1}, {l1} rides forth with {n1} for Player 1. "
    "{l2} of {f2} meets them with {n2} for Player 2. "
    "Steel yourself for battle!",

    "{l1} of {f1} unleashes {n1} upon the battlefield for Player 1. "
    "Not to be outdone, {l2} of {f2} deploys {n2} for Player 2. "
    "May fortune favor the bold!",
]


class DealCards(gwent.game.stages.base.GameStage):
    HAND_SIZE = 5

    _player1_deck = []
    _player2_deck = []
    _player1_hand = []
    _player2_hand = []
    _confirmed = False

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
        self._confirmed = False

        # Supplement decks from starter cards if needed
        self._supplement_deck(self._player1_deck, PLAYER.ONE)
        self._supplement_deck(self._player2_deck, PLAYER.TWO)

        self._deal_hands()

    def _supplement_deck(self, deck, player):
        """Fill in missing leaders and cards from starter cards.

        Owned cards are already in the deck and take priority.
        Starter cards are only added to fill gaps.
        """
        if not deck:
            return

        faction = deck[0].faction
        leaders = [c for c in deck if c.is_leader]
        non_leaders = [c for c in deck if not c.is_leader]

        starters = gwent.game.decks.load_starter_cards(faction)
        if not starters:
            return

        # Existing card names to avoid duplicates
        existing_names = {c.name for c in deck}

        # Add a leader if missing
        if not leaders:
            starter_leaders = [c for c in starters
                               if c.is_leader and c.name not in existing_names]
            if starter_leaders:
                leader = random.choice(starter_leaders)
                deck.append(leader)
                existing_names.add(leader.name)
                self._log.info(f"{player}: added starter leader {leader.name}")

        # Add non-leader cards if below HAND_SIZE
        needed = self.HAND_SIZE - len(non_leaders)
        if needed > 0:
            starter_non_leaders = [c for c in starters
                                   if not c.is_leader
                                   and c.name not in existing_names]
            random.shuffle(starter_non_leaders)
            for card in starter_non_leaders[:needed]:
                deck.append(card)
                existing_names.add(card.name)
                self._log.info(f"{player}: added starter card {card.name}")

    def _deal_hands(self):
        """Randomly deal cards from each deck into each player's hand."""
        self._player1_hand = self._deal_from_deck(self._player1_deck, PLAYER.ONE)
        self._player2_hand = self._deal_from_deck(self._player2_deck, PLAYER.TWO)

        self._log.info({
            'action': 'hands_dealt',
            'player1_hand_size': len(self._player1_hand),
            'player1_hand': [c.name for c in self._player1_hand],
            'player2_hand_size': len(self._player2_hand),
            'player2_hand': [c.name for c in self._player2_hand],
        })

        # Publish deals to players
        self._publish_all_deals()

        # Build summary from templates
        p1_leader = next((c for c in self._player1_deck if c.is_leader), None)
        p2_leader = next((c for c in self._player2_deck if c.is_leader), None)

        summary = random.choice(DEAL_ANNOUNCEMENTS).format(
            l1=p1_leader.name if p1_leader else "An unknown commander",
            f1=p1_leader.faction if p1_leader else self._player1_deck[0].faction,
            n1=len(self._player1_hand),
            l2=p2_leader.name if p2_leader else "An unknown commander",
            f2=p2_leader.faction if p2_leader else self._player2_deck[0].faction,
            n2=len(self._player2_hand),
        )

        # Announce and auto-progress to next stage
        self._publish_prompt_then(summary, self._auto_complete)

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

    def _auto_complete(self):
        """Auto-progress to next stage after announcement finishes."""
        self._log.info("Auto-completing deal stage")
        self.complete(
            self._player1_deck, self._player1_hand,
            self._player2_deck, self._player2_hand)

    def _publish_deal_to_player(self, player: PLAYER, card: gwent.messaging.card.Message):
        """Publish a deal_to_hand message for a card."""
        self._log.info(f"Dealing {card.name} to {player}")
        msg = gwent.messaging.card_play.Message.with_deal_to_hand(str(player), card)
        topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
        self.publish(topic, msg)

    def _publish_all_deals(self):
        """Publish deal_to_hand messages for all dealt cards."""
        for card in self._player1_hand:
            self._publish_deal_to_player(PLAYER.ONE, card)
        for card in self._player2_hand:
            self._publish_deal_to_player(PLAYER.TWO, card)
