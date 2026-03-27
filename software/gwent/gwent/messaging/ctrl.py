from typing import List, Iterable

import gwent.messaging.base
import gwent.messaging.choice

KIND = 'ctrl'

STAGE = 'stage'
ACTIVE = 'active'

STAGE_MAIN_MENU = 'MainMenu'
STAGE_REGISTER_LEADERS = 'RegisterLeaders'
STAGE_REGISTER_DECKS = 'RegisterDecks'
STAGE_DEAL_CARDS = 'DealCards'
STAGE_PLAY_ROUND = 'PlayRound'
STAGE_ROUND_END = 'RoundEnd'
STAGE_GAME_OVER = 'GameOver'


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
        return self._instance[STAGE]

    @property
    def active(self):
        return self._instance[ACTIVE]
