"""GameOver stage — final game over screen.

Announces the winner (or draw) based on gem count with flavorful
Witcher-themed commentary, then offers return to main menu.
"""

import random
from typing import Callable

import gwent.game
import gwent.game.stages.base
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card
import gwent.messaging.card_play

from gwent.game.constants import PLAYER
from gwent.game.board import Board

LOCATIONS = [
    "Vizima", "Oxenfurt", "Novigrad", "Kaer Morhen", "Skellige Isles",
    "Cintra", "Vengerberg", "Toussaint", "Loc Muinne", "Vergen",
    "Flotsam", "Nilfgaard", "Brenna", "Sodden Hill", "Thanedd Isle",
    "White Orchard", "Crow's Perch", "Velen", "Beauclair", "Kerack",
]

_WIN_TEMPLATES = [
    "{winner} trounces {loser}'s army at the battle of {location}! {w_gems} gems left to {l_gems}!",
    "{winner} crushes {loser} in a legendary showdown at {location}! {w_gems} gems left to {l_gems}!",
    "The bards will sing of how {winner} defeated {loser} at {location}. {w_gems} gems left to {l_gems}!",
    "{winner} outplays {loser} at the gates of {location}! {w_gems} gems left to {l_gems}.",
    "Victory for {winner}! {loser} retreats from {location} in shame. {w_gems} gems left to {l_gems}.",
    "{loser}'s forces crumble before {winner} at {location}! {w_gems} gems left to {l_gems}.",
    "A decisive victory! {winner} claims {location} from {loser}. {w_gems} gems left to {l_gems}!",
    "{winner} raises their banner over {location} after defeating {loser}! {w_gems} gems left to {l_gems}.",
]

_DRAW_TEMPLATES = [
    "Neither {leader1} nor {leader2} could claim {location}. Both armies destroyed!",
    "The battle of {location} ends in mutual destruction! {leader1} and {leader2} fall together.",
    "{leader1} and {leader2} fight to the death at {location}. No gems remain. No victor emerges.",
    "The tavern runs out of ale and warriors! {leader1} and {leader2} annihilate each other at {location}.",
    "Dandelion couldn't write a winner for this one. {leader1} and {leader2} both fall at {location}!",
    "A draw worthy of legend! {leader1} and {leader2} destroy each other at {location}. No gems left.",
]


class GameOver(gwent.game.stages.base.GameStage):

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_GAME_OVER

    def activate(self, complete: Callable, cancel: Callable, board: Board):
        super().activate(complete, cancel)

        p1_gems = board.players[PLAYER.ONE].gems
        p2_gems = board.players[PLAYER.TWO].gems

        leader1 = board.leaders[PLAYER.ONE].name if board.leaders.get(PLAYER.ONE) else "Player 1"
        leader2 = board.leaders[PLAYER.TWO].name if board.leaders.get(PLAYER.TWO) else "Player 2"
        location = random.choice(LOCATIONS)

        if p1_gems > p2_gems:
            msg = random.choice(_WIN_TEMPLATES).format(
                winner=leader1, loser=leader2, location=location,
                w_gems=p1_gems, l_gems=p2_gems)
        elif p2_gems > p1_gems:
            msg = random.choice(_WIN_TEMPLATES).format(
                winner=leader2, loser=leader1, location=location,
                w_gems=p2_gems, l_gems=p1_gems)
        else:
            msg = random.choice(_DRAW_TEMPLATES).format(
                leader1=leader1, leader2=leader2, location=location)

        self._log.info({
            'action': 'game_over',
            'p1_gems': p1_gems,
            'p2_gems': p2_gems,
            'message': msg,
        })

        # Publish final gem state to player displays
        for player in (PLAYER.ONE, PLAYER.TWO):
            gems = board.players[player].gems
            gem_msg = gwent.messaging.card_play.Message.with_update_gems(str(player), gems)
            topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
            self.publish(topic, gem_msg)

        if p1_gems > p2_gems:
            winner_faction = board.factions.get(PLAYER.ONE)
        elif p2_gems > p1_gems:
            winner_faction = board.factions.get(PLAYER.TWO)
        else:
            winner_faction = None

        self.publish_prompt(
            f"Game Over! {msg}",
            ok=True, cancel=False, clear_choices=True,
            ok_text="Main Menu", faction=winner_faction)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)
        if choice.id == 'y':
            self.complete()

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
