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
    HAND_SIZE = 8

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
        """Build a mixed deck from owned + starter cards.

        Ensures:
        - At least one leader (owned preferred, starter fallback)
        - ~50/50 mix of owned and starter non-leader cards
        - No duplicate card names
        """
        if not deck:
            return

        faction = deck[0].faction
        starters = gwent.game.decks.load_starter_cards(faction)
        if not starters:
            return

        existing_names = {c.name for c in deck}
        owned_leaders = [c for c in deck if c.is_leader]
        owned_non_leaders = [c for c in deck if not c.is_leader]

        # Ensure at least one leader
        if not owned_leaders:
            starter_leaders = [c for c in starters
                               if c.is_leader and c.name not in existing_names]
            if starter_leaders:
                leader = random.choice(starter_leaders)
                deck.append(leader)
                existing_names.add(leader.name)
                self._log.info(f"{player}: added starter leader {leader.name}")

        # Add starter non-leaders to reach ~50/50 mix
        starter_non_leaders = [c for c in starters
                               if not c.is_leader
                               and c.name not in existing_names]
        random.shuffle(starter_non_leaders)

        # Target: same number of starters as owned non-leaders
        target_starters = max(len(owned_non_leaders), self.HAND_SIZE)
        to_add = starter_non_leaders[:target_starters]

        for card in to_add:
            deck.append(card)
            existing_names.add(card.name)

        self._log.info(f"{player}: deck has {len(owned_non_leaders)} owned + "
                       f"{len(to_add)} starter cards")

    def _deal_hands(self):
        """Randomly deal cards from each deck into each player's hand."""
        self._player1_hand = self._deal_from_deck(self._player1_deck, PLAYER.ONE)
        self._player2_hand = self._deal_from_deck(self._player2_deck, PLAYER.TWO)

        # Check for extra_draw leader abilities
        self._apply_extra_draw(self._player1_deck, self._player1_hand, PLAYER.ONE)
        self._apply_extra_draw(self._player2_deck, self._player2_hand, PLAYER.TWO)

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

    def _apply_extra_draw(self, deck, hand, player):
        """If this player's leader has extra_draw, draw additional cards from deck."""
        leader = next((c for c in deck if c.is_leader), None)
        if not leader or not leader.leader:
            return
        extra = leader.leader.get("extra_draw", 0) if isinstance(leader.leader, dict) else 0
        if not extra:
            return

        dealt_rfids = {c.rfid for c in hand}
        remaining = [c for c in deck if not c.is_leader and c.rfid not in dealt_rfids]
        random.shuffle(remaining)

        drawn = remaining[:extra]
        hand.extend(drawn)
        for c in drawn:
            self._log.info(f"{player}: extra_draw — drew {c.name}")

    def _deal_from_deck(self, deck, player):
        """Randomly select HAND_SIZE cards from the deck with ~50/50 owned/starter mix."""
        # Exclude the leader from the deal pool — leader is played separately
        non_leader = [c for c in deck if not c.is_leader]
        hand_size = min(self.HAND_SIZE, len(non_leader))

        if hand_size < self.HAND_SIZE:
            self._log.warning(
                f"{player}: only {len(non_leader)} non-leader cards in deck, "
                f"dealing {hand_size} instead of {self.HAND_SIZE}")

        owned = [c for c in non_leader if c.has_owner]
        starters = [c for c in non_leader if not c.has_owner]
        random.shuffle(owned)
        random.shuffle(starters)

        # Deal ~50/50: half owned, half starter (round up owned)
        owned_count = min(len(owned), (hand_size + 1) // 2)
        starter_count = min(len(starters), hand_size - owned_count)
        # If one pool is short, take more from the other
        if owned_count + starter_count < hand_size:
            owned_count = min(len(owned), hand_size - starter_count)
        if owned_count + starter_count < hand_size:
            starter_count = min(len(starters), hand_size - owned_count)

        hand = owned[:owned_count] + starters[:starter_count]
        random.shuffle(hand)

        self._log.info(f"Dealt {len(hand)} cards to {player} "
                       f"({owned_count} owned, {starter_count} starter)")
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
