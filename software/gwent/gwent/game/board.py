"""Board data model and score calculation for Gwent.

Pure data model — no MQTT, no threading. Tracks the complete board state
including rows, hands, decks, discard piles, weather effects, and gems.
"""

import random
from typing import Optional

import gwent.messaging.card
from gwent.game.constants import PLAYER

ROWS = ("close", "ranged", "siege")


class PlayerBoard:
    """One player's side of the board."""

    def __init__(self):
        self.rows = {row: [] for row in ROWS}
        self.discard = []
        self.gems = 2
        self.passed = False
        self.leader_used = False


class Board:
    """Complete board state for a game. Persists across rounds."""

    def __init__(self, leader1, leader2):
        self.players = {
            PLAYER.ONE: PlayerBoard(),
            PLAYER.TWO: PlayerBoard(),
        }
        self.leaders = {PLAYER.ONE: leader1, PLAYER.TWO: leader2}
        self.factions = {
            PLAYER.ONE: leader1.faction,
            PLAYER.TWO: leader2.faction,
        }
        self.hands = {PLAYER.ONE: [], PLAYER.TWO: []}
        self.decks = {PLAYER.ONE: [], PLAYER.TWO: []}
        self.weather_rows = set()
        self.commander_horn_rows = {PLAYER.ONE: set(), PLAYER.TWO: set()}
        self.current_player = PLAYER.ONE
        self.round_number = 1
        self.spy_doubling = False
        self.medic_random = False
        self.half_weather_penalty = {PLAYER.ONE: False, PLAYER.TWO: False}

    def opponent(self, player):
        return PLAYER.TWO if player == PLAYER.ONE else PLAYER.ONE

    def place_card(self, player, card, row_name):
        """Place a card on a player's board row."""
        self.players[player].rows[row_name].append(card)

    def remove_from_hand(self, player, card):
        """Remove a card from a player's hand by RFID."""
        self.hands[player] = [c for c in self.hands[player] if c.rfid != card.rfid]

    def draw_from_deck(self, player, count=1):
        """Draw cards from a player's deck into their hand. Returns drawn cards."""
        drawn = []
        for _ in range(count):
            if self.decks[player]:
                card = self.decks[player].pop(0)
                self.hands[player].append(card)
                drawn.append(card)
        return drawn

    def find_in_hand(self, player, rfid):
        """Find a card in a player's hand by RFID."""
        for card in self.hands[player]:
            if card.rfid == rfid:
                return card
        return None

    def find_on_board(self, player, rfid):
        """Find a card on a player's board by RFID. Returns (card, row_name) or (None, None)."""
        for row_name in ROWS:
            for card in self.players[player].rows[row_name]:
                if card.rfid == rfid:
                    return card, row_name
        return None, None

    def calculate_row_score(self, player, row_name):
        """Calculate the score for a single row with all modifiers.

        Order of operations:
        1. Base strength (weather reduces non-heroes to 1)
        2. Tight bond multiplier
        3. Commander horn doubling
        4. Morale boost (+1 per morale card to others)
        """
        cards = self.players[player].rows[row_name]
        if not cards:
            return 0

        weather_active = row_name in self.weather_rows
        horn_active = row_name in self.commander_horn_rows[player]

        # Check if any card in the row has commander (specialty or ability)
        has_commander_card = any(
            (c.has_specialty and c.specialty == "commander")
            or (c.has_abilities and "commander" in c.abilities)
            for c in cards
        )

        # Step 1: Base strengths (weather reduces non-heroes to 1,
        # or half strength if half_weather_penalty is active for this player)
        half_weather = self.half_weather_penalty.get(player, False)
        strengths = {}
        for card in cards:
            if not card.strength:
                strengths[card.rfid] = 0
                continue
            if weather_active and not (card.has_specialty and card.specialty == "hero"):
                if half_weather:
                    strengths[card.rfid] = max(1, card.strength // 2)
                else:
                    strengths[card.rfid] = 1
            else:
                strengths[card.rfid] = card.strength

        # Step 1b: Spy doubling — doubles base strength of spy cards
        if self.spy_doubling:
            for card in cards:
                if card.has_abilities and "spy" in card.abilities:
                    strengths[card.rfid] *= 2

        # Step 2: Tight bond — same-name non-hero cards multiply
        # Strip ": N" suffix so "Poor Fucking Infantry: 1" bonds with ": 2"
        def _bond_name(name):
            return name.split(":")[0].strip() if ":" in name else name

        name_counts = {}
        for card in cards:
            if card.has_abilities and "bond" in card.abilities:
                if not (card.has_specialty and card.specialty == "hero"):
                    bn = _bond_name(card.name)
                    name_counts[bn] = name_counts.get(bn, 0) + 1

        for card in cards:
            if card.has_abilities and "bond" in card.abilities:
                if not (card.has_specialty and card.specialty == "hero"):
                    count = name_counts.get(_bond_name(card.name), 1)
                    if count > 1:
                        strengths[card.rfid] *= count

        # Step 3: Morale — each morale card adds +1 to every OTHER non-hero card
        morale_count = sum(
            1 for c in cards
            if c.has_abilities and "morale" in c.abilities
        )
        if morale_count > 0:
            for card in cards:
                if not (card.has_specialty and card.specialty == "hero"):
                    # Each morale card boosts others (not itself if it has morale)
                    if card.has_abilities and "morale" in card.abilities:
                        strengths[card.rfid] += morale_count - 1
                    else:
                        strengths[card.rfid] += morale_count

        # Step 4: Commander horn — doubles row total for non-heroes
        total = sum(strengths.values())
        if horn_active or has_commander_card:
            hero_total = sum(
                strengths[c.rfid] for c in cards
                if c.has_specialty and c.specialty == "hero"
            )
            non_hero_total = total - hero_total
            total = hero_total + (non_hero_total * 2)

        return total

    def calculate_player_score(self, player):
        """Sum of all three rows."""
        return sum(self.calculate_row_score(player, row) for row in ROWS)

    def clear_round(self):
        """Reset board for a new round. Move all row cards to discard, clear effects."""
        for player in (PLAYER.ONE, PLAYER.TWO):
            pb = self.players[player]
            for row_name in ROWS:
                pb.discard.extend(pb.rows[row_name])
                pb.rows[row_name] = []
            pb.passed = False
        self.weather_rows.clear()
        self.commander_horn_rows = {PLAYER.ONE: set(), PLAYER.TWO: set()}
        self.round_number += 1

    def transform_berserkers(self, card_loader):
        """Replace all berserker cards on both players' boards with their
        transformed versions. Returns list of (player, row, old, new) tuples."""
        transforms = []
        for player in (PLAYER.ONE, PLAYER.TWO):
            for row_name in ROWS:
                row = self.players[player].rows[row_name]
                for i, card in enumerate(row):
                    if card.is_berserker and card.transforms_to:
                        new_card = card_loader(card.transforms_to)
                        if new_card:
                            row[i] = new_card
                            transforms.append((player, row_name, card, new_card))
        return transforms

    def destroy_strongest(self, player, row_name=None):
        """Destroy the strongest non-hero card(s) on a player's board.

        If row_name is given, only that row. Otherwise all rows.
        Returns destroyed cards.
        """
        target_rows = [row_name] if row_name else list(ROWS)
        max_strength = 0
        candidates = []

        for rn in target_rows:
            for card in self.players[player].rows[rn]:
                if card.has_specialty and card.specialty == "hero":
                    continue
                s = card.strength or 0
                if s > max_strength:
                    max_strength = s
                    candidates = [(rn, card)]
                elif s == max_strength and s > 0:
                    candidates.append((rn, card))

        destroyed = []
        for rn, card in candidates:
            self.players[player].rows[rn].remove(card)
            self.players[player].discard.append(card)
            destroyed.append(card)

        return destroyed

    def to_dict(self):
        """Serialize board state to a dict for JSON saving."""
        def cards_to_list(cards):
            return [c._instance for c in cards]

        def player_board_to_dict(pb):
            return {
                "rows": {rn: cards_to_list(cards) for rn, cards in pb.rows.items()},
                "discard": cards_to_list(pb.discard),
                "gems": pb.gems,
                "passed": pb.passed,
                "leader_used": pb.leader_used,
            }

        return {
            "players": {
                str(p): player_board_to_dict(pb)
                for p, pb in self.players.items()
            },
            "leaders": {str(p): c._instance for p, c in self.leaders.items()},
            "factions": {str(p): f for p, f in self.factions.items()},
            "hands": {str(p): cards_to_list(h) for p, h in self.hands.items()},
            "decks": {str(p): cards_to_list(d) for p, d in self.decks.items()},
            "weather_rows": list(self.weather_rows),
            "commander_horn_rows": {
                str(p): list(s) for p, s in self.commander_horn_rows.items()
            },
            "current_player": str(self.current_player),
            "round_number": self.round_number,
            "spy_doubling": self.spy_doubling,
            "medic_random": self.medic_random,
            "half_weather_penalty": {
                str(p): v for p, v in self.half_weather_penalty.items()
            },
            "scores": {
                str(p): {
                    "total": self.calculate_player_score(p),
                    "close": self.calculate_row_score(p, "close"),
                    "ranged": self.calculate_row_score(p, "ranged"),
                    "siege": self.calculate_row_score(p, "siege"),
                }
                for p in (PLAYER.ONE, PLAYER.TWO)
            },
        }

    @staticmethod
    def from_dict(data):
        """Deserialize board state from a dict."""
        def dicts_to_cards(lst):
            return [gwent.messaging.card.Message.from_properties(d) for d in lst]

        def player_from_str(s):
            return PLAYER.ONE if s == str(PLAYER.ONE) else PLAYER.TWO

        leader1 = gwent.messaging.card.Message.from_properties(data["leaders"][str(PLAYER.ONE)])
        leader2 = gwent.messaging.card.Message.from_properties(data["leaders"][str(PLAYER.TWO)])
        board = Board(leader1, leader2)

        for p_str, pb_data in data["players"].items():
            player = player_from_str(p_str)
            pb = board.players[player]
            for rn, cards_data in pb_data["rows"].items():
                pb.rows[rn] = dicts_to_cards(cards_data)
            pb.discard = dicts_to_cards(pb_data.get("discard", []))
            pb.gems = pb_data.get("gems", 2)
            pb.passed = pb_data.get("passed", False)
            pb.leader_used = pb_data.get("leader_used", False)

        for p_str, hand_data in data.get("hands", {}).items():
            board.hands[player_from_str(p_str)] = dicts_to_cards(hand_data)
        for p_str, deck_data in data.get("decks", {}).items():
            board.decks[player_from_str(p_str)] = dicts_to_cards(deck_data)

        board.weather_rows = set(data.get("weather_rows", []))
        for p_str, rows in data.get("commander_horn_rows", {}).items():
            board.commander_horn_rows[player_from_str(p_str)] = set(rows)

        cp = data.get("current_player", str(PLAYER.ONE))
        board.current_player = player_from_str(cp)
        board.round_number = data.get("round_number", 1)
        board.spy_doubling = data.get("spy_doubling", False)
        board.medic_random = data.get("medic_random", False)
        hwp = data.get("half_weather_penalty", {})
        for p_str, val in hwp.items():
            board.half_weather_penalty[player_from_str(p_str)] = val

        return board
