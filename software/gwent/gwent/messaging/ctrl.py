from typing import List, Iterable

import gwent.messaging.base
import gwent.messaging.choice

KIND = 'ctrl'

STATE = 'state'
STATE_NEWGAME = 'NewGame'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_state(state: str):
        return Message({
            STATE: state,
        }, subkind=STATE)

    @property
    def kind(self):
        return KIND

    @property
    def state(self):
        return self.instance.get(STATE)
