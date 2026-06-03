"""Game-state serialization for the live MQTT snapshot.

Builds the JSON snapshot published (retained) on `gwent/server/state` by the
StatePublisher, plus a content hash used to dedupe republishes. There is no
on-disk recording/playback — games always start from freshly generated decks.

Snapshot shape:
    {
        "version": 1,
        "game_id": "20260330-001500",
        "saved_at": "2026-03-24T21:30:00Z",
        "active_stage": "PlayRound",
        "tts_provider": "elevenlabs",
        "state": {
            "leader1": {...}, "leader2": {...},
            "player1_deck": [...], "player2_deck": [...],
            "player1_hand": [...], "player2_hand": [...],   # pre-board stages
            "board": {...}                                   # PlayRound+ stages
        }
    }
"""

import hashlib
import json
from datetime import datetime, timezone

import gwent.messaging.card
from gwent.utils.logging import get_logger

log = get_logger("gwent.game.state")

STATE_VERSION = 1

# Unique ID for the current game — regenerated when a new game starts.
_game_id = datetime.now().strftime("%Y%m%d-%H%M%S")


def new_game_id():
    """Generate a new game_id from current time. Called when a new game starts."""
    global _game_id
    _game_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    return _game_id


def get_game_id():
    """Return the current game_id."""
    return _game_id


def _cards_to_dicts(cards):
    """Convert a list of card Messages to serializable dicts."""
    return [c._instance for c in cards] if cards else []


def snapshot_dict(controller, player_names=None, player_pronouns=None, client_tts=None):
    """Build the snapshot dict from current game state (for gwent/server/state).

    Args:
        controller: The game Controller instance.
        player_names: Optional dict mapping PLAYER.ONE/PLAYER.TWO to display names.
        player_pronouns: Optional dict of per-player pronouns.
        client_tts: Optional dict of {client_id: provider_name} for connected clients.

    Returns:
        dict: The complete snapshot ready for JSON serialization.
    """
    stage_name = None
    if controller.active_stage:
        stage_name = controller.active_stage.stage

    # Stages where board data is meaningful
    _BOARD_STAGES = {"PlayRound", "RoundEnd", "GameOver", "DisplayWinner"}

    state = {}

    # Gather state from register_leaders
    rl = controller.register_leaders
    if rl._leader1:
        state["leader1"] = rl._leader1._instance
    if rl._leader2:
        state["leader2"] = rl._leader2._instance

    # Gather state from register_decks
    rd = controller.register_decks
    if rd._player1_deck:
        state["player1_deck"] = _cards_to_dicts(rd._player1_deck)
    if rd._player2_deck:
        state["player2_deck"] = _cards_to_dicts(rd._player2_deck)

    # Only include board data during active game stages
    if stage_name in _BOARD_STAGES:
        # If in PlayRound or later, the board carries the live hands/rows.
        pr = controller.play_round
        if hasattr(pr, '_board') and pr._board is not None:
            state["board"] = pr._board.to_dict()

        # Also check round_end for board state
        re = controller.round_end
        if hasattr(re, '_board') and re._board is not None:
            state["board"] = re._board.to_dict()

    # Pre-board hands only when there's no board yet (board has its own hands)
    if "board" not in state:
        dc = controller.deal_cards
        if dc._player1_hand:
            state["player1_hand"] = _cards_to_dicts(dc._player1_hand)
        if dc._player2_hand:
            state["player2_hand"] = _cards_to_dicts(dc._player2_hand)

    result = {
        "version": STATE_VERSION,
        "game_id": _game_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "active_stage": stage_name,
        "tts_provider": getattr(controller, '_tts_provider', None),
        "state": state,
    }
    if player_names:
        result["player_names"] = player_names
    if player_pronouns:
        result["player_pronouns"] = player_pronouns
    if client_tts:
        result["client_tts"] = client_tts
    return result


def state_hash(snapshot):
    """Stable content hash of a snapshot, ignoring the volatile saved_at field.

    Lets the StatePublisher skip republishing when a burst of internal publishes
    didn't actually change the snapshot.
    """
    stable = dict(snapshot)
    stable.pop("saved_at", None)
    raw = json.dumps(stable, sort_keys=True).encode("utf-8")
    return hashlib.md5(raw).hexdigest()
