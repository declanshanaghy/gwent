"""In-memory game state model. Standalone — no gwent package dependency."""

import logging
import threading
import time
from collections import deque
from datetime import datetime

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

    # How long highlights persist (seconds)
    HIGHLIGHT_TTL = 2.0

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
        self.initial_deck_sizes = {P1: 0, P2: 0}
        self.weather_rows = set()
        self.half_weather_penalty = {P1: False, P2: False}
        self.commander_horn_rows = {P1: set(), P2: set()}
        self.passed = {P1: False, P2: False}
        self.leader_used = {P1: False, P2: False}

        # Registration state (pre-game stages)
        self.reg_leader1 = None
        self.reg_leader2 = None
        self.reg_deck1 = []
        self.reg_deck2 = []

        # Deal tracking (cards dealt in real-time via MQTT)
        self.dealt_cards = {P1: [], P2: []}

        # Event log (recent events for footer)
        self.last_prompt = ""
        self.last_prompt_time = ""
        self.last_error = ""
        self.last_error_time = ""
        self.last_choices = []
        self.last_announcement = ""
        self.last_card_read = None
        self.last_card_read_time = ""
        self._event_log = deque(maxlen=20)
        self.mqtt_status = "off"    # off, polling, processing, error
        self.http_status = "off"    # off, polling, processing, error
        self.server_tts = ""       # server TTS provider name (from snapshot)
        self.player_names = {P1: "Player 1", P2: "Player 2"}

        # Change highlights: {key: expire_time}
        # Keys: "board:{player}:{row}:{card_name}", "hand:{player}:{card_name}",
        #        "discard:{player}:{card_name}", "score:{player}", "gems:{player}",
        #        "deck:{player}", "weather:{row}"
        #        "removed:hand:{player}:{card_name}" — ghost entries for removed cards
        self.highlights = {}
        # Ghost cards: temporarily shown as removed (red highlight then vanish)
        # {("hand", player): [card_dict, ...], ("board", player, row): [...]}
        self.ghosts = {}

        # Move timing
        self._turn_start = time.monotonic()
        self._prev_player = None
        self.move_times = {P1: [], P2: []}  # seconds per move

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
        self.server_tts = snapshot.get("tts_provider", "") or ""

        # Player display names (set via PUT /players)
        names = snapshot.get("player_names", {})
        for key, name in names.items():
            p = _normalize_player(key)
            self.player_names[p] = name

        board = state.get("board", {})
        if not board or self.stage not in self._GAME_STAGES:
            self._reset_board()
            # Load registration data (leaders/decks from pre-game stages)
            self._load_registration_data(state)
            return

        # Detect changes before overwriting state
        self._detect_changes(board)

        self.round_number = board.get("round_number", 1)
        new_player = _normalize_player(board.get("current_player", P1))

        # Track move duration when the turn changes
        now = time.monotonic()
        if (self._prev_player is not None
                and self._prev_player != new_player
                and self._prev_player in (P1, P2)):
            elapsed = now - self._turn_start
            if 0.5 < elapsed < 600:  # ignore sub-second glitches and >10min stalls
                self.move_times[self._prev_player].append(elapsed)
        if self._prev_player != new_player:
            self._turn_start = now
        self._prev_player = new_player
        self.current_player = new_player

        self.weather_rows = set(board.get("weather_rows", []))
        hwp = board.get("half_weather_penalty", {})
        for key, val in hwp.items():
            p = _normalize_player(key)
            self.half_weather_penalty[p] = val

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
            filtered = [c for c in deck if c.get("specialty") != "leader"]
            # Capture initial deck size on first load (before any draws)
            if self.initial_deck_sizes[p] == 0 and filtered:
                self.initial_deck_sizes[p] = len(filtered)
            self.decks[p] = filtered

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

    def is_highlighted(self, key):
        """Check if a key is currently highlighted (within TTL)."""
        expire = self.highlights.get(key)
        if expire is None:
            return False
        if time.monotonic() > expire:
            del self.highlights[key]
            return False
        return True

    def _highlight(self, key):
        """Mark a key as highlighted."""
        self.highlights[key] = time.monotonic() + self.HIGHLIGHT_TTL

    def _expire_ghosts(self):
        """Remove expired ghost entries."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self.ghosts.items() if now > exp]
        for k in expired:
            del self.ghosts[k]

    def get_ghosts(self, *ghost_key):
        """Get ghost cards for a key, or empty list if expired."""
        entry = self.ghosts.get(ghost_key)
        if entry is None:
            return []
        cards, expire = entry
        if time.monotonic() > expire:
            del self.ghosts[ghost_key]
            return []
        return cards

    def _detect_changes(self, board):
        """Compare new board state against current and highlight differences."""
        now_ttl = time.monotonic() + self.HIGHLIGHT_TTL

        players = board.get("players", {})
        hands = board.get("hands", {})
        decks = board.get("decks", {})
        server_scores = board.get("scores", {})

        for key, pdata in players.items():
            p = _normalize_player(key)

            # Gems changed
            new_gems = pdata.get("gems", 2)
            if new_gems != self.gems.get(p, 2):
                self._highlight(f"gems:{p}")

            # Board rows changed — detect new cards
            rows = pdata.get("rows", {})
            for row_name in ("close", "ranged", "siege"):
                old_names = {c.get("name") for c in self.board_rows[p].get(row_name, [])}
                new_cards = rows.get(row_name, [])
                for c in new_cards:
                    if c.get("name") not in old_names:
                        self._highlight(f"board:{p}:{row_name}:{c.get('name')}")

            # Discard changed — detect new and removed cards
            old_disc_names = {c.get("name") for c in self.discard.get(p, [])}
            new_disc = pdata.get("discard", [])
            new_disc_names = {c.get("name") for c in new_disc}
            for c in new_disc:
                if c.get("name") not in old_disc_names:
                    self._highlight(f"discard:{p}:{c.get('name')}")
            # Track removed discard cards as ghosts (medic resurrect)
            removed_disc = old_disc_names - new_disc_names
            if removed_disc:
                ghost_key = ("discard", p)
                ghosts = []
                for c in self.discard.get(p, []):
                    if c.get("name") in removed_disc:
                        ghosts.append(c)
                        self._highlight(f"removed:discard:{p}:{c.get('name')}")
                if ghosts:
                    self.ghosts[ghost_key] = (ghosts, time.monotonic() + self.HIGHLIGHT_TTL)

        # Hands — detect removed cards (played) and new cards (drawn)
        # Clear expired ghosts first
        self._expire_ghosts()
        for key, hand in hands.items():
            p = _normalize_player(key)
            old_names = {c.get("name") for c in self.hands.get(p, [])}
            new_names = {c.get("name") for c in hand}
            for name in new_names - old_names:
                self._highlight(f"hand:{p}:{name}")
            # Track removed cards as ghosts (briefly visible with red highlight)
            removed_names = old_names - new_names
            if removed_names:
                ghost_key = ("hand", p)
                ghosts = []
                for c in self.hands.get(p, []):
                    if c.get("name") in removed_names:
                        ghosts.append(c)
                        self._highlight(f"removed:hand:{p}:{c.get('name')}")
                if ghosts:
                    self.ghosts[ghost_key] = (ghosts, time.monotonic() + self.HIGHLIGHT_TTL)
            if old_names != new_names:
                self._highlight(f"hand_count:{p}")

        # Decks — detect size change and removed cards (spy draws)
        for key, deck in decks.items():
            p = _normalize_player(key)
            old_deck = [c for c in self.decks.get(p, [])]
            new_filtered = [c for c in deck if c.get("specialty") != "leader"]
            old_size = len(old_deck)
            new_size = len(new_filtered)
            if old_size != new_size:
                self._highlight(f"deck:{p}")
            # Track removed deck cards as ghosts (drawn to hand)
            old_deck_names = {c.get("name") for c in old_deck}
            new_deck_names = {c.get("name") for c in new_filtered}
            removed_deck = old_deck_names - new_deck_names
            if removed_deck:
                ghost_key = ("deck", p)
                ghosts = []
                for c in old_deck:
                    if c.get("name") in removed_deck:
                        ghosts.append(c)
                        self._highlight(f"removed:deck:{p}:{c.get('name')}")
                if ghosts:
                    self.ghosts[ghost_key] = (ghosts, time.monotonic() + self.HIGHLIGHT_TTL)

        # Scores changed
        for key, p_scores in server_scores.items():
            p = _normalize_player(key)
            new_total = p_scores.get("total", 0)
            if new_total != self.scores.get(p, 0):
                self._highlight(f"score:{p}")

        # Weather changed
        new_weather = set(board.get("weather_rows", []))
        if new_weather != self.weather_rows:
            for row in new_weather.symmetric_difference(self.weather_rows):
                self._highlight(f"weather:{row}")

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
        self.initial_deck_sizes = {P1: 0, P2: 0}
        self.weather_rows = set()
        self.half_weather_penalty = {P1: False, P2: False}
        self.commander_horn_rows = {P1: set(), P2: set()}
        self.passed = {P1: False, P2: False}
        self.leader_used = {P1: False, P2: False}

    def _load_registration_data(self, state):
        """Load pre-game registration data (leaders/decks being built)."""
        self.reg_leader1 = state.get("leader1")
        self.reg_leader2 = state.get("leader2")
        self.reg_deck1 = state.get("player1_deck", [])
        self.reg_deck2 = state.get("player2_deck", [])

    def avg_move_time(self, player):
        """Average move time in seconds for a player, or 0 if no moves."""
        times = self.move_times.get(player, [])
        return sum(times) / len(times) if times else 0

    def move_count(self, player):
        """Number of completed moves for a player."""
        return len(self.move_times.get(player, []))

    @property
    def event_log(self):
        """Read-only access to event log. Use log_event() to add entries."""
        return self._event_log

    def _log_event(self, msg):
        """Append a timestamped event to the log."""
        ts = datetime.now().strftime("%H:%M:%S")
        self._event_log.append(f"{ts} {msg}")

    # --- MQTT event handlers ---

    def on_ctrl(self, data):
        """Handle gwent/ctrl stage message."""
        with self.lock:
            stage = data.get("stage", "")
            active = data.get("active", True)
            if active and stage:
                if stage == "DealCards":
                    self.dealt_cards = {P1: [], P2: []}
                    self.reg_leader1 = None
                    self.reg_leader2 = None
                    self.reg_deck1 = []
                    self.reg_deck2 = []
                self.stage = stage
                self._log_event(f"\U0001f3ad Stage: {stage}")

    def on_mfd(self, data):
        """Handle gwent/mfd/present."""
        with self.lock:
            subkind = data.get("subkind", "")
            if subkind == "prompt":
                self.last_prompt = data.get("prompt", "")
                self.last_prompt_time = datetime.now().strftime("%H:%M:%S")
                self._log_event(f"\U0001f4df {self.last_prompt}")
            elif subkind == "error":
                self.last_error = data.get("error", "")
                self.last_error_time = datetime.now().strftime("%H:%M:%S")
                self._log_event(f"\u274c {self.last_error}")
            elif subkind == "choices":
                self.last_choices = data.get("choices", [])
                labels = [c.get("text", "?") for c in self.last_choices]
                if labels:
                    self._log_event(f"\U0001f518 Choices: {' | '.join(labels)}")

    def on_sfx(self, data):
        """Handle gwent/sfx."""
        with self.lock:
            subkind = data.get("subkind", "")
            if subkind == "announcement":
                self.last_announcement = data.get("announcement", "")
                self._log_event(
                    f"\U0001f4e2 {self.last_announcement}"
                )

    def on_card_play(self, player_suffix, data):
        """Handle gwent/cards/play/{player} — tracks leaders, dealt cards, deck."""
        with self.lock:
            p = _normalize_player(player_suffix)
            subkind = data.get("subkind", "")
            card = data.get("card", {})
            if not card:
                return
            name = card.get("name", "???")
            if subkind == "deal_leader":
                if p == P1:
                    self.reg_leader1 = card
                else:
                    self.reg_leader2 = card
                self._log_event(f"\U0001f451 Leader: {name} \u2192 {p}")
            elif subkind == "deal_to_hand":
                self.dealt_cards[p].append(card)
                self._log_event(f"\U0001f0cf {name} \u2192 {p}")
            elif subkind in ("play_card", "place_card"):
                row = card.get("ranges", [""])[0] if card.get("ranges") else ""
                self._log_event(f"\u2694 {name} \u2192 {row or 'board'} ({p})")
            elif subkind == "add_to_deck":
                if p == P1:
                    self.reg_deck1.append(card)
                else:
                    self.reg_deck2.append(card)

    def on_choice(self, data):
        """Handle gwent/mfd/choose — a choice was made (rotary or LLM)."""
        with self.lock:
            text = data.get("text", "")
            if text:
                self._log_event(f"\u2714 Choice: {text}")

    def on_raw_read(self, data):
        """Handle gwent/cards/raw/read."""
        with self.lock:
            self.last_card_read = data
            self.last_card_read_time = datetime.now().strftime("%H:%M:%S")
            name = data.get("name", "???")
            self._log_event(f"\U0001f4f1 {name}")
