"""PlayRound stage — the core game loop.

Players alternate scanning cards from their hand to place on the board,
or pressing OK to pass. When both players have passed, the round ends.
"""

import random
from typing import Callable, List

import gwent.game
import gwent.game.stages.base
import gwent.game.board
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play
import gwent.messaging.mfd

from gwent.game.constants import PLAYER
from gwent.game.board import Board, ROWS


class PlayRound(gwent.game.stages.base.GameStage):
    """Turn-based card play stage."""

    # Internal state machine
    AWAITING_CARD = 'card'
    AWAITING_ROW_CHOICE = 'row_choice'
    AWAITING_MEDIC_CHOICE = 'medic_choice'

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_PLAY_ROUND

    def activate(self, complete: Callable, cancel: Callable,
                 deck1, hand1, deck2, hand2, board=None):
        super().activate(complete, cancel)

        self._awaiting = None
        self._pending_card = None

        if board is None:
            # First round — extract leaders from decks
            leader1 = next((c for c in deck1 if c.is_leader), None)
            leader2 = next((c for c in deck2 if c.is_leader), None)
            self._board = Board(leader1, leader2)

            # Populate hands/decks (exclude leaders from hand)
            self._board.hands[PLAYER.ONE] = [c for c in hand1 if not c.is_leader]
            self._board.hands[PLAYER.TWO] = [c for c in hand2 if not c.is_leader]
            self._board.decks[PLAYER.ONE] = [c for c in deck1 if c not in hand1]
            self._board.decks[PLAYER.TWO] = [c for c in deck2 if c not in hand2]

            # Scoai'tel faction check — coin toss for first player
            scoaitel_p1 = self._board.factions[PLAYER.ONE] == "Scoia'tael"
            scoaitel_p2 = self._board.factions[PLAYER.TWO] == "Scoia'tael"
            if scoaitel_p1 or scoaitel_p2:
                self._board.current_player = random.choice([PLAYER.ONE, PLAYER.TWO])
                self._log.info(f"Scoai'tel coin toss: {self._board.current_player} goes first")
            else:
                self._board.current_player = PLAYER.ONE
        else:
            self._board = board

        self._log.info({
            'action': 'play_round_activated',
            'round': self._board.round_number,
            'current_player': str(self._board.current_player),
            'p1_hand': len(self._board.hands[PLAYER.ONE]),
            'p2_hand': len(self._board.hands[PLAYER.TWO]),
            'p1_gems': self._board.players[PLAYER.ONE].gems,
            'p2_gems': self._board.players[PLAYER.TWO].gems,
        })

        self._prompt_turn()

    # --- Turn management ---

    def _player_label(self, player):
        return "Player 1" if player == PLAYER.ONE else "Player 2"

    def _prompt_turn(self):
        """Prompt the current player to play a card or pass."""
        p1_passed = self._board.players[PLAYER.ONE].passed
        p2_passed = self._board.players[PLAYER.TWO].passed

        if p1_passed and p2_passed:
            self._log.info("Both players passed, completing round")
            self.complete(self._board)
            return

        cur = self._board.current_player
        # Skip if current player already passed
        if self._board.players[cur].passed:
            self._board.current_player = self._board.opponent(cur)
            cur = self._board.current_player

        hand_size = len(self._board.hands[cur])
        p1_score = self._board.calculate_player_score(PLAYER.ONE)
        p2_score = self._board.calculate_player_score(PLAYER.TWO)
        label = self._player_label(cur)

        self._awaiting = self.AWAITING_CARD
        self.publish_prompt(
            f"Round {self._board.round_number} — {label}'s turn. "
            f"Hand: {hand_size} cards. "
            f"Score: P1={p1_score} P2={p2_score}. "
            f"Scan card or OK to pass.",
            ok=True, cancel=False, clear_choices=True)

    def _advance_turn(self):
        """Recalculate scores and advance to the next player's turn."""
        self._publish_scores()
        cur = self._board.current_player
        self._board.current_player = self._board.opponent(cur)
        self._prompt_turn()

    def _publish_scores(self):
        """Publish updated scores to Player components."""
        for player in (PLAYER.ONE, PLAYER.TWO):
            score = self._board.calculate_player_score(player)
            msg = gwent.messaging.card_play.Message.with_update_score(str(player), score)
            topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
            self.publish(topic, msg)

    # --- Card processing ---

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)

        if self._awaiting == self.AWAITING_ROW_CHOICE:
            self.publish_error("Choose a row from the menu first")
            return
        if self._awaiting == self.AWAITING_MEDIC_CHOICE:
            self.publish_error("Choose a card from the discard pile first")
            return
        if self._awaiting != self.AWAITING_CARD:
            return

        cur = self._board.current_player
        label = self._player_label(cur)

        # Validate card is in current player's hand
        hand_card = self._board.find_in_hand(cur, card.rfid)
        if not hand_card:
            self.publish_error(f"{card.name} is not in {label}'s hand")
            return

        # Route by card type
        if hand_card.is_weather:
            self._play_weather(hand_card)
        elif hand_card.has_specialty and hand_card.specialty == "scorch":
            self._play_scorch_specialty(hand_card)
        elif hand_card.has_specialty and hand_card.specialty == "decoy":
            self.publish_error("Decoy not yet implemented")
        elif hand_card.has_specialty and hand_card.specialty == "mardroeme":
            self._play_mardroeme(hand_card)
        elif hand_card.has_specialty and hand_card.specialty == "commander":
            self._play_commander_card(hand_card)
        elif hand_card.is_leader:
            self._play_leader(hand_card)
        else:
            self._play_unit_card(hand_card)

    def _play_weather(self, card):
        """Apply a weather effect."""
        cur = self._board.current_player
        label = self._player_label(cur)

        if card.name == "Clear Weather" or (card.has_specialty and card.specialty == "mardroeme"):
            self._board.weather_rows.clear()
            self._board.remove_from_hand(cur, card)
            self._board.players[cur].discard.append(card)
            self.publish_prompt(f"{label} played {card.name} — weather cleared!")
            self._log.info(f"Weather cleared by {card.name}")
        else:
            for row in card.ranges:
                if row in ROWS:
                    self._board.weather_rows.add(row)
            self._board.remove_from_hand(cur, card)
            self._board.players[cur].discard.append(card)
            self.publish_prompt(f"{label} played {card.name} — weather on {', '.join(card.ranges)}")
            self._log.info(f"Weather applied: {card.name} on {card.ranges}")

        self._advance_turn()

    def _play_mardroeme(self, card):
        """Mardroeme clears weather."""
        cur = self._board.current_player
        self._board.weather_rows.clear()
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)
        self.publish_prompt(f"{self._player_label(cur)} played {card.name} — weather cleared!")
        self._advance_turn()

    def _play_scorch_specialty(self, card):
        """Scorch: destroy highest-strength non-hero cards on the entire board."""
        cur = self._board.current_player
        opp = self._board.opponent(cur)
        destroyed = self._board.destroy_strongest(opp)
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)

        if destroyed:
            names = ", ".join(c.name for c in destroyed)
            self.publish_prompt(f"{self._player_label(cur)} played Scorch! Destroyed: {names}")
        else:
            self.publish_prompt(f"{self._player_label(cur)} played Scorch — no targets")
        self._advance_turn()

    def _play_commander_card(self, card):
        """Commander's Horn: double a row's strength."""
        cur = self._board.current_player
        # Commander card has ranges — apply horn to those rows
        for row in card.ranges:
            if row in ROWS:
                self._board.commander_horn_rows[cur].add(row)
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)
        self.publish_prompt(
            f"{self._player_label(cur)} played {card.name} — "
            f"horn on {', '.join(card.ranges)}")
        self._advance_turn()

    def _play_leader(self, card):
        """Play a leader card ability."""
        cur = self._board.current_player
        pb = self._board.players[cur]

        if pb.leader_used:
            self.publish_error("Leader ability already used this game")
            return

        pb.leader_used = True
        leader_data = card.leader if card.leader else {}

        if leader_data.get("weather_ranges"):
            for row in leader_data["weather_ranges"]:
                self._board.weather_rows.add(row)
            self.publish_prompt(
                f"{self._player_label(cur)} used leader: "
                f"weather on {leader_data['weather_ranges']}")
        elif leader_data.get("commander_ranges"):
            for row in leader_data["commander_ranges"]:
                self._board.commander_horn_rows[cur].add(row)
            self.publish_prompt(
                f"{self._player_label(cur)} used leader: "
                f"horn on {leader_data['commander_ranges']}")
        elif leader_data.get("draw_opponent_discard"):
            opp = self._board.opponent(cur)
            opp_discard = self._board.players[opp].discard
            if opp_discard:
                drawn = opp_discard.pop(0)
                self._board.hands[cur].append(drawn)
                self.publish_prompt(
                    f"{self._player_label(cur)} used leader: "
                    f"drew {drawn.name} from opponent's discard")
            else:
                self.publish_prompt(
                    f"{self._player_label(cur)} used leader: "
                    f"opponent's discard pile is empty")
        elif leader_data.get("reshuffle_graveyards"):
            opp = self._board.opponent(cur)
            self._board.decks[opp].extend(self._board.players[opp].discard)
            self._board.players[opp].discard = []
            random.shuffle(self._board.decks[opp])
            self.publish_prompt(
                f"{self._player_label(cur)} used leader: "
                f"reshuffled opponent's discard into deck")
        else:
            self.publish_prompt(
                f"{self._player_label(cur)} used leader: {leader_data.get('instructions', 'no effect')}")

        self._board.remove_from_hand(cur, card)
        self._advance_turn()

    def _play_unit_card(self, card):
        """Play a normal unit card (with strength)."""
        if card.has_abilities and "agile" in card.abilities and len(card.ranges) > 1:
            # Agile — player chooses row
            self._pending_card = card
            self._awaiting = self.AWAITING_ROW_CHOICE
            choices = []
            for i, row in enumerate(card.ranges):
                choices.append(
                    gwent.messaging.choice.Message.from_properties(str(i), row.capitalize()))
            mfd = gwent.messaging.mfd.Message.with_choices(choices, clear_prompt=False)
            self.publish(gwent.game.CH_MFD_PRESENT, mfd)
            self.publish_prompt(f"Choose row for {card.name}")
        else:
            # Single range
            row = card.ranges[0] if card.ranges else "close"
            self._place_card_on_row(card, row)

    def _place_card_on_row(self, card, row_name):
        """Place a unit card on the board and process abilities."""
        cur = self._board.current_player
        label = self._player_label(cur)

        # Spy: place on opponent's board
        is_spy = card.has_abilities and "spy" in card.abilities
        target = self._board.opponent(cur) if is_spy else cur

        self._board.place_card(target, card, row_name)
        self._board.remove_from_hand(cur, card)

        self._log.info({
            'action': 'card_placed',
            'player': str(cur),
            'target': str(target),
            'card': card.name,
            'row': row_name,
            'spy': is_spy,
        })

        # Process abilities
        if is_spy:
            drawn = self._board.draw_from_deck(cur, 2)
            drawn_names = ", ".join(c.name for c in drawn)
            self.publish_prompt(
                f"{label} played spy {card.name} on opponent's {row_name}. "
                f"Drew: {drawn_names}")
            self._advance_turn()
            return

        if card.has_abilities and "medic" in card.abilities:
            discard = self._board.players[cur].discard
            non_hero = [c for c in discard if not (c.has_specialty and c.specialty == "hero")]
            if non_hero:
                self._awaiting = self.AWAITING_MEDIC_CHOICE
                choices = []
                for i, dc in enumerate(non_hero):
                    choices.append(
                        gwent.messaging.choice.Message.from_properties(str(i), dc.name))
                mfd = gwent.messaging.mfd.Message.with_choices(choices, clear_prompt=False)
                self.publish(gwent.game.CH_MFD_PRESENT, mfd)
                self.publish_prompt(f"{label} played medic {card.name}. Choose a card to resurrect.")
                return
            else:
                self.publish_prompt(f"{label} played {card.name} on {row_name} (no cards to resurrect)")
                self._advance_turn()
                return

        if card.has_abilities and "muster" in card.abilities:
            self._process_muster(card, row_name)
            self._advance_turn()
            return

        # Scorch ability (not specialty): destroy strongest in opponent's same row
        if card.has_abilities and "scorch" in card.abilities:
            opp = self._board.opponent(cur)
            destroyed = self._board.destroy_strongest(opp, row_name)
            if destroyed:
                names = ", ".join(c.name for c in destroyed)
                self.publish_prompt(
                    f"{label} played {card.name} on {row_name}. Scorched: {names}")
            else:
                self.publish_prompt(f"{label} played {card.name} on {row_name}")
            self._advance_turn()
            return

        # Normal card
        self.publish_prompt(
            f"{label} played {card.name} (str:{card.strength}) on {row_name}")
        self._advance_turn()

    def _process_muster(self, card, row_name):
        """Auto-play all cards with the same name from hand and deck."""
        cur = self._board.current_player
        muster_name = card.name.split(":")[0].strip()  # "Arachas: 1" → "Arachas"
        mustered = []

        # From hand
        for hc in list(self._board.hands[cur]):
            if hc.rfid != card.rfid and hc.name.startswith(muster_name):
                row = hc.ranges[0] if hc.ranges else row_name
                self._board.place_card(cur, hc, row)
                self._board.remove_from_hand(cur, hc)
                mustered.append(hc)

        # From deck
        for dc in list(self._board.decks[cur]):
            if dc.name.startswith(muster_name):
                row = dc.ranges[0] if dc.ranges else row_name
                self._board.place_card(cur, dc, row)
                self._board.decks[cur].remove(dc)
                mustered.append(dc)

        if mustered:
            names = ", ".join(c.name for c in mustered)
            self.publish_prompt(
                f"{self._player_label(cur)} played {card.name} — "
                f"mustered: {names}")
        else:
            self.publish_prompt(
                f"{self._player_label(cur)} played {card.name} on {row_name}")

    # --- Choice processing ---

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

        if self._awaiting == self.AWAITING_CARD:
            if choice.id == 'y' and choice.text == 'ok':
                # Player passes
                cur = self._board.current_player
                self._board.players[cur].passed = True
                self._log.info(f"{self._player_label(cur)} passed")
                self.publish_prompt(f"{self._player_label(cur)} passed!")
                self._board.current_player = self._board.opponent(cur)
                self._prompt_turn()

        elif self._awaiting == self.AWAITING_ROW_CHOICE:
            # Agile card row selection
            card = self._pending_card
            if card and card.ranges:
                idx = int(choice.id) if choice.id.isdigit() else 0
                idx = min(idx, len(card.ranges) - 1)
                row = card.ranges[idx]
                self._awaiting = None
                self._pending_card = None
                self._place_card_on_row(card, row)

        elif self._awaiting == self.AWAITING_MEDIC_CHOICE:
            # Medic card resurrection
            cur = self._board.current_player
            discard = self._board.players[cur].discard
            non_hero = [c for c in discard if not (c.has_specialty and c.specialty == "hero")]
            idx = int(choice.id) if choice.id.isdigit() else 0
            idx = min(idx, len(non_hero) - 1)
            if non_hero:
                resurrected = non_hero[idx]
                discard.remove(resurrected)
                # Place resurrected card on its row
                row = resurrected.ranges[0] if resurrected.ranges else "close"
                self._board.place_card(cur, resurrected, row)
                self.publish_prompt(
                    f"{self._player_label(cur)} resurrected {resurrected.name} to {row}")
            self._awaiting = None
            self._advance_turn()
