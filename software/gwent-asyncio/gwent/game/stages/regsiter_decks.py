import collections
from typing import Callable

import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice


class RegisterDecks(gwent.game.stages.base.GameStage):
    _decks: dict = None

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_REGISTER_DECKS

    async def activate(self, complete: Callable, cancel: Callable):
        await super().activate(complete, cancel)
        self._decks = collections.OrderedDict()
        await self.publish_start_prompt()

    async def publish_start_prompt(self):
        await self.publish_prompt("Players, Register your decks",
                                  ok=True, cancel=True, clear_choices=True)

    async def process_choice(self, choice: gwent.messaging.choice.Message):
        await super().process_choice(choice)
        self.complete()

    async def process_card(self, card: gwent.messaging.card.Message):
        await super().process_card(card)
        self.complete()
