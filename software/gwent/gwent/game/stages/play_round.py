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
    AWAITING_DECOY_CHOICE = 'decoy_choice'
    AWAITING_LEADER_DISCARD = 'leader_discard'

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_PLAY_ROUND

    def activate(self, complete: Callable, cancel: Callable,
                 deck1, hand1, deck2, hand2, board=None):
        super().activate(complete, cancel)

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
                first_reason = f"Scoia'tael coin toss: {self._player_label(self._board.current_player)} goes first."
            else:
                self._board.current_player = PLAYER.ONE
                first_reason = "Player 1 goes first."
        else:
            self._board = board
            cur = self._board.current_player
            label = self._player_label(cur)
            if self._board.round_number == 1:
                first_reason = f"{label} goes first."
            else:
                first_reason = f"Round {self._board.round_number}. {label} goes first as round loser."

        # Log cards in each player's hand
        for card in self._board.hands[PLAYER.ONE]:
            self._log.info(f"Player 1 hand: {card.name} (strength={card.strength}, faction={card.faction})")
        for card in self._board.hands[PLAYER.TWO]:
            self._log.info(f"Player 2 hand: {card.name} (strength={card.strength}, faction={card.faction})")

        self._log.info({
            'action': 'play_round_activated',
            'round': self._board.round_number,
            'current_player': str(self._board.current_player),
            'p1_hand': len(self._board.hands[PLAYER.ONE]),
            'p2_hand': len(self._board.hands[PLAYER.TWO]),
            'p1_gems': self._board.players[PLAYER.ONE].gems,
            'p2_gems': self._board.players[PLAYER.TWO].gems,
        })

        self._publish_prompt_then(first_reason, self._prompt_turn)

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

        self._publish_scores()

        label = self._player_label(cur)
        player_num = "1" if cur == PLAYER.ONE else "2"

        self._awaiting = self.AWAITING_CARD
        self.publish_prompt(
            f"{label}'s turn.",
            ok=True, cancel=False, clear_choices=True,
            ok_text=f"Plr{player_num} Pass")

    def _advance_turn(self):
        """Advance to the next player's turn."""
        cur = self._board.current_player
        self._board.current_player = self._board.opponent(cur)
        self._prompt_turn()

    def _publish_scores(self):
        """Publish updated scores to Player components."""
        cur = self._board.current_player
        for player in (PLAYER.ONE, PLAYER.TWO):
            score = self._board.calculate_player_score(player)
            active = (player == cur)
            msg = gwent.messaging.card_play.Message.with_update_score(str(player), score, active_turn=active)
            topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
            self.publish(topic, msg)

    # --- Card processing ---

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)

        if self._awaiting == self.AWAITING_ROW_CHOICE:
            self.publish_error("Choose a row from the menu first")
            return
        if self._awaiting == self.AWAITING_MEDIC_CHOICE:
            self._process_medic_scan(card)
            return
        if self._awaiting == self.AWAITING_DECOY_CHOICE:
            self._process_decoy_scan(card)
            return
        if self._awaiting == self.AWAITING_LEADER_DISCARD:
            self._process_leader_discard_scan(card)
            return
        if self._awaiting != self.AWAITING_CARD:
            return

        cur = self._board.current_player
        label = self._player_label(cur)

        # Check if it's the player's leader card
        leader = self._board.leaders.get(cur)
        if leader and leader.rfid == card.rfid:
            self._play_leader(leader)
            return

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
            self._play_decoy(hand_card)
        elif hand_card.has_specialty and hand_card.specialty == "mardroeme":
            self._play_mardroeme(hand_card)
        elif hand_card.has_specialty and hand_card.specialty == "commander":
            self._play_commander_card(hand_card)
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
            self._log.info(f"Weather cleared by {card.name}")
            self._publish_prompt_then(
                f"{label}: place {card.name} on discard. Weather cleared!",
                self._advance_turn)
        else:
            for row in card.ranges:
                if row in ROWS:
                    self._board.weather_rows.add(row)
            self._board.remove_from_hand(cur, card)
            self._board.players[cur].discard.append(card)
            self._log.info(f"Weather applied: {card.name} on {card.ranges}")
            self._publish_prompt_then(
                f"{label}: place {card.name} on discard. Weather on {', '.join(card.ranges)}.",
                self._advance_turn)

    def _play_mardroeme(self, card):
        """Mardroeme clears weather."""
        cur = self._board.current_player
        self._board.weather_rows.clear()
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)
        self._publish_prompt_then(
            f"{self._player_label(cur)}: place {card.name} on discard. Weather cleared!",
            self._advance_turn)

    def _play_decoy(self, card):
        """Start the decoy swap flow. Player scans a card on their board to swap."""
        cur = self._board.current_player
        label = self._player_label(cur)

        # Check if player has any non-hero cards on the board to swap with
        has_target = False
        for row_name in ROWS:
            for c in self._board.players[cur].rows[row_name]:
                if not (c.has_specialty and c.specialty == "hero"):
                    has_target = True
                    break
            if has_target:
                break

        if not has_target:
            self.publish_error("No non-hero cards on your board to swap with Decoy")
            return

        self._pending_card = card
        self._awaiting = self.AWAITING_DECOY_CHOICE
        self.publish_prompt(
            f"{label}: Decoy! Scan a card on your board to return to hand.",
            ok=False, cancel=False, clear_choices=True)

    def _process_decoy_scan(self, card):
        """Handle a scanned card during decoy swap."""
        cur = self._board.current_player
        label = self._player_label(cur)
        decoy = self._pending_card

        # Find the scanned card on the player's board
        target, row_name = self._board.find_on_board(cur, card.rfid)
        if not target:
            self.publish_error(f"{card.name} is not on {label}'s board")
            return

        if target.has_specialty and target.specialty == "hero":
            self.publish_error("Cannot swap a hero card with Decoy")
            return

        # Swap: remove target from board, place decoy on that row, return target to hand
        self._board.players[cur].rows[row_name].remove(target)
        self._board.place_card(cur, decoy, row_name)
        self._board.remove_from_hand(cur, decoy)
        self._board.hands[cur].append(target)

        self._pending_card = None
        self._publish_prompt_then(
            f"{label}: place Decoy on {row_name}. {target.name} returned to hand.",
            self._advance_turn)

    def _play_scorch_specialty(self, card):
        """Scorch: destroy highest-strength non-hero cards on the entire board."""
        cur = self._board.current_player
        opp = self._board.opponent(cur)
        destroyed = self._board.destroy_strongest(opp)
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)

        label = self._player_label(cur)
        if destroyed:
            names = ", ".join(c.name for c in destroyed)
            self._publish_prompt_then(
                f"{label}: place {card.name} on discard. Destroyed: {names}",
                self._advance_turn)
        else:
            self._publish_prompt_then(
                f"{label}: place {card.name} on discard. No targets.",
                self._advance_turn)

    def _play_commander_card(self, card):
        """Commander's Horn: double a row's strength."""
        cur = self._board.current_player
        # Commander card has ranges — apply horn to those rows
        for row in card.ranges:
            if row in ROWS:
                self._board.commander_horn_rows[cur].add(row)
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)
        self._publish_prompt_then(
            f"{self._player_label(cur)}: place {card.name} on discard. "
            f"Horn on {', '.join(card.ranges)}.",
            self._advance_turn)

    def _play_leader(self, card):
        """Play a leader card ability."""
        cur = self._board.current_player
        pb = self._board.players[cur]

        if pb.leader_used:
            self.publish_error("Leader ability already used this game")
            return

        pb.leader_used = True
        leader_data = card.leader if card.leader else {}
        label = self._player_label(cur)

        if leader_data.get("weather_ranges"):
            for row in leader_data["weather_ranges"]:
                self._board.weather_rows.add(row)
            prompt = f"{label}: leader ability. Weather on {leader_data['weather_ranges']}."
        elif leader_data.get("commander_ranges"):
            for row in leader_data["commander_ranges"]:
                self._board.commander_horn_rows[cur].add(row)
            prompt = f"{label}: leader ability. Horn on {leader_data['commander_ranges']}."
        elif leader_data.get("draw_opponent_discard"):
            opp = self._board.opponent(cur)
            opp_discard = self._board.players[opp].discard
            if opp_discard:
                self._awaiting = self.AWAITING_LEADER_DISCARD
                self.publish_prompt(
                    f"{label}: leader ability. Scan a card from opponent's discard to take. "
                    f"{len(opp_discard)} available.",
                    ok=False, cancel=False, clear_choices=True)
                return
            else:
                prompt = f"{label}: leader ability. Opponent's discard pile is empty."
        elif leader_data.get("reshuffle_graveyards"):
            opp = self._board.opponent(cur)
            self._board.decks[opp].extend(self._board.players[opp].discard)
            self._board.players[opp].discard = []
            random.shuffle(self._board.decks[opp])
            prompt = f"{label}: leader ability. Reshuffled opponent's discard into deck."
        else:
            prompt = f"{label}: leader ability. {leader_data.get('instructions', 'No effect')}."

        self._publish_prompt_then(prompt, self._advance_turn)

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

        # Build placement instruction
        target_label = f"opponent's {row_name}" if is_spy else row_name
        place_msg = f"{label}: place {card.name} on {target_label}"

        # Process abilities
        if is_spy:
            drawn = self._board.draw_from_deck(cur, 2)
            drawn_names = ", ".join(c.name for c in drawn)
            self._publish_prompt_then(
                f"{place_msg}. Spy! Drew: {drawn_names}",
                self._advance_turn)
            return

        if card.has_abilities and "medic" in card.abilities:
            discard = self._board.players[cur].discard
            non_hero = [c for c in discard if not (c.has_specialty and c.specialty == "hero")]
            if non_hero:
                self._awaiting = self.AWAITING_MEDIC_CHOICE
                self.publish_prompt(
                    f"{place_msg}. Medic! Scan a card from discard to resurrect. {len(non_hero)} available.",
                    ok=False, cancel=False, clear_choices=True)
                return
            else:
                self._publish_prompt_then(
                    f"{place_msg}. No cards to resurrect.",
                    self._advance_turn)
                return

        if card.has_abilities and "muster" in card.abilities:
            self._process_muster(card, row_name)
            return

        # Scorch ability (not specialty): destroy strongest in opponent's same row
        if card.has_abilities and "scorch" in card.abilities:
            opp = self._board.opponent(cur)
            destroyed = self._board.destroy_strongest(opp, row_name)
            if destroyed:
                names = ", ".join(c.name for c in destroyed)
                self._publish_prompt_then(
                    f"{place_msg}. Scorched: {names}",
                    self._advance_turn)
            else:
                self._publish_prompt_then(place_msg, self._advance_turn)
            return

        # Normal card
        self._publish_prompt_then(
            f"{place_msg}, strength {card.strength}.",
            self._advance_turn)

    def _process_leader_discard_scan(self, card):
        """Handle a scanned card during leader draw-from-opponent-discard."""
        cur = self._board.current_player
        label = self._player_label(cur)
        opp = self._board.opponent(cur)
        opp_discard = self._board.players[opp].discard

        drawn = next((c for c in opp_discard if c.rfid == card.rfid), None)
        if not drawn:
            self.publish_error(f"{card.name} is not in opponent's discard pile")
            return

        opp_discard.remove(drawn)
        self._board.hands[cur].append(drawn)
        self._publish_prompt_then(
            f"{label}: took {drawn.name} from opponent's discard. Return to hand.",
            self._advance_turn)

    def _process_medic_scan(self, card):
        """Handle a scanned card during medic resurrection."""
        cur = self._board.current_player
        label = self._player_label(cur)
        discard = self._board.players[cur].discard
        non_hero = [c for c in discard if not (c.has_specialty and c.specialty == "hero")]

        # Find the scanned card in the discard pile
        resurrected = next((c for c in non_hero if c.rfid == card.rfid), None)
        if not resurrected:
            self.publish_error(f"{card.name} is not in {label}'s discard pile")
            return

        discard.remove(resurrected)
        self._board.hands[cur].append(resurrected)
        self._publish_prompt_then(
            f"{label}: {resurrected.name} resurrected! Return to hand.",
            self._advance_turn)

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

        label = self._player_label(cur)
        if mustered:
            names = ", ".join(c.name for c in mustered)
            self._publish_prompt_then(
                f"{label}: place {card.name} on {row_name}. "
                f"Muster! Also place: {names}",
                self._advance_turn)
        else:
            self._publish_prompt_then(
                f"{label}: place {card.name} on {row_name}.",
                self._advance_turn)

    # --- Choice processing ---

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

        if self._awaiting == self.AWAITING_CARD:
            if choice.id == 'y':
                # Player passes
                cur = self._board.current_player
                self._board.players[cur].passed = True
                self._log.info(f"{self._player_label(cur)} passed")
                self._board.current_player = self._board.opponent(cur)
                self._publish_prompt_then(
                    f"{self._player_label(cur)} passed!",
                    self._prompt_turn)

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
            # Medic resurrection is handled by scanning, ignore MFD choices
            pass
