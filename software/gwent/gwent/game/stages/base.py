from typing import Callable

import gwent.game
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.sfx


class GameStage(gwent.game.PubSubComponent):
    complete = None
    cancel = None

    def init(self):
        super().init()
        self._awaiting = None
        self._deferred_action = None
        # Subscribe once at init — safe because init runs before the MQTT loop
        self.subscribe(gwent.game.CH_SFX_COMPLETE,
                      gwent.messaging.sfx.KIND,
                      self._on_announcement_complete)

    def activate(self, complete: Callable, cancel: Callable):
        self._log.debug(f"activate ")
        self.complete = complete
        self.cancel = cancel
        self._awaiting = None
        self._deferred_action = None
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

    def _publish_prompt_then(self, prompt, action, ok=False, cancel=False,
                             clear_choices=True, ok_text=None):
        """Publish a prompt and defer an action until the announcement finishes."""
        self._deferred_action = action
        self._awaiting = 'announcement'
        self.publish_prompt(prompt, ok=ok, cancel=cancel,
                           clear_choices=clear_choices, ok_text=ok_text)

    def _on_announcement_complete(self, msg):
        """Called when an announcement finishes playing."""
        if self._awaiting == 'announcement' and self._deferred_action:
            action = self._deferred_action
            self._deferred_action = None
            self._awaiting = None
            action()

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
