"""Integration test for Emhyr Emperor — view 3 random opponent hand cards.

Tests the view_opponent_hand leader ability by:
1. Verifying initial state
2. Activating the leader ability via MQTT
3. Asserting leader_used is True and turn advances
   (info-only ability — no board state change beyond leader_used)

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_view_opponent_hand_validator.py \
        --recording <recording.json> -v
"""

from conftest import card_names


class TestViewOpponentHand:

    def test_initial_state(self, game, recording):
        """Verify the game loaded correctly."""
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"
        assert board["current_player"] == "PLAYER.ONE"
        assert board["players"]["PLAYER.ONE"]["leader_used"] is False

    def test_view_opponent_hand_full_flow(self, game, recording):
        """Activate view_opponent_hand and verify it completes cleanly."""
        rec = recording["state"]
        leader = rec["leader1"]
        initial_p1_hand_size = len(rec["board"]["hands"]["PLAYER.ONE"])
        initial_p2_hand_size = len(rec["board"]["hands"]["PLAYER.TWO"])

        # Activate leader ability
        state = game.inject_card_and_wait(leader)
        board = state["state"]["board"]

        # Leader should be marked as used
        assert board["players"]["PLAYER.ONE"]["leader_used"] is True

        # Info-only ability: no cards should have moved
        assert len(board["hands"]["PLAYER.ONE"]) == initial_p1_hand_size
        assert len(board["hands"]["PLAYER.TWO"]) == initial_p2_hand_size
        assert len(board["players"]["PLAYER.ONE"]["discard"]) == 0
        assert len(board["players"]["PLAYER.TWO"]["discard"]) == 0

        # Scores unchanged (no cards played)
        assert board["scores"]["PLAYER.ONE"]["total"] == 0
        assert board["scores"]["PLAYER.TWO"]["total"] == 0

        # Turn should advance to P2
        board = game.wait_for_current_player("PLAYER.TWO")
        assert board["current_player"] == "PLAYER.TWO"
