"""Integration test for Francesca Hope — optimize agile unit placement.

Tests the optimize_agile leader ability by:
1. P1 plays Biting Frost (weather on close row)
2. P1's turn ends, P2 plays agile unit on close row (weakened by weather)
3. P2's turn ends, P1 passes
4. P2 activates leader — agile unit should move to ranged (better row)

Requires a recording where P1 has Biting Frost in HAND and P2 has agile units.

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_optimize_agile_validator.py \
        --recording <recording.json> -v
"""

from conftest import card_names


class TestOptimizeAgile:

    def test_initial_state(self, game, recording):
        """Verify the game loaded with P2 having agile units."""
        rec = recording["state"]
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"
        assert board["players"]["PLAYER.TWO"]["leader_used"] is False

        p2_hand = rec["board"]["hands"]["PLAYER.TWO"]
        agile_count = sum(
            1 for c in p2_hand
            if "agile" in c.get("abilities", [])
        )
        assert agile_count >= 2, f"Need agile units in P2 hand, found {agile_count}"

    def test_optimize_agile_full_flow(self, game, recording):
        """Play agile unit on weather-affected row, then optimize."""
        import time
        rec = recording["state"]
        leader2 = rec["leader2"]
        p1_hand = rec["board"]["hands"]["PLAYER.ONE"]
        p2_hand = rec["board"]["hands"]["PLAYER.TWO"]

        # Find Biting Frost in P1's hand (close-row weather)
        frost_card = next(
            (c for c in p1_hand
             if c.get("specialty") == "weather"
             and "close" in c.get("ranges", [])),
            None,
        )
        assert frost_card is not None, (
            "P1 needs Biting Frost in HAND. Rebuild recording with frost in hand."
        )

        # Find an agile unit in P2's hand
        agile_card = next(
            c for c in p2_hand
            if "agile" in c.get("abilities", [])
            and c.get("specialty") != "hero"
            and len(c.get("ranges", [])) >= 2
        )

        # --- P1 plays Biting Frost ---
        state = game.inject_card_and_wait(frost_card)
        board = state["state"]["board"]
        assert "close" in board["weather_rows"]

        board = game.wait_for_current_player("PLAYER.TWO")

        # --- P2 plays agile unit, choosing close row ---
        # Agile cards prompt for row choice — inject card, then pick close row
        pre_state = game.get_state()
        pre_etag = game.compute_etag(pre_state)
        game.inject_card(agile_card)
        time.sleep(2)
        # Choose "close" (index 0 in ranges)
        game.inject_choice("0", "close")
        time.sleep(3)
        state = game.wait_for_state_change(pre_etag, timeout=20)

        board = game.wait_for_current_player("PLAYER.ONE")

        # Verify card is on close row (weather-weakened to str 1)
        p2_close = card_names(board["players"]["PLAYER.TWO"]["rows"]["close"])
        assert agile_card["name"] in p2_close

        # --- P1 passes ---
        game.inject_choice("p", "Player 1 Pass")
        time.sleep(3)
        board = game.wait_for_current_player("PLAYER.TWO")

        pre_score = board["scores"]["PLAYER.TWO"]["total"]

        # --- P2 activates optimize_agile leader ---
        state = game.inject_card_and_wait(leader2)
        board = state["state"]["board"]

        assert board["players"]["PLAYER.TWO"]["leader_used"] is True

        # Card should have moved from close (weather) to ranged (no weather)
        p2_close_after = card_names(board["players"]["PLAYER.TWO"]["rows"]["close"])
        p2_ranged_after = card_names(board["players"]["PLAYER.TWO"]["rows"]["ranged"])
        assert agile_card["name"] in p2_ranged_after, (
            f"Expected {agile_card['name']} moved to ranged, "
            f"close={p2_close_after}, ranged={p2_ranged_after}"
        )
        assert agile_card["name"] not in p2_close_after

        # Score should improve (full strength vs weather-reduced)
        post_score = board["scores"]["PLAYER.TWO"]["total"]
        assert post_score > pre_score, (
            f"Score should increase: {pre_score} -> {post_score}"
        )
