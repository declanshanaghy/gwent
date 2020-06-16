import gwent.cards
import gwent.messaging.factory
import gwent.messaging.mfd
import gwent.messaging.choice

import gwent.game
import gwent.hal.mfd


class MFD(gwent.game.PubSubComponent):
    _task_chooser = None

    async def init(self):
        self._mfd = gwent.hal.mfd.instance(self._loop)
        await self.subscribe(gwent.game.CH_MFD_PRESENT,
                             gwent.messaging.mfd.KIND,
                             self.process_mfd)

    async def shutdown(self):
        await self.unsubscribe(gwent.game.CH_MFD_PRESENT)

    async def cancel_chooser(self):
        if (self._task_chooser is not None and
                not self._task_chooser.done()):
            self._log.debug("Previous chooser being canceled")
            self._task_chooser.cancel()

    async def process_mfd(self, mfd: gwent.messaging.mfd.Message):
        self._log.info({
            'action': 'received mfd',
            'kind': mfd.kind,
            'subkind': mfd.subkind,
            'body': mfd.body,
        })
        await self.cancel_chooser()

        async def receive_choice(mfd_method):
            choice = await mfd_method(mfd)
            if choice:
                await self.publish(gwent.game.CH_MFD_CHOOSE, choice)

        if mfd.subkind == gwent.messaging.mfd.ERROR:
            self._task_chooser = self._loop.create_task(
                receive_choice(self._mfd.present_error))
        elif mfd.subkind == gwent.messaging.mfd.PROMPT:
            self._task_chooser = self._loop.create_task(
                receive_choice(self._mfd.present_prompt))
        elif mfd.subkind == gwent.messaging.mfd.CHOICES:
            self._task_chooser = self._loop.create_task(
                receive_choice(self._mfd.present_choices))
        else:
            self._log._error(f'Unhandled subkind {mfd.subkind}')

