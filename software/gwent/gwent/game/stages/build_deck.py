from typing import Callable

import gwent.game
import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play

from gwent.game.constants import PLAYER


class BuildDeck(gwent.game.stages.base.GameStage):
    _owner = None
    _faction = None
    _deck = []

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_BUILD_DECK

    def activate(self, complete: Callable, cancel: Callable):
        super().activate(complete, cancel)
        self._owner = None
        self._faction = None
        self._deck = []
        self._publish_prompt_then(
            "Scan your first card to start building a deck",
            self._show_save_cancel)

    def _show_save_cancel(self):
        """Show the save/cancel prompt with current deck counts."""
        non_leaders = self._non_leader_count()
        leaders = self._leader_count()
        self.publish_prompt(
            f"Scan cards ({non_leaders} cards, {leaders} leaders)",
            ok=True, cancel=True, clear_choices=True, ok_text='Save')

    def _leader_count(self):
        return sum(1 for c in self._deck if c.is_leader)

    def _non_leader_count(self):
        return sum(1 for c in self._deck if not c.is_leader)

    def _find_card_in_deck(self, card):
        return any(c.rfid == card.rfid for c in self._deck)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

        if choice.id == 'n' and choice.text == 'cancel':
            self._log.info("Build deck canceled")
            self.cancel()
            return

        if choice.id == 'y':
            non_leaders = self._non_leader_count()
            if non_leaders < 5:
                self.publish_error(
                    f"Need at least 5 non-leader cards (have {non_leaders})")
                return
            self._log.info({
                'action': 'build_deck_complete',
                'owner': self._owner,
                'faction': self._faction,
                'total_cards': len(self._deck),
                'leaders': self._leader_count(),
                'non_leaders': non_leaders,
            })
            self.complete(self._owner, self._faction, self._deck)

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)

        # Reject blank cards
        if card.is_blank:
            self.publish_error("Blank card — write card data first")
            return

        # Reject starter cards (use Build Deck for owned cards only)
        if card.is_starter:
            self.publish_error(f"{card.name} is a starter card, not allowed")
            return

        # Reject cards without an owner
        if not card.has_owner:
            self.publish_error(f"{card.name} has no owner, cannot add to deck")
            return

        # First card sets owner and faction, announce the owner
        if self._owner is None:
            self._owner = card.owner
            self._faction = card.faction
            self._log.info({
                'action': 'deck_identity_set',
                'owner': self._owner,
                'faction': self._faction,
            })
            self.publish_prompt(
                f"Building {self._owner}'s {self._faction} deck",
                ok=False, cancel=False, clear_choices=True)
        else:
            # Validate owner matches
            if card.owner != self._owner:
                self.publish_error(
                    f"{card.name} belongs to {card.owner}, not {self._owner}")
                return

            # Validate faction matches
            if card.faction != self._faction:
                self.publish_error(
                    f"{card.name} is {card.faction}, not {self._faction}")
                return

        # Reject duplicates
        if self._find_card_in_deck(card):
            self.publish_error(f"{card.name} is already in this deck")
            return

        self._deck.append(card)
        self._publish_card_to_player(card)

        # Show updated counts with Save/Cancel immediately (non-blocking).
        # Don't use _publish_prompt_then here — rapid card scans would
        # overwrite the deferred action and Save/Cancel would never appear.
        leaders = self._leader_count()
        non_leaders = self._non_leader_count()
        self.publish_prompt(
            f"{card.full_name} added ({non_leaders} cards, {leaders} leaders)",
            ok=True, cancel=True, clear_choices=True, ok_text='Save')

    def _publish_card_to_player(self, card: gwent.messaging.card.Message):
        """Publish a card_play message for visual feedback."""
        card_play_msg = gwent.messaging.card_play.Message.with_add_to_deck(
            str(PLAYER.ONE), card)
        player_topic = gwent.game.make_channel(
            gwent.game.CH_CARDS_PLAY, str(PLAYER.ONE))
        self.publish(player_topic, card_play_msg)
