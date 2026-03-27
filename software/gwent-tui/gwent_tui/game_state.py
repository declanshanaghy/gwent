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

    _ZERO_ROW_SCORES = {"close": 0, "ranged": 0, "siege": 0}

    def _reset(self):
        self.stage = "—"
        self.round_number = 1
        self.current_player = P1
        self.scores = {P1: 0, P2: 0}
        self.row_scores = {P1: dict(self._ZERO_ROW_SCORES), P2: dict(self._ZERO_ROW_SCORES)}
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

        # Registration state (pre-game stages)
        self.reg_leader1 = None
        self.reg_leader2 = None
        self.reg_deck1 = []
        self.reg_deck2 = []

        # Event log (recent events for footer)
        self.last_prompt = ""
        self.last_error = ""
        self.last_choices = []
        self.last_announcement = ""
        self.last_card_read = None
        self.event_log = deque(maxlen=20)
        self.mqtt_status = "off"    # off, polling, processing, error
        self.http_status = "off"    # off, polling, processing, error

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
            # Load registration data (leaders/decks from pre-game stages)
            self._load_registration_data(state)
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

        # Use server-calculated scores
        server_scores = board.get("scores", {})
        for key, p_scores in server_scores.items():
            p = _normalize_player(key)
            self.scores[p] = p_scores.get("total", 0)
            self.row_scores[p] = {
                "close": p_scores.get("close", 0),
                "ranged": p_scores.get("ranged", 0),
                "siege": p_scores.get("siege", 0),
            }

    def _reset_board(self):
        """Reset all game board state to defaults."""
        self.round_number = 1
        self.current_player = P1
        self.scores = {P1: 0, P2: 0}
        self.row_scores = {P1: dict(self._ZERO_ROW_SCORES), P2: dict(self._ZERO_ROW_SCORES)}
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

    def _load_registration_data(self, state):
        """Load pre-game registration data (leaders/decks being built)."""
        self.reg_leader1 = state.get("leader1")
        self.reg_leader2 = state.get("leader2")
        self.reg_deck1 = state.get("player1_deck", [])
        self.reg_deck2 = state.get("player2_deck", [])

    # --- MQTT event handlers ---

    def on_ctrl(self, data):
        """Handle gwent/ctrl stage message."""
        with self.lock:
            stage = data.get("stage", "")
            active = data.get("active", True)
            if active and stage:
                self.stage = stage
                self.event_log.append(f"Stage: {stage}")

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
