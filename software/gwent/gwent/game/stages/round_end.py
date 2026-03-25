"""RoundEnd stage — resolve the round after both players pass.

Determines the winner, removes gems, applies faction abilities,
and checks for game over.
"""

import random
from typing import Callable

import gwent.game.stages.base
import gwent.messaging.ctrl
import gwent.messaging.choice

from gwent.game.constants import PLAYER
from gwent.game.board import Board, ROWS


class RoundEnd(gwent.game.stages.base.GameStage):

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_ROUND_END

    def activate(self, complete: Callable, cancel: Callable, board: Board):
        super().activate(complete, cancel)
        self._board = board
        self._game_over = False
        self._determine_winner()

    def _determine_winner(self):
        p1_score = self._board.calculate_player_score(PLAYER.ONE)
        p2_score = self._board.calculate_player_score(PLAYER.TWO)

        self._log.info({
            'action': 'round_end',
            'round': self._board.round_number,
            'p1_score': p1_score,
            'p2_score': p2_score,
        })

        if p1_score > p2_score:
            winner, loser = PLAYER.ONE, PLAYER.TWO
        elif p2_score > p1_score:
            winner, loser = PLAYER.TWO, PLAYER.ONE
        else:
            # Tie: Nilfgaardian wins ties
            if self._board.factions[PLAYER.ONE] == "Nilfgaardian":
                winner, loser = PLAYER.ONE, PLAYER.TWO
            elif self._board.factions[PLAYER.TWO] == "Nilfgaardian":
                winner, loser = PLAYER.TWO, PLAYER.ONE
            else:
                winner, loser = None, None

        # Remove gems
        if loser:
            self._board.players[loser].gems -= 1
            result = f"Player {'1' if winner == PLAYER.ONE else '2'} wins round {self._board.round_number}!"
        elif winner is None:
            self._board.players[PLAYER.ONE].gems -= 1
            self._board.players[PLAYER.TWO].gems -= 1
            result = f"Round {self._board.round_number} is a draw! Both lose a gem."
        else:
            result = ""

        self._winner = winner
        self._loser = loser

        # Apply faction end-of-round abilities
        self._apply_faction_abilities(winner)

        # Check game over
        p1_gems = self._board.players[PLAYER.ONE].gems
        p2_gems = self._board.players[PLAYER.TWO].gems
        self._game_over = p1_gems <= 0 or p2_gems <= 0

        gems_info = f"Gems: P1={p1_gems}, P2={p2_gems}"

        if self._game_over:
            if p1_gems <= 0 and p2_gems <= 0:
                self.publish_prompt(f"{result} {gems_info}. Game over — it's a draw! Press OK.")
            elif p1_gems <= 0:
                self.publish_prompt(f"{result} {gems_info}. Game over — Player 2 wins the match! Press OK.")
            else:
                self.publish_prompt(f"{result} {gems_info}. Game over — Player 1 wins the match! Press OK.")
        else:
            self.publish_prompt(
                f"{result} {gems_info}. Press OK for next round.",
                ok=True, cancel=False, clear_choices=True)

        self._log.info({
            'action': 'round_result',
            'winner': str(winner) if winner else 'draw',
            'p1_gems': p1_gems,
            'p2_gems': p2_gems,
            'game_over': self._game_over,
        })

    def _apply_faction_abilities(self, winner):
        """Apply end-of-round faction abilities."""
        for player in (PLAYER.ONE, PLAYER.TWO):
            faction = self._board.factions[player]
            pb = self._board.players[player]

            if faction == "Monsters":
                # Keep the strongest non-hero card on the board
                strongest = None
                strongest_row = None
                strongest_val = 0
                for row_name in ROWS:
                    for card in pb.rows[row_name]:
                        if card.has_specialty and card.specialty == "hero":
                            continue
                        s = card.strength or 0
                        if s > strongest_val:
                            strongest = card
                            strongest_row = row_name
                            strongest_val = s
                # All other cards go to discard — the kept card stays
                if strongest:
                    self._log.info(f"Monsters keep {strongest.name} on board")

            elif faction == "Northern Realms" and player == winner:
                # Winner draws 1 extra card from deck
                drawn = self._board.draw_from_deck(player, 1)
                if drawn:
                    self._log.info(f"Northern Realms draws {drawn[0].name}")

            elif faction == "Skellige":
                # Resurrect 2 random cards from discard to hand
                non_hero = [c for c in pb.discard
                            if not (c.has_specialty and c.specialty == "hero")]
                resurrect_count = min(2, len(non_hero))
                if resurrect_count > 0:
                    resurrected = random.sample(non_hero, resurrect_count)
                    for card in resurrected:
                        pb.discard.remove(card)
                        self._board.hands[player].append(card)
                        self._log.info(f"Skellige resurrects {card.name}")

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

        if choice.id == 'y' and choice.text == 'ok':
            if self._game_over:
                self.complete(self._board, True)
            else:
                # Prepare for next round
                # Loser goes first next round (or random if draw)
                if self._loser:
                    self._board.current_player = self._loser
                else:
                    self._board.current_player = random.choice([PLAYER.ONE, PLAYER.TWO])

                self._board.clear_round()
                self.complete(self._board, False)

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
        self.publish_error("Round is over — press OK to continue")
