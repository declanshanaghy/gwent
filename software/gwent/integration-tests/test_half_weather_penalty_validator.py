"""Integration test for King Bran — half weather strength penalty.

Tests the half_weather_penalty leader ability by:
1. P1 plays a close combat unit
2. P2 plays a unit (to advance turn)
3. P1 plays Biting Frost (affects own close row too)
4. Verify P1's unit is reduced (normal weather penalty)
5. P2 plays a unit (to advance turn)
6. P1 activates King Bran leader ability
7. Verify P1's unit now has half original strength instead of 1

Requires recording 021-skellige-vs-monsters.json:
- P1 (Skellige) has King Bran as leader, close units, and Biting Frost in hand
- P2 (Monsters) has playable units in hand

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_half_weather_penalty_validator.py \
        --recording <recording.json> -v
"""

from conftest import card_names


class TestHalfWeatherPenalty:

    def test_initial_state(self, game, recording):
        """Verify the game loaded correctly."""
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"
        assert board["current_player"] == "PLAYER.ONE"
        assert board["players"]["PLAYER.ONE"]["leader_used"] is False
        assert board["weather_rows"] == []

    def test_half_weather_penalty_flow(self, game, recording):
        """Play unit, apply weather, activate King Bran, verify half penalty."""
        rec = recording["state"]
        p1_hand = rec["board"]["hands"]["PLAYER.ONE"]
        p2_hand = rec["board"]["hands"]["PLAYER.TWO"]
        leader1 = rec["leader1"]

        # Find a close-only (non-agile, non-hero) unit in P1's hand with strength > 2
        unit_card = next(
            (c for c in p1_hand
             if c.get("strength") and c["strength"] > 2
             and c.get("ranges") == ["close"]
             and c.get("specialty") != "hero"),
            None,
        )
        assert unit_card is not None, "P1 needs a non-hero close-only unit with strength > 2"
        original_strength = unit_card["strength"]

        # Find Biting Frost in P1's hand
        frost_card = next(
            (c for c in p1_hand
             if c.get("specialty") == "weather"
             and "close" in c.get("ranges", [])),
            None,
        )
        assert frost_card is not None, "P1 needs a Biting Frost card in hand"

        # Find two non-agile playable cards in P2's hand (for turn advancement)
        p2_units = [
            c for c in p2_hand
            if c.get("strength") and c.get("ranges")
            and len(c.get("ranges", [])) == 1
        ]
        assert len(p2_units) >= 2, "P2 needs at least 2 non-agile playable cards"
        p2_card1, p2_card2 = p2_units[0], p2_units[1]

        # --- Turn 1: P1 plays close unit ---
        state = game.inject_card_and_wait(unit_card)
        board = state["state"]["board"]

        p1_close = board["players"]["PLAYER.ONE"]["rows"]["close"]
        played_names = card_names(p1_close)
        assert unit_card["name"] in played_names, (
            f"Expected {unit_card['name']} on close row, got {played_names}"
        )

        # Score should reflect original strength
        score_before_weather = board["scores"]["PLAYER.ONE"]["close"]
        assert score_before_weather >= original_strength

        # --- Turn 2: P2 plays a unit (advance turn) ---
        board = game.wait_for_current_player("PLAYER.TWO")
        state = game.inject_card_and_wait(p2_card1)

        # --- Turn 3: P1 plays Biting Frost ---
        board = game.wait_for_current_player("PLAYER.ONE")
        state = game.inject_card_and_wait(frost_card)
        board = state["state"]["board"]

        assert "close" in board["weather_rows"], (
            f"Expected 'close' in weather_rows, got {board['weather_rows']}"
        )

        # P1's close unit should now be reduced to 1 (normal weather)
        score_with_weather = board["scores"]["PLAYER.ONE"]["close"]
        # The unit contributes 1, there may also be bond multipliers
        # but the key thing is it's much less than original
        assert score_with_weather < original_strength, (
            f"Expected close score < {original_strength} with weather, "
            f"got {score_with_weather}"
        )

        # --- Turn 4: P2 plays another unit (advance turn) ---
        board = game.wait_for_current_player("PLAYER.TWO")
        state = game.inject_card_and_wait(p2_card2)

        # --- Turn 5: P1 activates King Bran ---
        board = game.wait_for_current_player("PLAYER.ONE")
        state = game.inject_card_and_wait(leader1)
        board = state["state"]["board"]

        assert board["players"]["PLAYER.ONE"]["leader_used"] is True

        # Verify the half_weather_penalty flag is set
        hwp = board.get("half_weather_penalty", {})
        assert hwp.get("PLAYER.ONE") is True, (
            f"Expected half_weather_penalty['PLAYER.ONE'] = True, got {hwp}"
        )
        assert hwp.get("PLAYER.TWO") is not True, (
            "half_weather_penalty should not be active for PLAYER.TWO"
        )

        # With half penalty, the unit should be at half strength (not 1)
        expected_half = max(1, original_strength // 2)
        score_half = board["scores"]["PLAYER.ONE"]["close"]
        # Score should be greater than when weather was at full penalty
        assert score_half > score_with_weather, (
            f"Expected close score > {score_with_weather} after half penalty, "
            f"got {score_half}"
        )
        # Score for our single unit row should include the half-strength value
        assert score_half >= expected_half, (
            f"Expected close score >= {expected_half} (half of {original_strength}), "
            f"got {score_half}"
        )

        # Turn should advance back to P2
        board = game.wait_for_current_player("PLAYER.TWO")
        assert board["current_player"] == "PLAYER.TWO"
