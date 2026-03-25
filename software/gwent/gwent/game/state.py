"""Game state serialization and deserialization.

Saves/loads the complete game state as a JSON file so the game can be
resumed at any point. State files are stored in the recordings/ directory.

Format:
    {
        "version": 1,
        "saved_at": "2026-03-24T21:30:00Z",
        "active_stage": "DealCards",
        "state": {
            "leader1": { ...card dict... },
            "leader2": { ...card dict... },
            "player1_deck": [ ...card dicts... ],
            "player2_deck": [ ...card dicts... ],
            "player1_hand": [ ...card dicts... ],
            "player2_hand": [ ...card dicts... ],
            "player1_score": 0,
            "player2_score": 0
        }
    }

Unknown fields are ignored on load (forward compatible).
Missing fields default to empty/zero (backward compatible).
"""

import json
import os
import time
from datetime import datetime, timezone

import gwent.messaging.card
from gwent.utils.logging import get_logger

log = get_logger("gwent.game.state")

STATE_VERSION = 1
STATES_DIR = os.path.join(os.path.dirname(__file__), "recordings")


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


def save(filepath, controller):
    """Save the current game state to a JSON file.

    Args:
        filepath: Absolute path to write the state file.
        controller: The game Controller instance.
    """
    stage_name = None
    if controller.active_stage:
        stage_name = controller.active_stage.stage

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

    # Gather state from deal_cards
    dc = controller.deal_cards
    if dc._player1_hand:
        state["player1_hand"] = _cards_to_dicts(dc._player1_hand)
    if dc._player2_hand:
        state["player2_hand"] = _cards_to_dicts(dc._player2_hand)

    # Player scores (from the Player components, accessed via controller)
    # These are set during process_card_play, not directly on the controller.
    # For now, store 0 — scores will be populated when Player exposes them.
    state["player1_score"] = 0
    state["player2_score"] = 0

    snapshot = {
        "version": STATE_VERSION,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "active_stage": stage_name,
        "state": state,
    }

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(snapshot, f, indent=2)

    log.info(f"Game state saved to {filepath} (stage={stage_name})")
    return filepath


def load(filepath, controller):
    """Load a saved game state and jump to the appropriate stage.

    Args:
        filepath: Absolute path to the state JSON file.
        controller: The game Controller instance.
    """
    with open(filepath) as f:
        snapshot = json.load(f)

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
    player1_hand = _dicts_to_cards(state.get("player1_hand", []))
    player2_hand = _dicts_to_cards(state.get("player2_hand", []))

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
        if player1_deck and player1_hand and player2_deck and player2_hand:
            controller.start_play_round(player1_deck, player1_hand, player2_deck, player2_hand)
        else:
            log.error("Cannot restore PlayRound: missing deck/hand data")
            controller.start_register_leaders()

    else:
        log.info(f"Starting from main menu (stage={stage_name})")
        controller.start_main_menu()

    log.info(f"Game state loaded, now at stage: {stage_name}")


def get_filepath(name):
    """Resolve a state filename to an absolute path in the recordings dir."""
    if not name.endswith(".json"):
        name += ".json"
    return os.path.join(STATES_DIR, name)
