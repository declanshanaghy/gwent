from typing import Callable

import gwent.game
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice


class GameStage(gwent.game.PubSubComponent):
    complete = None
    cancel = None

    def activate(self, complete: Callable, cancel: Callable):
        self._log.debug(f"activate ")
        self.complete = complete
        self.cancel = cancel
        self.publish_game_stage(active=True)

    def deactivate(self):
        self.publish_game_stage(active=False)

    def publish_game_stage(self, active: bool):
        ctrl = gwent.messaging.ctrl.Message.with_stage(
            self.stage, active=active)
        self.publish(gwent.game.CH_CTRL, ctrl)

    @property
    def stage(self):
        raise NotImplementedError(f'{self.__class__.__name__} must implement '
                                 f'stage')

    def process_card(self, card: gwent.messaging.card.Message):
        self._log.debug({
            'action': 'received card',
            'kind': card.kind,
            'faction': card.faction,
            'full_name': card.full_name,
            'rfid': card.rfid,
        })

    def process_choice(self, choice: gwent.messaging.choice.Message):
        self._log.info({
            'action': 'process_choice',
            'id': choice.id,
            'text': choice.text,
        })
