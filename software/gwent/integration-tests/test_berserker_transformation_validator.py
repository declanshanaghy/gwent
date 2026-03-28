"""Integration test for Mardroeme berserker transformation (#27).

Tests that playing Mardroeme transforms all berserker cards on the board:
1. P1 plays Berserker (str 4) to close row
2. P2 plays a unit (to advance turn)
3. P1 plays Mardroeme
4. Verify Berserker replaced by Transformed Vildkaarl (str 14) on close row

Requires recording 022-skellige-vs-monsters-berserker.json:
- P1 (Skellige) has Berserker and Mardroeme in hand

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_berserker_transformation_validator.py \
        --recording <recording.json> -v
"""

from conftest import card_names


class TestBerserkerTransformation:

    def test_initial_state(self, game, recording):
        """Verify the game loaded correctly."""
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"
        assert board["current_player"] == "PLAYER.ONE"

        # Verify P1 has Berserker and Mardroeme in hand
        p1_hand = board["hands"]["PLAYER.ONE"]
        names = card_names(p1_hand)
        assert "Berserker" in names, f"P1 needs Berserker in hand, got {names}"
        assert "Mardroeme: 1" in names, f"P1 needs Mardroeme in hand, got {names}"

    def test_berserker_transformation_flow(self, game, recording):
        """Play Berserker, then Mardroeme, verify transformation."""
        rec = recording["state"]
        p1_hand = rec["board"]["hands"]["PLAYER.ONE"]
        p2_hand = rec["board"]["hands"]["PLAYER.TWO"]

        # Find cards
        berserker = next(c for c in p1_hand if c["name"] == "Berserker")
        mardroeme = next(c for c in p1_hand if c["name"] == "Mardroeme: 1")
        p2_card = next(
            c for c in p2_hand
            if c.get("strength") and c.get("ranges")
            and len(c.get("ranges", [])) == 1
        )

        # --- P1 plays Berserker to close row ---
        state = game.inject_card_and_wait(berserker)
        board = state["state"]["board"]

        p1_close = board["players"]["PLAYER.ONE"]["rows"]["close"]
        close_names = card_names(p1_close)
        assert "Berserker" in close_names, (
            f"Expected Berserker on close row, got {close_names}"
        )

        # Score should be 4 (Berserker's base strength)
        close_score = board["scores"]["PLAYER.ONE"]["close"]
        assert close_score >= 4, (
            f"Expected close score >= 4, got {close_score}"
        )

        # --- P2 plays a unit to advance turn ---
        board = game.wait_for_current_player("PLAYER.TWO")
        state = game.inject_card_and_wait(p2_card)

        # --- P1 plays Mardroeme ---
        board = game.wait_for_current_player("PLAYER.ONE")
        state = game.inject_card_and_wait(mardroeme)
        board = state["state"]["board"]

        # Berserker should be GONE from close row
        p1_close = board["players"]["PLAYER.ONE"]["rows"]["close"]
        close_names = card_names(p1_close)
        assert "Berserker" not in close_names, (
            f"Berserker should be transformed, but still on close row: {close_names}"
        )

        # Transformed Vildkaarl should be on close row
        assert any("Transformed Vildkaarl" in n for n in close_names), (
            f"Expected Transformed Vildkaarl on close row, got {close_names}"
        )

        # Score should reflect the transformation (14 str instead of 4)
        close_score = board["scores"]["PLAYER.ONE"]["close"]
        assert close_score >= 14, (
            f"Expected close score >= 14 after transformation, got {close_score}"
        )

        # Mardroeme should be in discard
        p1_disc = board["players"]["PLAYER.ONE"]["discard"]
        disc_names = card_names(p1_disc)
        assert "Mardroeme: 1" in disc_names, (
            f"Expected Mardroeme in discard, got {disc_names}"
        )

        # Turn should advance to P2
        board = game.wait_for_current_player("PLAYER.TWO")
        assert board["current_player"] == "PLAYER.TWO"
