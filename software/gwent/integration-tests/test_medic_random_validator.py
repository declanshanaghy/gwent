"""Integration test for Emhyr Invader — medic restores random unit.

Tests the medic_random leader ability by:
1. Activating the leader (sets medic_random flag)
2. P1 plays a medic card while discard has a non-hero card
3. Asserting the medic auto-picks a random card from discard (no scan prompt)

Requires a recording where P1 has a medic card in hand and a card in discard.

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_medic_random_validator.py \
        --recording <recording.json> -v
"""

from conftest import card_names


class TestMedicRandom:

    def test_initial_state(self, game, recording):
        """Verify P1 has a medic card and a non-empty discard."""
        rec = recording["state"]
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"
        assert board["current_player"] == "PLAYER.ONE"
        assert board["players"]["PLAYER.ONE"]["leader_used"] is False

        # P1 must have a medic in hand
        p1_hand = rec["board"]["hands"]["PLAYER.ONE"]
        has_medic = any("medic" in c.get("abilities", []) for c in p1_hand)
        assert has_medic, "P1 needs a medic card in hand"

        # P1 must have non-empty discard
        assert len(board["players"]["PLAYER.ONE"]["discard"]) > 0, \
            "P1 needs at least one card in discard"

    def test_medic_random_full_flow(self, game, recording):
        """Activate medic_random, then play medic — card auto-restored."""
        import time
        rec = recording["state"]
        leader = rec["leader1"]
        p1_hand = rec["board"]["hands"]["PLAYER.ONE"]
        initial_hand_size = len(p1_hand)
        initial_discard_size = len(rec["board"]["players"]["PLAYER.ONE"]["discard"])

        # Find the medic card
        medic_card = next(
            c for c in p1_hand if "medic" in c.get("abilities", [])
        )

        # --- Activate leader ability ---
        state = game.inject_card_and_wait(leader)
        board = state["state"]["board"]
        assert board["players"]["PLAYER.ONE"]["leader_used"] is True

        # Wait for turn to advance back to P1 (after TTS)
        # Leader ability is an announce-and-advance, so turn goes to P2 then back
        board = game.wait_for_current_player("PLAYER.TWO")

        # --- P2 passes so P1 can play medic ---
        game.inject_choice("p", "Player 2 Pass")
        time.sleep(3)
        board = game.wait_for_current_player("PLAYER.ONE")

        # Record discard state before medic
        pre_discard = card_names(board["players"]["PLAYER.ONE"]["discard"])
        pre_hand_size = len(board["hands"]["PLAYER.ONE"])

        # --- P1 plays medic card ---
        # With medic_random active, it should auto-pick from discard
        # Wait for turn prompt TTS to finish before injecting
        time.sleep(5)
        state = game.inject_card_and_wait(medic_card)
        board = state["state"]["board"]

        # Medic card was placed on board (in its row)
        medic_row = medic_card.get("ranges", ["siege"])[0]
        row_names = card_names(board["players"]["PLAYER.ONE"]["rows"][medic_row])
        assert medic_card["name"] in row_names, (
            f"Medic card {medic_card['name']} should be on {medic_row} row"
        )

        # A card was restored from discard to hand
        post_discard = card_names(board["players"]["PLAYER.ONE"]["discard"])
        post_hand_size = len(board["hands"]["PLAYER.ONE"])

        # Discard should have shrunk by 1
        assert len(post_discard) == initial_discard_size - 1, (
            f"Discard should shrink by 1: was {initial_discard_size}, "
            f"now {len(post_discard)}"
        )

        # Hand should be: pre - 1 (medic played) + 1 (card restored) = same
        # But medic was removed from hand and placed on board, then a discard
        # card was added to hand. So: pre_hand - 1 + 1 = pre_hand
        assert post_hand_size == pre_hand_size - 1 + 1, (
            f"Hand size should be {pre_hand_size}: "
            f"was {pre_hand_size}, now {post_hand_size}"
        )
