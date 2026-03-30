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
    "Blood and thunder at {location}! {winner} grinds {loser} into the dirt, {w_score} to {l_score}.",
    "A tale for the ages at {location}! {winner} takes round {round} by {margin}. {loser} never stood a chance.",
    "The sorceresses of the Lodge watch from {location} as {winner} dismantles {loser}. {w_score} to {l_score}.",
    "Zoltan Chivay would wager his last crown on {winner}! {w_score} to {l_score} at {location}.",
    "{loser} should have stayed home. {winner} claims round {round} at {location}, {w_score} to {l_score}!",
    "The druids of {location} foresaw this: {winner} triumphs over {loser} by {margin} points!",
    "Roach gallops through {location} with news of {winner}'s victory! {w_score} to {l_score} over {loser}.",
    "Vesemir would be proud. {winner} outfoxes {loser} at {location}, round {round}. {w_score} to {l_score}.",
    "{winner} plays like a grandmaster at {location}. {loser} falls behind by {margin}!",
    "The crows circle over {location} as {loser} crumbles. {winner} wins round {round}, {w_score} to {l_score}.",
    "A cunning gambit at {location}! {winner} lures {loser} into defeat. {w_score} to {l_score}!",
    "The Emperor himself would applaud. {winner} seizes {location}, crushing {loser} by {margin}.",
    "Yennefer smirks from the gallery at {location}. {winner} dispatches {loser}, {w_score} to {l_score}.",
    "Steel clashes at {location}! When the dust settles, {winner} stands tall. {w_score} to {l_score}.",
    "The innkeeper at {location} pours a victory ale for {winner}. {loser} drowns their sorrows at {l_score}.",
    "By the Eternal Fire! {winner} scorches {loser} at {location}. {w_score} to {l_score} in round {round}!",
    "Dijkstra's spies confirm it: {winner} has routed {loser} at {location} by {margin} points.",
    "The bonfires of {location} burn bright for {winner}! {loser} slinks away with only {l_score}.",
    "A masterful round at {location}! {winner} leaves {loser} speechless. {w_score} to {l_score}, round {round}.",
]

_DRAW_TEMPLATES = [
    "The battle at {location} ends in stalemate! {p1} and {p2} tie at {score}.",
    "Neither army yields at {location}. Both sides score {score}. Both lose a gem!",
    "Dandelion can't pick a winner at {location}. {p1} and {p2} tied at {score}!",
    "The fog over {location} clears to reveal a draw. {score} to {score}. A gem from each!",
    "Even Gaunter O'Dimm couldn't decide this one at {location}. Both score {score}!",
    "The battle of {location} grinds to a halt! {p1} and {p2} lock horns at {score}. Both lose a gem!",
    "Like two Witchers fighting over a contract! {p1} and {p2} tie at {score} in round {round} at {location}!",
    "The merchants of {location} can't pick a winner! {p1} and {p2} deadlocked at {score}. A gem from each!",
    "Stalemate at {location}! {p1} and {p2} matched blow for blow at {score}. Round {round} claims a gem from both!",
    "Lambert would call this pathetic! {p1} and {p2} both score {score} at {location}. Neither deserves to win!",
    "Geralt sighs at {location}. {p1} and {p2} locked at {score}. A pox on both houses!",
    "The crowd at {location} groans. {p1} and {p2} deadlocked at {score} in round {round}. Both lose a gem!",
    "Ciri would have ended this faster. {p1} and {p2} tie at {score} at {location}. How disappointing!",
    "A draw worthy of {location}'s muddiest brawl! {p1} and {p2} stuck at {score}. Both pay the price!",
    "The ravens of {location} caw in mockery. {p1} and {p2} matched at {score}. Round {round} claims two gems!",
    "Triss shakes her head at {location}. {p1} and {p2} both manage {score}. Neither advances unscathed!",
    "The dice land on edge at {location}! {p1} and {p2} share a grim {score}. A gem from each!",
    "No glory at {location} tonight. {p1} and {p2} stagger away from round {round} tied at {score}.",
    "Emhyr would have them both flogged. {p1} and {p2} draw at {score} in {location}. Two gems lost!",
    "The philosophers of Oxenfurt debate who lost worse. {p1} and {p2} tied at {score} at {location}!",
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

    def _msg_round_win(self, winner, loser, w_score, l_score, rnd, w_faction, l_faction):
        if gwent.game.BaseComponent.simple_mode:
            return f"Round {rnd}. {winner} wins {w_score} to {l_score}."
        location = random.choice(LOCATIONS)
        margin = w_score - l_score
        return random.choice(_WIN_TEMPLATES).format(
            winner=winner, loser=loser, w_score=w_score, l_score=l_score,
            w_faction=w_faction, l_faction=l_faction,
            margin=margin, round=rnd, location=location)

    def _msg_round_draw(self, p1, p2, score, rnd):
        if gwent.game.BaseComponent.simple_mode:
            return f"Round {rnd}. Draw at {score}."
        location = random.choice(LOCATIONS)
        return random.choice(_DRAW_TEMPLATES).format(
            p1=p1, p2=p2, score=score, round=rnd, location=location)

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
        rnd = self._board.round_number

        if loser:
            self._board.players[loser].gems -= 1
            w_label = _leader_nickname(self._board, winner)
            l_label = _leader_nickname(self._board, loser)
            w_score = max(p1_score, p2_score)
            l_score = min(p1_score, p2_score)
            commentary = self._msg_round_win(
                w_label, l_label, w_score, l_score, rnd,
                self._board.factions.get(winner, ""),
                self._board.factions.get(loser, ""))
        elif winner is None:
            self._board.players[PLAYER.ONE].gems -= 1
            self._board.players[PLAYER.TWO].gems -= 1
            commentary = self._msg_round_draw(
                _leader_nickname(self._board, PLAYER.ONE),
                _leader_nickname(self._board, PLAYER.TWO),
                p1_score, rnd)
        else:
            commentary = ""

        self._winner = winner
        self._loser = loser

        # Publish gem updates to player displays
        self._publish_gems()

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
                # Keep the strongest non-hero card on the board.
                # After clear_round, all cards are in discard — find the
                # strongest non-hero and move it back to its original row.
                strongest = None
                strongest_val = 0
                for card in pb.discard:
                    if card.has_specialty and card.specialty == "hero":
                        continue
                    s = card.strength or 0
                    if s > strongest_val:
                        strongest = card
                        strongest_val = s
                if strongest:
                    row_name = (strongest.ranges or ["close"])[0]
                    pb.discard.remove(strongest)
                    pb.rows[row_name].append(strongest)
                    self._log.info(f"Monsters keep {strongest.name} on {row_name}")

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

            # Clear board first (moves cards to discard), then apply faction
            # abilities so Skellige can resurrect from the populated discard
            # pile and Monsters' kept card can be restored to the board.
            self._board.clear_round()
            self._apply_faction_abilities(self._winner)
            self.complete(self._board, False)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
        _ROUND_OVER_PROMPTS = [
            "Round is over — press OK to continue",
            "The round has ended. Press OK when ready.",
            "Swords down! Press OK to move on.",
            "The dust settles. Press OK to proceed.",
            "This round is done. Press OK for the next.",
            "Cards are spent. Press OK to continue.",
        ]
        self.publish_error(random.choice(_ROUND_OVER_PROMPTS))
