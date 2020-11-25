from typing import Callable

import gwent.game
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice


class GameStage(gwent.game.PubSubComponent):
    complete = None
    cancel = None

    async def activate(self, complete: Callable, cancel: Callable):
        self.complete = complete
        self.cancel = cancel
        await self.publish_game_stage(active=True)

    async def deactivate(self):
        await self.publish_game_stage(active=False)

    async def publish_game_stage(self, active: bool):
        ctrl = gwent.messaging.ctrl.Message.with_stage(
            self.stage, active=active)
        await self.publish(gwent.game.CH_CTRL, ctrl)

    @property
    def stage(self):
        raise NotImplementedError(f'{self.__class__.__name__} must implement '
                                  f'stage')

    async def process_card(self, card: gwent.messaging.card.Message):
        self._log.debug({
            'action': 'received card',
            'kind': card.kind,
            'faction': card.faction,
            'full_name': card.full_name,
            'rfid': card.rfid,
        })

    async def process_choice(self, choice: gwent.messaging.choice.Message):
        self._log.debug({
            'action': 'received choice',
            'id': choice.id,
            'text': choice.text,
        })
