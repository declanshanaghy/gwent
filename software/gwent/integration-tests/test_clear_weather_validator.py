"""Integration test for Foltest: Lord Commander — clear all weather effects.

Tests the clear_weather leader ability by:
1. Having PLAYER.ONE play a weather card first
2. Verifying weather is active
3. PLAYER.TWO activates their clear_weather leader
4. Asserting weather_rows is empty and leader_used is True

Requires a running gwent game loaded with a recording where:
- PLAYER.ONE has at least one weather card in hand
- PLAYER.TWO leader has clear_weather ability

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_clear_weather_validator.py \
        --recording <recording.json> -v
"""

from conftest import card_names


class TestClearWeather:

    def test_initial_state(self, game, recording):
        """Verify the game loaded with no active weather."""
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"
        assert board["current_player"] == "PLAYER.ONE"
        assert board["players"]["PLAYER.TWO"]["leader_used"] is False
        assert board["weather_rows"] == []

    def test_clear_weather_full_flow(self, game, recording):
        """Play weather, then clear it with leader ability."""
        rec = recording["state"]
        p1_hand = rec["board"]["hands"]["PLAYER.ONE"]
        leader2 = rec["leader2"]

        # Find a weather card in P1's hand
        weather_card = next(
            (c for c in p1_hand if c.get("specialty") == "weather"
             and c.get("ranges")),
            None,
        )
        assert weather_card is not None, "P1 needs a weather card with a range in hand"
        weather_row = weather_card["ranges"][0]

        # --- P1 plays weather card ---
        state = game.inject_card_and_wait(weather_card)
        board = state["state"]["board"]

        # Weather should now be active on the card's row
        assert weather_row in board["weather_rows"], (
            f"Expected {weather_row} in weather_rows after playing {weather_card['name']}, "
            f"got {board['weather_rows']}"
        )

        # Wait for turn to advance to P2
        board = game.wait_for_current_player("PLAYER.TWO")
        assert board["current_player"] == "PLAYER.TWO"

        # --- P2 activates clear_weather leader ---
        state = game.inject_card_and_wait(leader2)
        board = state["state"]["board"]

        assert board["players"]["PLAYER.TWO"]["leader_used"] is True
        assert board["weather_rows"] == [], (
            f"Expected empty weather_rows after clear_weather, got {board['weather_rows']}"
        )

        # Turn should advance back to P1
        board = game.wait_for_current_player("PLAYER.ONE")
        assert board["current_player"] == "PLAYER.ONE"
