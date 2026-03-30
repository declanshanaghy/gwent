"""Game state serialization and deserialization.

Saves/loads the complete game state as a JSON file so the game can be
resumed at any point. State files are stored in the recordings/ directory.

Format:
    {
        "version": 1,
        "game_id": "20260330-001500",
        "saved_at": "2026-03-24T21:30:00Z",
        "active_stage": "DealCards",
        "state": {
            "leader1": { ...card dict... },
            "leader2": { ...card dict... },
            "player1_deck": [ ...card dicts... ],
            "player2_deck": [ ...card dicts... ],
            "player1_hand": [ ...card dicts (pre-board stages only)... ],
            "player2_hand": [ ...card dicts (pre-board stages only)... ],
            "board": { ...board dict (PlayRound+ stages, includes hands)... }
        }
    }

Unknown fields are ignored on load (forward compatible).
Missing fields default to empty/zero (backward compatible).
"""

import json
import os
import time
from datetime import datetime, timezone

# Unique ID for the current game — regenerated when a new game starts
_game_id = datetime.now().strftime("%Y%m%d-%H%M%S")


def new_game_id():
    """Generate a new game_id from current time. Called when a new game starts."""
    global _game_id
    _game_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    return _game_id


def get_game_id():
    """Return the current game_id."""
    return _game_id

import jsonschema

import gwent.messaging.card
from gwent.game.constants import PLAYER
from gwent.utils.logging import get_logger

log = get_logger("gwent.game.state")

STATE_VERSION = 1
STATES_DIR = os.path.join(os.path.dirname(__file__), "recordings")
SCHEMA_PATH = os.path.join(STATES_DIR, "recording.schema.json")


def _cards_to_dicts(cards):
    """Convert a list of card Messages to serializable dicts."""
    return [c._instance for c in cards] if cards else []


def _dicts_to_cards(dicts):
    """Convert a list of dicts back to card Messages."""
    if not dicts:
        return []
    return [gwent.messaging.card.Message.from_properties(d) for d in dicts]


def _dict_to_card(d):
    """Convert a single dict to a card Message, or None."""
    if not d:
        return None
    return gwent.messaging.card.Message.from_properties(d)


def snapshot_dict(controller, player_names=None, client_tts=None):
    """Build the snapshot dict from current game state.

    Used by both save() and the HTTP /state endpoint.

    Args:
        controller: The game Controller instance.
        player_names: Optional dict mapping PLAYER.ONE/PLAYER.TWO to display names.
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
        # If in PlayRound or later, save the board state (includes hands)
        pr = controller.play_round
        if hasattr(pr, '_board') and pr._board is not None:
            state["board"] = pr._board.to_dict()

        # Also check round_end for board state
        re = controller.round_end
        if hasattr(re, '_board') and re._board is not None:
            state["board"] = re._board.to_dict()

    # Save deal_cards hands only if no board (board has its own hands)
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
    if client_tts:
        result["client_tts"] = client_tts
    return result


def save(filepath, controller):
    """Save the current game state to a JSON file.

    Args:
        filepath: Absolute path to write the state file.
        controller: The game Controller instance.
    """
    snapshot = snapshot_dict(controller)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(snapshot, f, indent=2)

    log.info(f"Game state saved to {filepath} (stage={snapshot['active_stage']})")
    return filepath


def load(filepath, controller):
    """Load a saved game state and jump to the appropriate stage.

    Args:
        filepath: Absolute path to the state JSON file.
        controller: The game Controller instance.
    """
    with open(filepath) as f:
        snapshot = json.load(f)

    # Validate against schema for PlayRound recordings
    if snapshot.get("active_stage") == "PlayRound" and os.path.exists(SCHEMA_PATH):
        try:
            with open(SCHEMA_PATH) as sf:
                schema = json.load(sf)
            jsonschema.validate(snapshot, schema)
        except jsonschema.ValidationError as e:
            log.warning(f"Recording schema validation failed: {e.message} at {'.'.join(str(p) for p in e.absolute_path)}")

    version = snapshot.get("version", 0)
    if version > STATE_VERSION:
        log.warning(f"State file version {version} is newer than supported {STATE_VERSION}")

    stage_name = snapshot.get("active_stage", "MainMenu")
    state = snapshot.get("state", {})

    log.info(f"Loading game state from {filepath} (stage={stage_name}, version={version})")

    # Reconstruct card objects
    leader1 = _dict_to_card(state.get("leader1"))
    leader2 = _dict_to_card(state.get("leader2"))
    player1_deck = _dicts_to_cards(state.get("player1_deck", []))
    player2_deck = _dicts_to_cards(state.get("player2_deck", []))

    # Reconstruct board if present
    board = None
    if "board" in state:
        from gwent.game.board import Board
        board = Board.from_dict(state["board"])

    # Jump to the saved stage with the appropriate data
    if stage_name == "RegisterLeaders":
        controller.start_register_leaders()

    elif stage_name == "RegisterDecks":
        if leader1 and leader2:
            controller.start_register_decks(leader1, leader2)
        else:
            log.error("Cannot restore RegisterDecks: missing leaders")
            controller.start_register_leaders()

    elif stage_name == "DealCards":
        if player1_deck and player2_deck:
            controller.start_deal_cards(player1_deck, player2_deck)
        else:
            log.error("Cannot restore DealCards: missing decks")
            controller.start_register_leaders()

    elif stage_name == "PlayRound":
        if board:
            controller.start_play_round(
                board.decks[PLAYER.ONE], board.hands[PLAYER.ONE],
                board.decks[PLAYER.TWO], board.hands[PLAYER.TWO],
                board=board)
        else:
            log.error("Cannot restore PlayRound: missing board")
            controller.start_register_leaders()

    elif stage_name == "RoundEnd":
        if board:
            controller.start_round_end(board)
        else:
            log.error("Cannot restore RoundEnd: missing board")
            controller.start_register_leaders()

    elif stage_name in ("GameOver", "DisplayWinner"):
        if board:
            controller.start_game_over(board)
        else:
            controller.start_main_menu()

    else:
        log.info(f"Starting from main menu (stage={stage_name})")
        controller.start_main_menu()

    log.info(f"Game state loaded, now at stage: {stage_name}")


def get_filepath(name):
    """Resolve a state filename to an absolute path in the recordings dir."""
    if not name.endswith(".json"):
        name += ".json"
    return os.path.join(STATES_DIR, name)
