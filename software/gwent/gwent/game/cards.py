import asyncio

import asyncio_mqtt

import gwent.game
import gwent.hal.rfid
import gwent.hal.tts


class Reader(gwent.game.Component):

    async def init(self):
        self._rfid = gwent.hal.rfid.instance()

    async def run(self):
        while True:
            card = await self._loop.run_in_executor(None, self._rfid.read_card)

            if card is not None:
                await self.publish(gwent.game.CH_CARDS_RAW_READ, card)


