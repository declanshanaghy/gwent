"""DisplayWinner stage — game over screen.

Shows the match winner and returns to main menu on OK.
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

_WIN_TEMPLATES = [
    "Player {w_num} wins the match! {w_gems} gems to {l_gems}.",
    "Victory for Player {w_num}! The battlefield belongs to them. {w_gems} gems to {l_gems}.",
    "Player {w_num} claims the prize! {w_gems} gems standing, Player {l_num} left with {l_gems}.",
    "The crowd roars! Player {w_num} triumphs with {w_gems} gems! Player {l_num} has {l_gems}.",
    "A glorious win for Player {w_num}! {w_gems} to {l_gems}. The bards will sing!",
    "Player {w_num} stands victorious! {w_gems} gems shine bright. Player {l_num}'s {l_gems} fade to dust.",
    "Like Geralt collecting his reward! Player {w_num} wins {w_gems} to {l_gems}!",
    "The White Wolf would be proud! Player {w_num} conquers with {w_gems} gems to {l_gems}!",
    "Dandelion's quill flies! Player {w_num}'s victory — {w_gems} gems to {l_gems} — will echo across the Continent!",
    "A match worthy of legend! Player {w_num} prevails with {w_gems} gems. Player {l_num} falls at {l_gems}.",
    "By the Eternal Fire! Player {w_num} burns through with {w_gems} gems! Player {l_num} is left smoldering at {l_gems}.",
    "Triss herself couldn't conjure a finer finish! Player {w_num} wins {w_gems} to {l_gems}!",
    "Player {w_num} drinks from the cup of victory! {w_gems} gems to Player {l_num}'s bitter {l_gems}.",
    "The cards have spoken! Player {w_num} seizes glory with {w_gems} gems. Player {l_num} retreats with {l_gems}.",
    "Vesemir nods approvingly! Player {w_num} commands the table — {w_gems} gems to {l_gems}!",
    "Player {w_num} plays like a Nilfgaardian general! {w_gems} gems crush Player {l_num}'s {l_gems}.",
    "A decisive rout! Player {w_num} sweeps the field with {w_gems} gems. Player {l_num} manages only {l_gems}.",
    "Even Dijkstra's spies couldn't have predicted it! Player {w_num} takes {w_gems} gems to {l_gems}!",
    "Player {w_num} earns a toast at every inn on the Continent! {w_gems} gems to Player {l_num}'s {l_gems}.",
    "Yennefer raises an eyebrow — impressive! Player {w_num} dominates with {w_gems} gems against {l_gems}.",
]

_DRAW_TEMPLATES = [
    "The match is a draw! Both players have {gems} gems. Neither army prevails.",
    "A stalemate for the ages! Both commanders hold {gems} gems. The Continent is undecided.",
    "Neither player yields! {gems} gems apiece. Even Gaunter O'Dimm couldn't pick a winner!",
    "Deadlocked at {gems} gems! The tavern argues all night about who really won.",
    "A draw most foul! {gems} gems each. Lambert storms off in disgust.",
    "Both armies bloodied, neither broken! {gems} gems remain on each side. Rematch?",
    "The coin lands on its edge! {gems} gems each. Destiny itself cannot decide.",
    "Triss and Yennefer would call this a tie — {gems} gems apiece. Neither sorceress blinks.",
    "A draw at {gems} gems! The innkeeper pours another round while both players stare daggers.",
    "Even the Lodge of Sorceresses couldn't break this deadlock! {gems} gems each.",
    "Locked at {gems} gems! Somewhere, Zoltan flips a table and demands a rematch.",
    "The Northern Realms and Nilfgaard sign an armistice! {gems} gems each — peace, for now.",
]


class DisplayWinner(gwent.game.stages.base.GameStage):

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_DISPLAY_WINNER

    def activate(self, complete: Callable, cancel: Callable, board: Board):
        super().activate(complete, cancel)

        p1_gems = board.players[PLAYER.ONE].gems
        p2_gems = board.players[PLAYER.TWO].gems

        if p1_gems > p2_gems:
            w_num, l_num = "1", "2"
            w_gems, l_gems = p1_gems, p2_gems
        elif p2_gems > p1_gems:
            w_num, l_num = "2", "1"
            w_gems, l_gems = p2_gems, p1_gems
        else:
            w_num, l_num = None, None
            w_gems, l_gems = p1_gems, p2_gems

        if gwent.game.BaseComponent.simple_mode:
            if w_num:
                msg = f"Player {w_num} wins. {w_gems} to {l_gems}."
            else:
                msg = f"Draw. {p1_gems} gems each."
        else:
            if w_num:
                msg = random.choice(_WIN_TEMPLATES).format(
                    w_num=w_num, l_num=l_num, w_gems=w_gems, l_gems=l_gems)
            else:
                msg = random.choice(_DRAW_TEMPLATES).format(gems=p1_gems)

        self._log.info({
            'action': 'display_winner',
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

        self.publish_prompt(
            f"Game Over! {msg}",
            ok=True, cancel=False, clear_choices=True,
            ok_text="Main Menu")

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)
        if choice.id == 'y':
            self.complete()

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)
