import random
from typing import Callable

import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.mfd


MAIN_MENU_GREETINGS = [
    "Welcome to Gwent",
    "A round of Gwent?",
    "The cards await",
    "Care for a game?",
    "Fancy a hand?",
    "How about a round?",
    "Toss a coin, play a card",
    "Gwent, anyone?",
]


class MainMenu(gwent.game.stages.base.GameStage):
    CHOICE_RANDOM_DEAL_ID = '1'
    CHOICE_PLAYER_DEAL_ID = '2'

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_MAIN_MENU

    def activate(self, complete: Callable, cancel: Callable):
        super().activate(complete, cancel)
        self.publish_main_menu()

    def publish_main_menu(self):
        self.publish_prompt(random.choice(MAIN_MENU_GREETINGS),
                           ok=False, cancel=False,
                           clear_choices=False)
        choices = [
            gwent.messaging.choice.Message.from_properties(
                self.CHOICE_RANDOM_DEAL_ID, 'Random Deal'),
            gwent.messaging.choice.Message.from_properties(
                self.CHOICE_PLAYER_DEAL_ID, 'Player Deal'),
        ]
        mfd = gwent.messaging.mfd.Message.with_choices(
            choices, clear_prompt=True)
        self.publish(gwent.game.CH_MFD_PRESENT, mfd)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)
        if choice.id == self.CHOICE_RANDOM_DEAL_ID:
            self.complete('random_deal')
        elif choice.id == self.CHOICE_PLAYER_DEAL_ID:
            self.complete('player_deal')
        else:
            self._log.error({
                'action': 'unknown_choice',
                'text': choice.text,
            })
            self.publish_main_menu()
