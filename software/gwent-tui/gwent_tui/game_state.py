"""In-memory game state model. Standalone — no gwent package dependency."""

import logging
import threading
from collections import deque

log = logging.getLogger("gwent_tui.state")


# Player key normalization: MQTT uses "player1"/"player2",
# snapshots use "PLAYER.ONE"/"PLAYER.TWO"
P1_KEYS = {"player1", "PLAYER.ONE", "1"}
P2_KEYS = {"player2", "PLAYER.TWO", "2"}

P1 = "PLAYER.ONE"
P2 = "PLAYER.TWO"


def _normalize_player(key):
    """Normalize player key to P1/P2 constants."""
    if key in P1_KEYS:
        return P1
    if key in P2_KEYS:
        return P2
    # Handle topic-based: gwent/cards/play/1 → "1"
    if str(key).endswith("1"):
        return P1
    if str(key).endswith("2"):
        return P2
    return key


class GameState:
    def __init__(self):
        self.lock = threading.Lock()
        self._reset()

    def _reset(self):
        self.stage = "—"
        self.round_number = 1
        self.current_player = P1
        self.scores = {P1: 0, P2: 0}
        self.gems = {P1: 2, P2: 2}
        self.factions = {P1: "", P2: ""}
        self.leaders = {P1: None, P2: None}
        self.hands = {P1: [], P2: []}
        self.board_rows = {
            P1: {"close": [], "ranged": [], "siege": []},
            P2: {"close": [], "ranged": [], "siege": []},
        }
        self.discard = {P1: [], P2: []}
        self.decks = {P1: [], P2: []}
        self.weather_rows = set()
        self.commander_horn_rows = {P1: set(), P2: set()}
        self.passed = {P1: False, P2: False}
        self.leader_used = {P1: False, P2: False}

        # Event log (recent events for footer)
        self.last_prompt = ""
        self.last_error = ""
        self.last_choices = []
        self.last_announcement = ""
        self.last_card_read = None
        self.event_log = deque(maxlen=20)
        self.connected = False
        self.http_ok = False

    def load_snapshot(self, snapshot):
        """Populate state from a JSON snapshot (HTTP API or SIGUSR1)."""
        with self.lock:
            self._load_snapshot_unlocked(snapshot)
            log.debug("Snapshot loaded: stage=%s round=%d scores=%s",
                       self.stage, self.round_number, self.scores)

    # Stages where game board data is meaningful
    _GAME_STAGES = {"PlayRound", "RoundEnd", "GameOver", "DisplayWinner"}

    def _load_snapshot_unlocked(self, snapshot):
        state = snapshot.get("state", {})
        self.stage = snapshot.get("active_stage", "—") or "—"

        board = state.get("board", {})
        if not board or self.stage not in self._GAME_STAGES:
            self._reset_board()
            return

        self.round_number = board.get("round_number", 1)
        self.current_player = _normalize_player(
            board.get("current_player", P1)
        )
        self.weather_rows = set(board.get("weather_rows", []))

        # Factions
        factions = board.get("factions", {})
        for key, faction in factions.items():
            p = _normalize_player(key)
            self.factions[p] = faction

        # Leaders
        leaders = board.get("leaders", {})
        for key, leader in leaders.items():
            p = _normalize_player(key)
            self.leaders[p] = leader

        # Players (rows, discard, gems, passed)
        players = board.get("players", {})
        for key, pdata in players.items():
            p = _normalize_player(key)
            self.gems[p] = pdata.get("gems", 2)
            self.passed[p] = pdata.get("passed", False)
            self.leader_used[p] = pdata.get("leader_used", False)
            self.discard[p] = list(pdata.get("discard", []))

            rows = pdata.get("rows", {})
            for row_name in ("close", "ranged", "siege"):
                self.board_rows[p][row_name] = list(rows.get(row_name, []))

        # Hands
        hands = board.get("hands", {})
        for key, hand in hands.items():
            p = _normalize_player(key)
            self.hands[p] = list(hand)

        # Decks (filter out leaders — they're shown separately)
        decks = board.get("decks", {})
        for key, deck in decks.items():
            p = _normalize_player(key)
            self.decks[p] = [
                c for c in deck if c.get("specialty") != "leader"
            ]

        # Commander horn rows
        horn_rows = board.get("commander_horn_rows", {})
        for key, rows in horn_rows.items():
            p = _normalize_player(key)
            self.commander_horn_rows[p] = set(rows)

    def _reset_board(self):
        """Reset all game board state to defaults."""
        self.round_number = 1
        self.current_player = P1
        self.scores = {P1: 0, P2: 0}
        self.gems = {P1: 2, P2: 2}
        self.factions = {P1: "", P2: ""}
        self.leaders = {P1: None, P2: None}
        self.hands = {P1: [], P2: []}
        self.board_rows = {
            P1: {"close": [], "ranged": [], "siege": []},
            P2: {"close": [], "ranged": [], "siege": []},
        }
        self.discard = {P1: [], P2: []}
        self.decks = {P1: [], P2: []}
        self.weather_rows = set()
        self.commander_horn_rows = {P1: set(), P2: set()}
        self.passed = {P1: False, P2: False}
        self.leader_used = {P1: False, P2: False}

        # Calculate scores from board data (mirrors board.calculate_player_score)
        for p in (P1, P2):
            self.scores[p] = self._calculate_score(p)

    def _calculate_score(self, player):
        """Calculate player score with all modifiers (weather, bonds, morale, horn)."""
        total = 0
        for row_name in ("close", "ranged", "siege"):
            total += self._calculate_row_score(player, row_name)
        return total

    def _calculate_row_score(self, player, row_name):
        """Calculate score for a single row with modifiers.

        Mirrors board.calculate_row_score from the game engine:
        1. Base strength (weather reduces non-heroes to 1)
        2. Tight bond multiplier (same-name non-hero cards)
        3. Morale boost (+1 per morale card to others)
        4. Commander horn doubling (doubles non-hero total)
        """
        cards = self.board_rows[player].get(row_name, [])
        if not cards:
            return 0

        weather_active = row_name in self.weather_rows
        horn_active = row_name in self.commander_horn_rows.get(player, set())

        def _is_hero(c):
            return c.get("specialty") == "hero"

        def _has_ability(c, ability):
            abilities = c.get("abilities") or []
            return ability in abilities

        def _get_strength(c):
            return c.get("strength") or 0

        # Check if any card in row has commander ability
        has_commander_card = any(
            c.get("specialty") == "commander" or _has_ability(c, "commander")
            for c in cards
        )

        # Step 1: Base strengths (weather reduces non-heroes to 1)
        strengths = {}
        for i, card in enumerate(cards):
            s = _get_strength(card)
            if s == 0:
                strengths[i] = 0
            elif weather_active and not _is_hero(card):
                strengths[i] = 1
            else:
                strengths[i] = s

        # Step 2: Tight bond — only cards with "bond" ability multiply
        from collections import Counter
        name_counts = Counter(
            c.get("name") for c in cards
            if not _is_hero(c) and _has_ability(c, "bond")
        )
        for i, card in enumerate(cards):
            if not _is_hero(card) and _has_ability(card, "bond"):
                count = name_counts.get(card.get("name"), 1)
                if count > 1:
                    strengths[i] *= count

        # Step 3: Morale — each morale card adds +1 to every OTHER non-hero
        morale_count = sum(1 for c in cards if _has_ability(c, "morale"))
        if morale_count > 0:
            for i, card in enumerate(cards):
                if not _is_hero(card):
                    if _has_ability(card, "morale"):
                        strengths[i] += morale_count - 1
                    else:
                        strengths[i] += morale_count

        # Step 4: Commander horn — doubles non-hero total
        row_total = sum(strengths.values())
        if horn_active or has_commander_card:
            hero_total = sum(
                strengths[i] for i, c in enumerate(cards) if _is_hero(c)
            )
            non_hero_total = row_total - hero_total
            row_total = hero_total + (non_hero_total * 2)

        return row_total

    # --- MQTT event handlers ---

    def on_ctrl(self, data):
        """Handle gwent/ctrl stage message."""
        with self.lock:
            stage = data.get("stage", "")
            active = data.get("active", True)
            if active and stage:
                self.stage = stage
                self.event_log.append(f"Stage: {stage}")

    def on_score_update(self, data):
        """Handle card_play/update_score."""
        with self.lock:
            player = _normalize_player(data.get("player", ""))
            score = data.get("score", 0)
            active_turn = data.get("active_turn", False)
            log.debug("Score update: %s=%d active=%s", player, score, active_turn)
            self.scores[player] = score
            if active_turn:
                self.current_player = player

    def on_gems_update(self, data):
        """Handle card_play/update_gems."""
        with self.lock:
            player = _normalize_player(data.get("player", ""))
            gems = data.get("gems", 0)
            self.gems[player] = gems

    def on_deal_to_hand(self, data):
        """Handle card_play/deal_to_hand."""
        with self.lock:
            player = _normalize_player(data.get("player", ""))
            card = data.get("card", {})
            if card:
                self.hands[player].append(card)

    def on_add_to_deck(self, data):
        """Handle card_play/add_to_deck."""
        with self.lock:
            player = _normalize_player(data.get("player", ""))
            card = data.get("card", {})
            if card and card.get("specialty") != "leader":
                self.decks[player].append(card)

    def on_mfd(self, data):
        """Handle gwent/mfd/present."""
        with self.lock:
            subkind = data.get("subkind", "")
            if subkind == "prompt":
                self.last_prompt = data.get("prompt", "")
                self.event_log.append(f"Prompt: {self.last_prompt}")
            elif subkind == "error":
                self.last_error = data.get("error", "")
                self.event_log.append(f"Error: {self.last_error}")
            elif subkind == "choices":
                self.last_choices = data.get("choices", [])

    def on_sfx(self, data):
        """Handle gwent/sfx."""
        with self.lock:
            subkind = data.get("subkind", "")
            if subkind == "announcement":
                self.last_announcement = data.get("announcement", "")
                self.event_log.append(
                    f"Announce: {self.last_announcement}"
                )

    def on_raw_read(self, data):
        """Handle gwent/cards/raw/read."""
        with self.lock:
            self.last_card_read = data
            name = data.get("name", "???")
            self.event_log.append(f"Card read: {name}")
