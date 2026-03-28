"""Integration test for Emhyr White Flame — cancel opponent's leader ability.

Tests the cancel_leader ability by:
1. P1 activates cancel_leader
2. Asserting opponent's leader_used is set to True
3. P2 tries to use their leader — should be rejected

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_cancel_leader_validator.py \
        --recording <recording.json> -v
"""


class TestCancelLeader:

    def test_initial_state(self, game, recording):
        """Verify both leaders are unused at start."""
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"
        assert board["current_player"] == "PLAYER.ONE"
        assert board["players"]["PLAYER.ONE"]["leader_used"] is False
        assert board["players"]["PLAYER.TWO"]["leader_used"] is False

    def test_cancel_leader_full_flow(self, game, recording):
        """Activate cancel_leader, verify opponent's leader is disabled."""
        import time
        rec = recording["state"]
        leader1 = rec["leader1"]
        leader2 = rec["leader2"]

        # --- P1 activates cancel_leader ---
        state = game.inject_card_and_wait(leader1)
        board = state["state"]["board"]

        # P1's leader should be used
        assert board["players"]["PLAYER.ONE"]["leader_used"] is True
        # P2's leader should ALSO be marked as used (cancelled)
        assert board["players"]["PLAYER.TWO"]["leader_used"] is True

        # Turn should advance to P2
        board = game.wait_for_current_player("PLAYER.TWO")
        assert board["current_player"] == "PLAYER.TWO"

        # --- P2 tries to use their leader — should fail ---
        # Inject P2's leader card; the game should reject it
        # (leader_used is already True, so it publishes an error)
        pre_state = game.get_state()
        game.inject_card(leader2)
        time.sleep(3)

        # State should NOT change meaningfully — leader was already used
        board = game.get_board()
        # P2's leader_used should still be True
        assert board["players"]["PLAYER.TWO"]["leader_used"] is True
        # Current player should still be P2 (rejected scan doesn't advance turn)
        assert board["current_player"] == "PLAYER.TWO"
