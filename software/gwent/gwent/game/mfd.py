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

    async def init(self):
        await self.subscribe(gwent.game.CH_MFD_PRESENT,
                             gwent.messaging.mfd.mfd.KIND,
                             self.process_mfd)

    async def shutdown(self):
        await self.unsubscribe(gwent.game.CH_MFD_PRESENT)

    async def process_mfd(self, mfd: gwent.messaging.mfd.mfd.Message):
        self._log.info({
            'action': 'received message',
            'kind': mfd.kind,
            'subkind': mfd.subkind,
            'prompt': mfd.prompt,
            'choices': mfd.choices,
        })

        if mfd.subkind == gwent.messaging.mfd.mfd.ERROR:
            await self._mfd.present_error(mfd)
        elif mfd.subkind == gwent.messaging.mfd.mfd.PROMPT:
          await self._mfd.present_prompt(mfd)
        elif mfd.subkind == gwent.messaging.mfd.mfd.CHOICES:
            await self._mfd.present_choices(self.receive_choice, mfd)
        else:
            self._log.error(f'Unhandled subkind {mfd.subkind}')

    async def receive_choice(self, choice: gwent.messaging.mfd.choice.Message):
        await self.publish(gwent.game.CH_MFD_CHOICE, choice)
