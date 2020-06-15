import asyncio
import asyncio_mqtt

import gwent.cards
import gwent.messaging.factory
import gwent.messaging.mfd
import gwent.messaging.choice

import gwent.game
import gwent.hal.mfd


class MFD(gwent.game.Component):

    def __init__(self, loop: asyncio.AbstractEventLoop,
                 pubsub: asyncio_mqtt.Client):
        super().__init__(loop, pubsub)
        self._mfd = gwent.hal.mfd.instance(loop=loop)

    async def init(self):
        await self.subscribe(gwent.game.CH_MFD_PRESENT,
                             gwent.messaging.mfd.KIND,
                             self.process_mfd)

    async def shutdown(self):
        await self.unsubscribe(gwent.game.CH_MFD_PRESENT)

    async def process_mfd(self, mfd: gwent.messaging.mfd.Message):
        self._log.info({
            'action': 'received mfd',
            'kind': mfd.kind,
            'subkind': mfd.subkind,
            'prompt': mfd.prompt,
            'choices': mfd.choices,
        })

        choice = None
        if mfd.subkind == gwent.messaging.mfd.ERROR:
            choice = await self._mfd.present_error(mfd)
        elif mfd.subkind == gwent.messaging.mfd.PROMPT:
            choice = await self._mfd.present_prompt(mfd)
        elif mfd.subkind == gwent.messaging.mfd.CHOICES:
            choice = await self._mfd.present_choices(mfd)
        else:
            self._log._error(f'Unhandled subkind {mfd.subkind}')

        if choice:
            await self.publish(gwent.game.CH_MFD_CHOICE, choice)
