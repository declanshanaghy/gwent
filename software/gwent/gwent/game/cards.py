import asyncio
import time

import gwent.cards
import gwent.game
import gwent.messaging.factory
import gwent.messaging.ctrl
import gwent.messaging.sfx

import gwent.hal.rfid

T_PAUSE_CARD_READ_SHORT = 1
T_PAUSE_CARD_READ_LONG = 3

READING_STAGES = {
    gwent.messaging.ctrl.STAGE_REGISTER_LEADERS: T_PAUSE_CARD_READ_SHORT,
    gwent.messaging.ctrl.STAGE_REGISTER_DECKS: T_PAUSE_CARD_READ_SHORT,
}


class Reader(gwent.game.PubSubComponent):
    _pause_until = None
    _pause_length = None

    async def init(self):
        self._read_enabled = False
        self._rfid = await gwent.hal.rfid.instance(self._loop)

        await self.subscribe(gwent.game.CH_CTRL,
                             gwent.messaging.ctrl.KIND,
                             self.process_ctrl)

    async def shutdown(self):
        self._read_enabled = False
        await self.unsubscribe(gwent.game.CH_CTRL)

    async def process_ctrl(self, ctrl: gwent.messaging.ctrl.Message):
        self._log.info({
            'action': 'received ctrl',
            'kind': ctrl.kind,
            'subkind': ctrl.subkind,
            'body': ctrl.body,
        })

        if ctrl.subkind == gwent.messaging.ctrl.STAGE:
            if ctrl.stage in READING_STAGES:
                self.pause_length = READING_STAGES[ctrl.stage]
                self.read_enabled = ctrl.active
                self._log.info({
                    'action': 'read_enabled',
                    'read_enabled': self._read_enabled,
                })
        else:
            self._log._error(f'Unhandled subkind {ctrl.subkind}')

    def pause_reading(self):
        self._pause_until = time.time() + self.pause_length

    def pause_complete(self):
        if self._pause_until is None:
            return True
        else:
            complete = time.time() > self._pause_until
            if complete:
                self._pause_until = None
                self._log.info('pause complete, reading unblocked')
            return complete

    @property
    def should_read(self) -> bool:
        return self.read_enabled and self.pause_complete()

    @property
    def pause_length(self) -> float:
        return self._pause_length

    @pause_length.setter
    def pause_length(self, v: float):
        self._pause_length = v

    @property
    def read_enabled(self) -> bool:
        return self._read_enabled

    @read_enabled.setter
    def read_enabled(self, v: bool):
        self._log.info({
            'action': 'set read enabled',
            'read_enabled': v,
        })
        self._read_enabled = v

    async def run(self):
        while True:
            if self.should_read:
                card = await self._loop.run_in_executor(
                    None, self._rfid.read_card)

                if card is not None:
                    await self.publish_effect(
                        gwent.messaging.sfx.EFFECT_CARD_READ)
                    await self.publish(gwent.game.CH_CARDS_RAW_READ, card)
                    self.pause_reading()

            await asyncio.sleep(gwent.game.DEFAULT_YIELD_TIME)
