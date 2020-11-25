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

    async def activate(self, complete: Callable, cancel: Callable):
        await super().activate(complete, cancel)
        await self.publish_main_menu()

    async def publish_main_menu(self):
        await self.publish_prompt('Main Menu', ok=False, cancel=False,
                                  clear_choices=False)
        choices = [
            gwent.messaging.choice.Message.from_properties(
                self.CHOICE_START_GAME_ID, 'Start Game'),
        ]
        mfd = gwent.messaging.mfd.Message.with_choices(
            choices, clear_prompt=True)
        await self.publish(gwent.game.CH_MFD_PRESENT, mfd)

    async def process_choice(self, choice: gwent.messaging.choice.Message):
        await super().process_choice(choice)
        if choice.id == self.CHOICE_START_GAME_ID:
            await self.complete()
        else:
            self._log.error({
                'action': 'dummy_choice',
                'text': choice.text,
            })
            await self.publish_main_menu()
