"""Integration test for Francesca Daisy — draw extra card at battle start.

Tests the extra_draw leader ability by:
1. Verifying P2 has 11 cards in hand (10 normal + 1 extra from leader)
2. Verifying the leader card scan during PlayRound reports "already applied"

The extra_draw ability triggers during DealCards, so the recording
should have P2 starting with 11 cards in hand.

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_extra_draw_validator.py \
        --recording <recording.json> -v
"""


class TestExtraDraw:

    def test_p2_has_extra_card(self, game, recording):
        """Verify P2 started with 11 cards (extra_draw effect)."""
        rec = recording["state"]
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"

        # P2 should have 11 cards (10 normal + 1 extra)
        p2_hand_size = len(board["hands"]["PLAYER.TWO"])
        expected = len(rec["board"]["hands"]["PLAYER.TWO"])
        assert p2_hand_size == expected, (
            f"P2 hand size should be {expected}, got {p2_hand_size}"
        )
        assert p2_hand_size == 11, (
            f"P2 should have 11 cards (10 + extra_draw), got {p2_hand_size}"
        )

    def test_leader_scan_reports_already_applied(self, game, recording):
        """Scanning the leader during PlayRound should report already applied."""
        rec = recording["state"]
        leader2 = rec["leader2"]

        # First, P1 needs to play so it's P2's turn
        p1_hand = rec["board"]["hands"]["PLAYER.ONE"]
        # Find a non-spy, non-hero unit to play
        unit = next(
            c for c in p1_hand
            if c.get("strength") and c.get("specialty") != "hero"
            and "spy" not in c.get("abilities", [])
        )
        game.inject_card_and_wait(unit)
        board = game.wait_for_current_player("PLAYER.TWO")

        # Now scan the P2 leader
        state = game.inject_card_and_wait(leader2)
        board = state["state"]["board"]

        # Leader should be marked as used
        assert board["players"]["PLAYER.TWO"]["leader_used"] is True

        # P2's hand should be unchanged (no additional draw during PlayRound)
        # Hand lost nothing — it's info-only
        p2_hand_size = len(board["hands"]["PLAYER.TWO"])
        assert p2_hand_size == 11, (
            f"P2 hand should still be 11, got {p2_hand_size}"
        )
