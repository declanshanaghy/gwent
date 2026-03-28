"""Integration test for Eredin: King of the Wild Hunt — pick any weather from deck.

Tests the weather_ranges leader ability by:
1. Waiting for PLAYER.TWO's turn
2. PLAYER.TWO activates Eredin leader ability
3. When multiple weather cards are in deck, scanning one to complete the pick
4. Verifying weather is now active on the board

NOTE: This test runs after test_half_weather_penalty_validator in the same session,
so the game state reflects prior moves (weather on close, several cards played).

Requires a running gwent game loaded with a recording where:
- PLAYER.TWO leader has weather_ranges ability
- PLAYER.TWO has weather cards in their deck (not hand)

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_half_weather_penalty_validator.py \
           software/gwent/integration-tests/test_weather_ranges_validator.py \
        --recording <recording.json> -v
"""

import time

from conftest import card_names


class TestWeatherRanges:

    def test_initial_state(self, game, recording):
        """Verify the game is loaded and P2 has weather in deck."""
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"
        assert board["players"]["PLAYER.TWO"]["leader_used"] is False

    def test_weather_ranges_full_flow(self, game, recording):
        """P2 uses leader to play weather from deck."""
        rec = recording["state"]
        p1_hand = rec["board"]["hands"]["PLAYER.ONE"]
        p2_deck_rec = rec["board"]["decks"]["PLAYER.TWO"]
        leader2 = rec["leader2"]

        # Ensure it's P2's turn — if it's P1's turn, play a card to advance
        board = game.get_board()
        if board["current_player"] == "PLAYER.ONE":
            # Find a non-agile playable card in P1's hand
            p1_card = next(
                (c for c in p1_hand
                 if c.get("strength") and c.get("ranges")
                 and len(c.get("ranges", [])) == 1),
                None,
            )
            if p1_card:
                state = game.inject_card_and_wait(p1_card)
            board = game.wait_for_current_player("PLAYER.TWO")

        assert board["current_player"] == "PLAYER.TWO"

        # Record weather state before leader
        weather_before = set(board["weather_rows"])

        # Count weather cards in P2's deck before
        p2_deck_live = board["decks"]["PLAYER.TWO"]
        weather_deck_before = [c for c in p2_deck_live if c.get("specialty") == "weather"]
        assert len(weather_deck_before) > 0, (
            f"P2 needs weather cards in deck, got: {card_names(p2_deck_live)}"
        )

        # Find a weather card from P2's deck whose row is NOT already weathered
        weather_to_scan = next(
            (c for c in p2_deck_live
             if c.get("specialty") == "weather" and c.get("ranges")
             and c["ranges"][0] not in weather_before),
            None,
        )
        # Fall back to any weather card if all rows already weathered
        if weather_to_scan is None:
            weather_to_scan = next(
                (c for c in p2_deck_live
                 if c.get("specialty") == "weather" and c.get("ranges")),
                None,
            )
        assert weather_to_scan is not None, "P2 needs a weather card with ranges in deck"
        expected_row = weather_to_scan["ranges"][0]

        # --- P2 activates leader: pick weather from deck ---
        state = game.inject_card_and_wait(leader2)
        board = state["state"]["board"]

        assert board["players"]["PLAYER.TWO"]["leader_used"] is True

        # With multiple weather cards, the game prompts to scan one.
        # Always inject the weather card scan since the game awaits it.
        time.sleep(1)
        state = game.inject_card_and_wait(weather_to_scan)
        board = state["state"]["board"]
        weather_after = set(board["weather_rows"])

        # Weather should now be active on the expected row
        assert expected_row in weather_after, (
            f"Expected '{expected_row}' in weather_rows after leader, "
            f"got {weather_after}"
        )

        # The weather card should have been removed from P2's deck
        p2_deck_after = board["decks"]["PLAYER.TWO"]
        weather_deck_after = [c for c in p2_deck_after if c.get("specialty") == "weather"]
        assert len(weather_deck_after) < len(weather_deck_before), (
            f"Expected fewer weather cards in deck after leader, "
            f"before={len(weather_deck_before)}, after={len(weather_deck_after)}"
        )

        # Turn should advance back to P1
        board = game.wait_for_current_player("PLAYER.ONE")
        assert board["current_player"] == "PLAYER.ONE"
