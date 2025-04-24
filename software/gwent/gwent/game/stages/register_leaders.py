import collections
from typing import Callable

import gwent.game.stages.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice


class RegisterLeaders(gwent.game.stages.base.GameStage):
    _leaders = None

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_REGISTER_LEADERS

    def activate(self, complete: Callable, cancel: Callable):
        super().activate(complete, cancel)
        self._leaders = collections.OrderedDict()
        self.publish_start_prompt()

    def publish_start_prompt(self):
        self.publish_prompt("Players, Register your leaders",
            ok=True, cancel=True, clear_choices=True)

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

        if choice.id == gwent.messaging.choice.OK_ID:
            if len(self._leaders) < 2:
                self.publish_error('2 Leaders are not registered yet!')
            else:
                leaders = [l for l in self._leaders.values()]
                self.complete(leaders[0], leaders[1])
        elif choice.id == gwent.messaging.choice.CANCEL_ID:
            self.cancel()

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)

        if not card.is_leader:
            self.publish_error(f'{card.name} is not a leader')
            return

        if card.faction in self._leaders:
            self._leaders[card.faction] = card
            self.publish_prompt(
                f'Replaced {card.faction} leader: {card.name}')
            return

        if len(self._leaders.keys()) < 2:
            self._leaders[card.faction] = card
            self.publish_prompt(
                f'Player {len(self._leaders)} new leader: {card.name}')
            return
        else:
            self.publish_error(
                f'{card.faction} is not in this game')
