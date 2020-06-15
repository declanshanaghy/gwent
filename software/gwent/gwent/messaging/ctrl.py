from typing import List, Iterable

import gwent.messaging.base
import gwent.messaging.choice

KIND = 'ctrl'

STAGE = 'stage'
ACTIVE = 'active'

STAGE_MAIN_MENU = 'MainMenu'
STAGE_REGSITER_LEADERS = 'RegisterLeaders'
STAGE_REGSITER_DECKS = 'RegisterDecks'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_stage(state: str, active: bool):
        return Message({
            STAGE: state,
            ACTIVE: active,
        }, subkind=STAGE)

    @property
    def kind(self):
        return KIND

    @property
    def stage(self):
        return self.instance[STAGE]

    @property
    def active(self):
        return self.instance[ACTIVE]
