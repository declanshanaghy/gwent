import asyncio
import aioredis

import gwent.messaging.cards
import gwent.messaging.factory
import gwent.messaging.mfd.mfd
import gwent.messaging.mfd.choice

import gwent.game
import gwent.hal.mfd


class MFD(gwent.game.Component):

    def __init__(self, loop: asyncio.AbstractEventLoop, redis: aioredis.Redis):
        super().__init__(loop, redis)
        self._mfd = gwent.hal.mfd.instance(loop=loop)

    async def run(self):
        await self.subscribe(self.process,
                             gwent.game.CH_MFD_PRESENT,
                             expect=[gwent.messaging.mfd.mfd.KIND,])

    async def process(self, mfd: gwent.messaging.mfd.mfd.Message):
        self._log.info({
            'action': 'received message',
            'kind': mfd.kind,
            'choices': mfd.choices,
        })

        await self._mfd.present(self.receive_choice, mfd)

    async def receive_choice(self, choice: gwent.messaging.mfd.choice.Message):
        await self.publish(gwent.game.CH_MFD_CHOICE, choice)
