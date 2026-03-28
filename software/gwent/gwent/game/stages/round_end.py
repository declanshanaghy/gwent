"""RoundEnd stage — resolve the round after both players pass.

Determines the winner, removes gems, applies faction abilities,
and checks for game over.
"""

import random
from typing import Callable

import gwent.game
import gwent.game
import gwent.game.stages.base
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play

from gwent.game.constants import PLAYER
from gwent.game.board import Board, ROWS


LOCATIONS = [
    "Vizima", "Oxenfurt", "Novigrad", "Kaer Morhen", "the Skellige Isles",
    "Cintra", "Vengerberg", "Toussaint", "Loc Muinne", "Vergen",
    "Flotsam", "Brenna", "Sodden Hill", "Thanedd Isle", "White Orchard",
    "Crow's Perch", "Velen", "Beauclair", "Kerack", "Ard Skellig",
]

_WIN_TEMPLATES = [
    "The tavern at {location} erupts! {winner} crushes {loser}, {w_score} to {l_score}!",
    "Word spreads from {location}: {winner} bested {loser} by {margin} points!",
    "{winner} sweeps round {round} like a Skellige storm! {w_score} over {loser}'s {l_score}.",
    "The bards of {location} will sing of {winner}'s {w_score}-point triumph over {loser}!",
    "Not even the mages of Aretuza could save {loser}. {winner} wins {w_score} to {l_score} at {location}!",
    "{loser}'s forces crumble at the gates of {location}. {winner} stands victorious, {w_score} to {l_score}.",
    "From the walls of {location}, {winner} claims round {round}! {margin} points to spare.",
    "Dandelion scribbles furiously: {winner} humiliates {loser} at {location}, {w_score} to {l_score}!",
    "The Continent trembles! {winner} dominates round {round} at {location}. {w_score} to {l_score}.",
    "{winner} outplays {loser} at {location} with the cunning of a Nilfgaardian spy. {w_score} to {l_score}!",
    "A decisive blow at {location}! {winner} takes the round {w_score} to {l_score}.",
    "{loser} retreats from {location} in shame. {winner} wins by {margin}!",
    "The merchants of {location} bet heavily on {winner}. {w_score} to {l_score} proves them right!",
    "{winner} raises a tankard at {location}! Round {round} won, {w_score} to {l_score}.",
    "The Witchers of Kaer Morhen nod approvingly. {winner} bests {loser} by {margin} at {location}.",
    "Like Geralt slaying a griffin, {winner} dismantles {loser} at {location}! {w_score} to {l_score}.",
    "Round {round} at {location} belongs to {winner}! {loser} falls {margin} short.",
    "Triss would be proud. {winner} outmaneuvers {loser} at {location}, {w_score} to {l_score}.",
    "The dwarves of Mahakam raise their axes for {winner}! {w_score} to {l_score} at {location}.",
    "{winner} conquers {location}! {loser} left with nothing but {l_score} points and bruised pride.",
]

_DRAW_TEMPLATES = [
    "The battle at {location} ends in stalemate! {p1} and {p2} tie at {score}.",
    "Neither army yields at {location}. Both sides score {score}. Both lose a gem!",
    "Dandelion can't pick a winner at {location}. {p1} and {p2} tied at {score}!",
    "The fog over {location} clears to reveal a draw. {score} to {score}. A gem from each!",
    "Even Gaunter O'Dimm couldn't decide this one at {location}. Both score {score}!",
]


def _leader_nickname(board, player):
    """Get a short leader nickname for announcements."""
    from gwent.game.stages.play_round import PlayRound
    leader = board.leaders.get(player)
    if leader:
        name = leader.name if hasattr(leader, 'name') else leader.get('name', '')
        return PlayRound._LEADER_NICKNAMES.get(name, name)
    return "Player 1" if str(player) == "PLAYER.ONE" else "Player 2"


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

        # Remove gems and build commentary
        location = random.choice(LOCATIONS)
        rnd = self._board.round_number

        if loser:
            self._board.players[loser].gems -= 1
            w_label = _leader_nickname(self._board, winner)
            l_label = _leader_nickname(self._board, loser)
            w_score = max(p1_score, p2_score)
            l_score = min(p1_score, p2_score)
            margin = w_score - l_score
            w_faction = self._board.factions.get(winner, "")
            l_faction = self._board.factions.get(loser, "")
            commentary = random.choice(_WIN_TEMPLATES).format(
                winner=w_label, loser=l_label,
                w_score=w_score, l_score=l_score,
                w_faction=w_faction, l_faction=l_faction,
                margin=margin, round=rnd, location=location,
            )
        elif winner is None:
            self._board.players[PLAYER.ONE].gems -= 1
            self._board.players[PLAYER.TWO].gems -= 1
            commentary = random.choice(_DRAW_TEMPLATES).format(
                p1=_leader_nickname(self._board, PLAYER.ONE),
                p2=_leader_nickname(self._board, PLAYER.TWO),
                score=p1_score, round=rnd, location=location,
            )
        else:
            commentary = ""

        self._winner = winner
        self._loser = loser

        # Publish gem updates to player displays
        self._publish_gems()

        # Apply faction end-of-round abilities
        self._apply_faction_abilities(winner)

        # Check game over
        p1_gems = self._board.players[PLAYER.ONE].gems
        p2_gems = self._board.players[PLAYER.TWO].gems
        self._game_over = p1_gems <= 0 or p2_gems <= 0

        g1 = "gem" if p1_gems == 1 else "gems"
        g2 = "gem" if p2_gems == 1 else "gems"
        p1_name = _leader_nickname(self._board, PLAYER.ONE)
        p2_name = _leader_nickname(self._board, PLAYER.TWO)
        gems_info = f"{p1_name}: {p1_gems} {g1}. {p2_name}: {p2_gems} {g2}."

        prompt = f"{commentary} {gems_info}"

        winner_faction = self._board.factions.get(winner) if winner else None
        self._publish_prompt_then(prompt, self._advance,
                                  faction=winner_faction)

        self._log.info({
            'action': 'round_result',
            'winner': str(winner) if winner else 'draw',
            'p1_gems': p1_gems,
            'p2_gems': p2_gems,
            'game_over': self._game_over,
        })

    def _publish_gems(self):
        """Publish gem updates to player displays."""
        for player in (PLAYER.ONE, PLAYER.TWO):
            gems = self._board.players[player].gems
            msg = gwent.messaging.card_play.Message.with_update_gems(str(player), gems)
            topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
            self.publish(topic, msg)

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

    def _advance(self):
        """Progress to the next stage."""
        if self._game_over:
            self.complete(self._board, True)
        else:
            # Loser goes first next round (or random if draw)
            if self._loser:
                self._board.current_player = self._loser
            else:
                self._board.current_player = random.choice([PLAYER.ONE, PLAYER.TWO])

            self._board.clear_round()
            self.complete(self._board, False)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
        self.publish_error("Round is over — press OK to continue")
