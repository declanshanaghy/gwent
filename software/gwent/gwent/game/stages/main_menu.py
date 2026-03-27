from typing import Callable

import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.mfd


class MainMenu(gwent.game.stages.base.GameStage):
    CHOICE_START_GAME_ID = '1'

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_MAIN_MENU

    def activate(self, complete: Callable, cancel: Callable):
        super().activate(complete, cancel)
        self.publish_main_menu()

    def publish_main_menu(self):
        self.publish_prompt('Main Menu', ok=False, cancel=False,
                           clear_choices=False)
        choices = [
            gwent.messaging.choice.Message.from_properties(
                self.CHOICE_START_GAME_ID, 'Start Game'),
        ]
        mfd = gwent.messaging.mfd.Message.with_choices(
            choices, clear_prompt=True)
        self.publish(gwent.game.CH_MFD_PRESENT, mfd)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)
        if choice.id == self.CHOICE_START_GAME_ID:
            self.complete('start_game')
        else:
            self._log.error({
                'action': 'unknown_choice',
                'text': choice.text,
            })
            self.publish_main_menu()
