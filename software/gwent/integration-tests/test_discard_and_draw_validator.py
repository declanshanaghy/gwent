"""Integration test for Eredin: Destroyer of Worlds — discard 2, draw 1.

Tests the discard_and_draw leader ability by:
1. Verifying initial state (correct leaders, hand/deck sizes)
2. Injecting the leader card via MQTT
3. Scanning 2 hand cards to discard
4. Scanning 1 deck card to draw
5. Asserting final state: hand size, discard pile, deck size, turn advancement

Requires a running gwent game loaded with a recording that has
a PLAYER.ONE leader with discard_and_draw ability.

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_discard_and_draw_validator.py \
        --recording <recording.json> -v
"""

from conftest import card_names


class TestDiscardAndDraw:

    def test_initial_state(self, game, recording):
        """Verify the game loaded correctly at PlayRound with expected sizes."""
        rec = recording["state"]
        state = game.get_state()
        board = state["state"]["board"]

        assert state["active_stage"] == "PlayRound"
        assert board["current_player"] == "PLAYER.ONE"
        assert board["players"]["PLAYER.ONE"]["leader_used"] is False
        assert len(board["hands"]["PLAYER.ONE"]) == len(rec["board"]["hands"]["PLAYER.ONE"])
        assert len(board["decks"]["PLAYER.ONE"]) == len(rec["board"]["decks"]["PLAYER.ONE"])
        assert len(board["players"]["PLAYER.ONE"]["discard"]) == 0

    def test_discard_and_draw_full_flow(self, game, recording):
        """Exercise the full discard 2 + draw 1 leader ability flow."""
        rec = recording["state"]
        leader = rec["leader1"]
        p1_hand = rec["board"]["hands"]["PLAYER.ONE"]
        p1_deck = rec["board"]["decks"]["PLAYER.ONE"]
        initial_hand_size = len(p1_hand)
        initial_deck_size = len(p1_deck)

        # Pick 2 weakest non-hero hand cards to discard
        discardable = [c for c in p1_hand
                       if c.get("specialty") != "hero" and c.get("strength", 0)]
        discardable.sort(key=lambda c: c.get("strength", 0))
        discard_cards = discardable[:2]
        assert len(discard_cards) == 2, "Need at least 2 discardable cards in hand"

        # Pick first deck card to draw
        draw_card = p1_deck[0]

        # --- Activate leader ability ---
        state = game.inject_card_and_wait(leader)
        board = state["state"]["board"]
        assert board["players"]["PLAYER.ONE"]["leader_used"] is True

        # --- Discard card 1 ---
        state = game.inject_card_and_wait(discard_cards[0])
        board = state["state"]["board"]
        assert len(board["hands"]["PLAYER.ONE"]) == initial_hand_size - 1
        assert discard_cards[0]["name"] in card_names(
            board["players"]["PLAYER.ONE"]["discard"])

        # --- Discard card 2 ---
        state = game.inject_card_and_wait(discard_cards[1])
        board = state["state"]["board"]
        assert len(board["hands"]["PLAYER.ONE"]) == initial_hand_size - 2
        assert len(board["players"]["PLAYER.ONE"]["discard"]) == 2

        # --- Draw card from deck ---
        state = game.inject_card_and_wait(draw_card)
        board = state["state"]["board"]

        # Final state assertions
        assert len(board["hands"]["PLAYER.ONE"]) == initial_hand_size - 2 + 1
        assert len(board["decks"]["PLAYER.ONE"]) == initial_deck_size - 1
        assert len(board["players"]["PLAYER.ONE"]["discard"]) == 2
        assert draw_card["name"] in card_names(board["hands"]["PLAYER.ONE"])
        for dc in discard_cards:
            assert dc["name"] in card_names(
                board["players"]["PLAYER.ONE"]["discard"])

        # Turn should advance after TTS completes
        board = game.wait_for_current_player("PLAYER.TWO")
        assert board["current_player"] == "PLAYER.TWO"
