import asyncio

import gwent.cards
import gwent.game
import gwent.messaging.factory
import gwent.messaging.ctrl

import gwent.hal.rfid
import gwent.hal.tts


class Reader(gwent.game.PubSubComponent):
    READING_STAGES = (
        gwent.messaging.ctrl.STAGE_MAIN_MENU,
        gwent.messaging.ctrl.STAGE_REGISTER_LEADERS,
        gwent.messaging.ctrl.STAGE_REGISTER_DECKS,
    )

    async def init(self):
        self._rfid = gwent.hal.rfid.instance()
        self._read_enabled = False
        await self.subscribe(gwent.game.CH_GAMESTAGE,
                             gwent.messaging.ctrl.KIND,
                             self.process_ctrl)

    async def shutdown(self):
        await self.unsubscribe(gwent.game.CH_GAMESTAGE)

    async def process_ctrl(self, ctrl: gwent.messaging.ctrl.Message):
        self._log.info({
            'action': 'received ctrl',
            'kind': ctrl.kind,
            'subkind': ctrl.subkind,
            'body': ctrl.body,
        })

        if ctrl.subkind == gwent.messaging.ctrl.STAGE:
            if ctrl.stage in self.READING_STAGES:
                self._read_enabled = ctrl.active
                self._log.info({
                    'action': 'read_enabled',
                    'read_enabled': self._read_enabled,
                })
        else:
            self._log._error(f'Unhandled subkind {ctrl.subkind}')

    async def run(self):
        while True:
            if not self._read_enabled:
                # if self.should_log():
                #     self._log.info({
                #         'action': 'read_enabled',
                #         'read_enabled': self._read_enabled,
                #     })
                await asyncio.sleep(0.1)
            else:
                card = await self._loop.run_in_executor(
                    None, self._rfid.read_card)

                if card is not None:
                    await self.publish(gwent.game.CH_CARDS_RAW_READ, card)
                    await asyncio.sleep(3)

