"""In-memory game state model. Standalone — no gwent package dependency."""

import logging
import os
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from gwent_tui.game_log import GameLog

log = logging.getLogger("gwent_tui.state")

_REPO_ROOT = Path(os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))

# Event colors by type (used in _log_event for the events footer)
_EVENT_COLORS = {
    "deal_leader":      "bright_yellow",
    "deal_to_hand":     "dodger_blue2",
    "play_card":        "orange1",
    "place_card":       "orange1",
    "muster":           "orchid",
    "spy_draw":         "turquoise2",
    "medic_resurrect":  "green3",
    "remove_card":      "bright_red",
    "weather_change":   "grey70",
    "weather_clear":    "bright_yellow",
    "commander_horn":   "gold1",
    "decoy_swap":       "bright_cyan",
    "transform":        "bright_magenta",
    "round_clear":      "bright_white",
    "stage":            "bright_cyan",
    "error":            "bright_red",
    "announcement":     "dark_khaki",
    "choice":           "green1",
    "card_scan":        "bright_cyan",
    "music":            "plum1",
}

# Faction colors for announcements (matches FACTION_STYLE text colors)
_FACTION_COLORS = {
    "Monsters":        "#ff0000",
    "Nilfgaardian":    "#bdbdbd",
    "Northern Realms": "#1e90ff",
    "Scoia'tael":      "#00ff00",
    "Scoiatael":       "#00ff00",
    "Skellige":        "#9370db",
    "Neutral":         "#ffffff",
}


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
        self.game_log = GameLog(str(_REPO_ROOT / "tmp" / "games"))
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

        # TUI menu mirror cache — {menu_id: payload-dict} from retained
        # `gwent/menu/present/+` messages. Cleared per-menu when the backend
        # publishes an empty payload (retained slot cleared).
        self.menus: dict[str, dict] = {}

        # Per-side controller from retained `gwent/players/controller/PLAYER.*`.
        # Default "human" when nothing has been published yet.
        self.controllers: dict = {P1: "human", P2: "human"}
        # Display labels for the controllers, owned ONLY by the controller
        # topic — unlike player_names, server snapshots never overwrite these.
        self.controller_labels: dict = {P1: "", P2: ""}

        # Toasts received on gwent/toast — list of dicts, newest last. The
        # toast widget pops the oldest after its display duration.
        self.toasts: list[dict] = []

        # Deal tracking (cards dealt in real-time via MQTT)
        self.dealt_cards = {P1: [], P2: []}

        # Card overlay queue — cards are displayed in order, shortened when queued
        self.card_queue = []  # list of (card, subkind, player) tuples
        self.last_played_card = None
        self.last_played_time = 0.0
        self.last_played_subkind = ""
        self.last_played_by = None  # P1 or P2 enum — who played/drew the card

        # Score dedup gate (for disk writes)
        self._last_recorded_scores = (0, 0)
        self._summary_round = 0

        # Pending interactive MFD pick (numeric-id choices: agile row,
        # leader weather card, …). The app pops MFDChoiceModal for it.
        self.mfd_pick: dict | None = None
        self._mfd_pick_seq = 0

        # Event log (recent events for footer)
        self.last_prompt = ""
        self.last_prompt_time = ""
        self.last_error = ""
        self.last_error_time = ""
        self.last_choices = []
        self.last_announcement = ""
        self.last_card_read = None
        self.last_card_read_time = ""
        self._event_log = deque(maxlen=50)
        self.mqtt_status = "off"    # off, polling, processing, error
        self.server_online = True   # driven by gwent/server/presence; gates Offline stage
        self.dirty = False          # set on snapshot load → UI does a layout refresh
        self.server_tts = ""       # server TTS provider name (from snapshot)
        self.player_names = {P1: "Player 1", P2: "Player 2"}
        self.player_pronouns = {P1: "he", P2: "he"}

        # Change highlights: {key: expire_time}
        # Keys: "board:{player}:{row}:{card_name}", "hand:{player}:{card_name}",
        #        "discard:{player}:{card_name}", "score:{player}", "gems:{player}",
        #        "deck:{player}", "weather:{row}"
        #        "removed:hand:{player}:{card_name}" — ghost entries for removed cards
        self.highlights = {}
        # Ghost cards: temporarily shown as removed (red highlight then vanish)
        # {("hand", player): [card_dict, ...], ("board", player, row): [...]}
        self.ghosts = {}

        # Game identity — reset round history when game_id changes
        self.game_id = ""

        self._last_recorded_round = 0

        # Move timing
        self._turn_start = time.monotonic()
        self._prev_player = None
        self.move_times = {P1: [], P2: []}  # seconds per move

    def load_snapshot(self, snapshot):
        """Populate state from a JSON snapshot (gwent/server/state or SIGUSR1)."""
        with self.lock:
            self._load_snapshot_unlocked(snapshot)
            # Signal the UI to do a LAYOUT refresh (not just a repaint) on the
            # next tick: hand/board sizes change, and auto-height panels
            # (e.g. the Hands panel) must recompute or their rows stay clipped.
            self.dirty = True
            log.debug("Snapshot loaded: stage=%s round=%d scores=%s",
                       self.stage, self.round_number, self.scores)

    # Stages where game board data is meaningful
    _GAME_STAGES = {"PlayRound", "RoundEnd", "GameOver", "DisplayWinner"}

    def _load_snapshot_unlocked(self, snapshot):
        # Detect new game — reset game log when game_id changes
        new_game_id = snapshot.get("game_id", "")
        if new_game_id and new_game_id != self.game_id:
            if self.game_id:
                log.info("New game detected (id=%s → %s), resetting game log",
                         self.game_id, new_game_id)
                self.game_log.reset()
            self.game_id = new_game_id
            self.game_log.set_game_id(new_game_id)
            self._last_recorded_round = 0
            self.move_times = {P1: [], P2: []}

        state = snapshot.get("state", {})
        self.stage = snapshot.get("active_stage", "—") or "—"
        self.server_tts = snapshot.get("tts_provider", "") or ""

        # Player display names and pronouns (set via PUT /players)
        names = snapshot.get("player_names", {})
        for key, name in names.items():
            p = _normalize_player(key)
            self.player_names[p] = name
        pronouns = snapshot.get("player_pronouns", {})
        for key, pronoun in pronouns.items():
            p = _normalize_player(key)
            self.player_pronouns[p] = pronoun

        board = state.get("board", {})
        if not board or self.stage not in self._GAME_STAGES:
            self._reset_board()
            # Load registration data (leaders/decks from pre-game stages)
            self._load_registration_data(state)
            return

        # Detect changes before overwriting state
        self._detect_changes(board)

        new_round = board.get("round_number", 1)

        # Record round result when round advances or game ends
        if new_round > self._last_recorded_round and self._last_recorded_round > 0:
            self._record_round_result(self._last_recorded_round)
        if self.stage in ("GameOver", "DisplayWinner"):
            self._record_round_result(self.round_number)
        self._last_recorded_round = new_round

        self.round_number = new_round

        # Set summary round only when stage first transitions TO RoundEnd/GameOver.
        # Don't update on subsequent snapshots — the server advances round_number
        # during RoundEnd (clear_round + faction abilities) before the 10s pause.
        prev_stage = getattr(self, '_prev_snapshot_stage', '')
        if self.stage in ("RoundEnd", "GameOver", "DisplayWinner"):
            if prev_stage not in ("RoundEnd", "GameOver", "DisplayWinner"):
                self._summary_round = new_round
        self._prev_snapshot_stage = self.stage

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
            # Also update reg_leader for card overlay compatibility
            if p == P1:
                self.reg_leader1 = leader
            else:
                self.reg_leader2 = leader

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

        # Track score changes to disk
        current = (self.scores.get(P1, 0), self.scores.get(P2, 0))
        if current != self._last_recorded_scores:
            self.game_log.write("snapshots", "score_change", {
                "subkind": "score_change",
                "round": self.round_number,
                "ts": time.time(),
                "p1_score": current[0],
                "p2_score": current[1],
            })
            self._last_recorded_scores = current

    def score_history_for_round(self, round_num):
        """Return score history entries for a specific round (from disk)."""
        return self.game_log.read_filtered(
            "snapshots", round_num=round_num, subkinds=["score_change"])

    def is_highlighted(self, key):
        """Check if a key is currently highlighted (within TTL)."""
        expire = self.highlights.get(key)
        if expire is None:
            return False
        if time.monotonic() > expire:
            del self.highlights[key]
            return False
        return True

    def _highlight(self, key, ttl=None):
        """Mark a key as highlighted."""
        self.highlights[key] = time.monotonic() + (ttl or self.HIGHLIGHT_TTL)

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

            # Board rows changed — detect new and removed cards
            rows = pdata.get("rows", {})
            for row_name in ("close", "ranged", "siege"):
                old_cards = self.board_rows[p].get(row_name, [])
                old_names = {c.get("name") for c in old_cards}
                new_cards = rows.get(row_name, [])
                new_names = {c.get("name") for c in new_cards}
                # New cards — green highlight
                for c in new_cards:
                    if c.get("name") not in old_names:
                        self._highlight(f"board:{p}:{row_name}:{c.get('name')}")
                # Removed cards — red ghost (scorch, decoy, round end)
                removed_board = old_names - new_names
                if removed_board:
                    ghost_key = ("board", p, row_name)
                    ghosts = []
                    for c in old_cards:
                        if c.get("name") in removed_board:
                            ghosts.append(c)
                            self._highlight(f"removed:board:{p}:{row_name}:{c.get('name')}")
                    if ghosts:
                        self.ghosts[ghost_key] = (ghosts, time.monotonic() + self.HIGHLIGHT_TTL)

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

    def _record_round_result(self, round_num):
        """Write round result to disk using the last score snapshot for this round."""
        # Avoid duplicates
        if any(r["round"] == round_num for r in self.round_results):
            return
        # Use last score_change from game log (most accurate — not affected by race)
        score_history = self.game_log.read_filtered(
            "snapshots", round_num=round_num, subkinds=["score_change"])
        if score_history:
            last = score_history[-1]
            p1s = last.get("p1_score", 0)
            p2s = last.get("p2_score", 0)
        else:
            # Fallback to current in-memory scores
            p1s = self.scores.get(P1, 0)
            p2s = self.scores.get(P2, 0)
        if p1s > p2s:
            winner = P1
        elif p2s > p1s:
            winner = P2
        else:
            winner = None  # draw
        self.game_log.write("cards", "round_result", {
            "subkind": "round_result",
            "round": round_num,
            "p1_score": p1s,
            "p2_score": p2s,
            "winner": winner,
            "p1_gems": self.gems.get(P1, 0),
            "p2_gems": self.gems.get(P2, 0),
        })
        log.info("Round %d result: P1=%d P2=%d winner=%s", round_num, p1s, p2s, winner)

    def save_game_recording(self):
        """Save game recording summary to tmp/games/{game-id}.json."""
        import json
        game_dir = _REPO_ROOT / "tmp" / "games"
        game_dir.mkdir(parents=True, exist_ok=True)
        game_id = self.game_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        path = game_dir / f"{game_id}.json"

        p1_gems = self.gems.get(P1, 0)
        p2_gems = self.gems.get(P2, 0)
        if p1_gems > p2_gems:
            winner = P1
        elif p2_gems > p1_gems:
            winner = P2
        else:
            winner = None

        recording = {
            "game_id": game_id,
            "timestamp": datetime.now().isoformat(),
            "player_names": dict(self.player_names),
            "factions": dict(self.factions),
            "leaders": {
                p: self.leaders.get(p, {}).get("name", "")
                for p in (P1, P2)
            },
            "winner": winner,
            "final_gems": {P1: p1_gems, P2: p2_gems},
            "rounds": self.round_results,
            "move_times": {
                P1: self.move_times.get(P1, []),
                P2: self.move_times.get(P2, []),
            },
        }
        with open(path, "w") as f:
            json.dump(recording, f, indent=2)
        log.info("Game recording saved: %s", path)
        return str(path)

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

    def _log_event(self, msg, color=None):
        """Append a timestamped event to the log and write to file.

        Args:
            msg: Event text (may contain Rich markup).
            color: Optional Rich color to wrap the entire message.
        """
        ts = datetime.now().strftime("%H:%M:%S")
        if color:
            entry = f"[dim]{ts}[/dim] [{color}]{msg}[/{color}]"
        else:
            entry = f"[dim]{ts}[/dim] {msg}"
        self._event_log.append(entry)
        try:
            _events_log = os.path.join(str(_REPO_ROOT), "tmp", "logs", "gwent-tui-events.log")
            os.makedirs(os.path.dirname(_events_log), exist_ok=True)
            with open(_events_log, "a") as f:
                # Strip markup for the file log
                import re
                plain = re.sub(r'\[/?[^\]]*\]', '', entry)
                f.write(plain + "\n")
        except Exception:
            pass

    def queue_card(self, card, subkind, player):
        """Queue a card for overlay display."""
        self.card_queue.append((card, subkind, player))
        # If nothing currently showing, pop immediately
        if not self.last_played_card or (time.time() - self.last_played_time > 3):
            self._pop_card_queue()

    def _pop_card_queue(self):
        """Pop the next card from the queue into the display slot.

        Sets all fields atomically (subkind before card) to prevent the
        overlay from reading a stale subkind with a new card.
        """
        if self.card_queue:
            card, subkind, player = self.card_queue.pop(0)
            # Set subkind FIRST so the overlay never sees a new card with old subkind
            self.last_played_subkind = subkind
            self.last_played_by = player
            self.last_played_time = time.time()
            self.last_played_card = card  # set last — triggers overlay render

    def advance_card_queue(self):
        """Called by the overlay when the current card display expires."""
        self._pop_card_queue()

    @property
    def card_display_seconds(self):
        """5 seconds per card when queued, 8 seconds for single cards."""
        return 5 if self.card_queue else 8

    # Subkinds that represent gameplay events (not deal/registration)
    _EVENT_SUBKINDS = [
        "play_card", "place_card", "muster", "spy_draw",
        "medic_resurrect", "remove_card", "weather_change",
        "commander_horn", "decoy_swap", "transform",
    ]

    @property
    def card_events(self):
        """All card events across all rounds (from disk)."""
        return self.game_log.read_filtered("cards", subkinds=self._EVENT_SUBKINDS)

    def events_for_round(self, round_num):
        """Return card events for a specific round (from disk)."""
        return self.game_log.read_filtered(
            "cards", round_num=round_num, subkinds=self._EVENT_SUBKINDS)

    @property
    def round_results(self):
        """All round results (from disk)."""
        return self.game_log.read_filtered("cards", subkinds=["round_result"])

    def dismiss_round_summary(self):
        """No-op — kept for backwards compat with round_summary.py on_key."""
        pass

    def _record_card_event(self, subkind, p, card, data):
        """Write a compact event record to disk for stats tracking."""
        self.game_log.write("cards", subkind, {
            "subkind": subkind,
            "round": self.round_number,
            "ts": time.time(),
            "player": p,
            "name": card.get("name", "???"),
            "row": data.get("row", ""),
            "strength": card.get("strength"),
            "faction": card.get("faction", ""),
            "specialty": card.get("specialty", ""),
            "abilities": card.get("abilities", []) or [],
            "p1_score": self.scores.get(P1, 0),
            "p2_score": self.scores.get(P2, 0),
            "reason": data.get("reason", ""),
            "weather_rows": data.get("weather_rows", []),
        })

    # --- MQTT event handlers ---

    def on_ctrl(self, data):
        """Handle gwent/ctrl stage message."""
        self.game_log.write("ctrl", data.get("stage", "unknown"), data)
        with self.lock:
            stage = data.get("stage", "")
            active = data.get("active", True)
            if active and stage:
                prev_stage = self.stage
                if stage == "DealCards":
                    self.dealt_cards = {P1: [], P2: []}
                    self.reg_leader1 = None
                    self.reg_leader2 = None
                    self.reg_deck1 = []
                    self.reg_deck2 = []
                # Set summary round when entering RoundEnd (for RoundEndStage display)
                if stage == "RoundEnd":
                    self._summary_round = self.round_number
                    self._record_round_result(self.round_number)
                self.stage = stage
                self._log_event(f"\U0001f3ad Stage: {stage}", color=_EVENT_COLORS["stage"])
                if stage in ("GameOver", "DisplayWinner"):
                    # Record final round and save game
                    self._record_round_result(self.round_number)
                    try:
                        self.save_game_recording()
                    except Exception as e:
                        log.warning("Failed to save game recording: %s", e)

    def on_controller(self, player: str, controller: str,
                      label: str | None = None) -> None:
        """Handle a retained `gwent/players/controller/PLAYER.*` update.

        `player` is the suffix after `controller/` (e.g. 'PLAYER.ONE').
        `label` is the human-readable model name from the server (optional).
        """
        with self.lock:
            if player.endswith("ONE"):
                key, default_name = P1, "Player 1"
            elif player.endswith("TWO"):
                key, default_name = P2, "Player 2"
            else:
                log.warning("controller update for unknown player %r", player)
                return
            self.controllers[key] = controller
            if not controller or controller == "human":
                self.player_names[key] = default_name
                self.controller_labels[key] = ""
            else:
                self.controller_labels[key] = (
                    label if label and label != "human" else controller)
                if label and label not in ("human", controller):
                    self.player_names[key] = label
            log.info("controller %s = %s (label=%r)", player, controller, label)

    def on_toast(self, payload: dict) -> None:
        """Handle a `gwent/toast` event — render to event log + cache for widget."""
        text = payload.get("text", "")
        level = payload.get("level", "info")
        with self.lock:
            self.toasts.append({
                "ts": payload.get("ts") or 0,
                "level": level,
                "text": text,
            })
            if len(self.toasts) > 5:
                self.toasts = self.toasts[-5:]
        # Mirror to the event log so it's visible immediately in the footer.
        color = {
            "info": "cyan",
            "warn": "yellow",
            "error": "red",
        }.get(level, "white")
        icon = {"info": "ℹ", "warn": "⚠", "error": "✖"}.get(level, "•")
        self._log_event(f"{icon} {text}", color=color)
        log.info("toast queued level=%s text=%r", level, text)

    def on_menu(self, menu_id: str, payload: dict | None):
        """Handle a retained `gwent/menu/present/{menu_id}` update.

        `payload=None` means the retained slot was cleared (empty payload).
        Stores or removes the entry from self.menus. Caller is responsible
        for triggering any UI refresh.
        """
        self.game_log.write("menu", menu_id, payload or {})
        with self.lock:
            if payload is None or not payload.get("choices"):
                self.menus.pop(menu_id, None)
                log.info("menu cleared: %s", menu_id)
            else:
                self.menus[menu_id] = payload
                log.info("menu cached: %s (%d choices)",
                         menu_id, len(payload.get("choices", [])))

    def on_mfd(self, data):
        """Handle gwent/mfd/present."""
        self.game_log.write("mfd", data.get("subkind", "unknown"), data)
        with self.lock:
            subkind = data.get("subkind", "")
            if subkind == "prompt":
                self.last_prompt = data.get("prompt", "")
                self.last_prompt_time = datetime.now().strftime("%H:%M:%S")
                # Don't log prompts to events pane — too noisy
                if data.get("clear_choices"):
                    # Choices resolved/superseded — drop any pending pick so
                    # the popup closes (it may have been answered via rotary).
                    if self.mfd_pick is not None:
                        log.info("mfd pick cleared by prompt (clear_choices)")
                    self.mfd_pick = None
                elif self.mfd_pick is not None and self.last_prompt:
                    # The contextual prompt (e.g. 'Assign X to a row.')
                    # arrives AFTER the choices — attach it as the title.
                    self.mfd_pick["prompt"] = self.last_prompt
            elif subkind == "error":
                self.last_error = data.get("error", "")
                self.last_error_time = datetime.now().strftime("%H:%M:%S")
                self._log_event(f"\u274c {self.last_error}", color=_EVENT_COLORS["error"])
            elif subkind == "choices":
                self.last_choices = data.get("choices", [])
                labels = [c.get("text", "?") for c in self.last_choices]
                if labels:
                    self._log_event(f"\U0001f518 Choices: {' | '.join(labels)}", color="bright_yellow")
                # Interactive picks (agile row, leader weather card, …) use
                # numeric ids; the per-turn Repeat('h')/Pass('p') choices
                # don't. Surface numeric-id sets as a popup request so the
                # touchscreen can answer them (rotary/OLED-only before).
                if self.last_choices and all(
                        str(c.get("id", "")).isdigit() for c in self.last_choices):
                    self._mfd_pick_seq += 1
                    self.mfd_pick = {
                        "seq": self._mfd_pick_seq,
                        "prompt": "",
                        "choices": list(self.last_choices),
                    }
                    log.info("mfd pick #%d posted: %s",
                             self._mfd_pick_seq, labels)

    def on_sfx(self, data):
        """Handle gwent/sfx."""
        self.game_log.write("sfx", data.get("subkind", "unknown"), data)
        with self.lock:
            subkind = data.get("subkind", "")
            if subkind == "announcement":
                self.last_announcement = data.get("announcement", "")
                # Use faction color if present (player action), otherwise server color
                faction = data.get("faction", "")
                color = _FACTION_COLORS.get(faction, _EVENT_COLORS["announcement"])
                self._log_event(
                    f"\U0001f4e2 {self.last_announcement}", color=color
                )

    def on_card_play(self, player_suffix, data):
        """Handle gwent/cards/play/{player} — tracks leaders, dealt cards, deck.

        Raw MQTT data is NOT written here — _record_card_event writes the
        enriched version to cards/ for gameplay subkinds.
        """
        with self.lock:
            p = _normalize_player(player_suffix)
            subkind = data.get("subkind", "")
            card = data.get("card", {})
            if not card:
                return
            name = card.get("name", "???")
            # Subkinds that represent gameplay actions — record for stats
            _RECORD_SUBKINDS = {"play_card", "place_card", "muster", "spy_draw",
                                "medic_resurrect", "remove_card", "weather_change",
                                "commander_horn", "decoy_swap", "transform"}

            # Color by player's faction for player-specific events
            fc = _FACTION_COLORS.get(self.factions.get(p, ""))
            ec = fc or _EVENT_COLORS.get(subkind)
            if subkind == "deal_leader":
                if p == P1:
                    self.reg_leader1 = card
                else:
                    self.reg_leader2 = card
                self._log_event(f"\U0001f451 Leader: {name} \u2192 {p}", color=ec)
                self.queue_card(card, subkind, p)
            elif subkind == "deal_to_hand":
                self.dealt_cards[p].append(card)
                self._log_event(f"\U0001f0cf {name} \u2192 {p}", color=ec)
            elif subkind in ("play_card", "place_card"):
                row = data.get("row", "")
                if not row:
                    row = card.get("ranges", [""])[0] if card.get("ranges") else ""
                self._log_event(f"\u2694 {name} \u2192 {row or 'board'} ({p})", color=ec)
                self.queue_card(card, subkind, p)
            elif subkind == "muster":
                row = data.get("row", "")
                self._log_event(f"\U0001f4e3 Muster: {name} \u2192 {row} ({p})", color=ec)
                self.queue_card(card, subkind, p)
            elif subkind == "spy_draw":
                self._log_event(f"\U0001f575 Spy draw: {name} ({p})", color=ec)
                self.queue_card(card, subkind, p)
            elif subkind == "medic_resurrect":
                row = data.get("row", "")
                self._log_event(f"\U0001f48a Medic: {name} \u2192 {row} ({p})", color=ec)
                self.queue_card(card, subkind, p)
            elif subkind == "remove_card":
                reason = data.get("reason", "")
                self._log_event(f"\U0001f525 {name} destroyed ({reason}) ({p})", color=ec)
                self.queue_card(card, subkind, p)
                self.last_played_subkind = subkind
                self.last_played_by = p
            elif subkind == "weather_change":
                rows = data.get("weather_rows", [])
                if rows:
                    self._log_event(f"\u2601 Weather: {', '.join(rows)}", color=_EVENT_COLORS["weather_change"])
                else:
                    self._log_event(f"\u2600 Weather cleared", color=_EVENT_COLORS["weather_clear"])
            elif subkind == "commander_horn":
                row = data.get("row", "")
                self._log_event(f"\U0001f4ef Horn on {row} ({p})", color=ec)
            elif subkind == "decoy_swap":
                returned = data.get("returned_card", {})
                self._log_event(f"\U0001f3ad Decoy: {returned.get('name', '?')} returned ({p})", color=ec)
                if returned:
                    self.queue_card(returned, subkind, p)
            elif subkind == "transform":
                new_card = data.get("new_card", {})
                old_name = data.get("old_card", {}).get("name", "?")
                new_name = new_card.get("name", "?")
                self._log_event(f"\U0001f500 Transform: {old_name} \u2192 {new_name} ({p})", color=ec)
                if new_card:
                    self.queue_card(new_card, subkind, p)
            elif subkind == "round_clear":
                self._log_event(f"\U0001f3c1 Round cleared", color=_EVENT_COLORS["round_clear"])

            # Record gameplay events for round summary / game over stats
            if subkind in _RECORD_SUBKINDS:
                self._record_card_event(subkind, p, card, data)
            elif subkind == "add_to_deck":
                if p == P1:
                    self.reg_deck1.append(card)
                else:
                    self.reg_deck2.append(card)

    def on_choice(self, data):
        """Handle gwent/mfd/choose — a choice was made (rotary or LLM)."""
        self.game_log.write("mfd", "choice", data)
        with self.lock:
            text = data.get("text", "")
            if text:
                self._log_event(f"\u2714 Choice: {text}", color=_EVENT_COLORS["choice"])

    def on_raw_read(self, data):
        """Handle gwent/cards/raw/read."""
        self.game_log.write("cards", "raw_read", data)
        with self.lock:
            self.last_card_read = data
            self.last_card_read_time = datetime.now().strftime("%H:%M:%S")
            name = data.get("name", "???")
            self._log_event(f"\U0001f4f1 {name}", color=_EVENT_COLORS["card_scan"])
