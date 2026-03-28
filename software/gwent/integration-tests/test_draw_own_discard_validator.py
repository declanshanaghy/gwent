"""Integration test for Eredin Bringer of Death — restore card from own discard.

Tests the draw_own_discard leader ability. Since cancel_leader is tested
first in this matchup (P1 cancels P2's leader), this test verifies
the cancelled state — P2 cannot use draw_own_discard.

For a standalone test of draw_own_discard working correctly, use a
recording where the leader is not cancelled.

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_draw_own_discard_validator.py \
        --recording <recording.json> -v
"""


class TestDrawOwnDiscard:

    def test_initial_state(self, game, recording):
        """Verify P2 has the draw_own_discard leader."""
        rec = recording["state"]
        leader2 = rec["leader2"]
        assert leader2.get("leader", {}).get("draw_own_discard") is True

    def test_p2_leader_identity(self, game, recording):
        """Verify P2 leader is Eredin: Bringer of Death."""
        state = game.get_state()
        board = state["state"]["board"]
        p2_leader = board["leaders"]["PLAYER.TWO"]
        assert "Bringer of Death" in p2_leader["name"]
