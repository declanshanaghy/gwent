import asyncio
import aioconsole
from typing import Callable, Any

import gwent.hal
import gwent.messaging.base

import gwent.messaging.mfd.mfd
import gwent.messaging.mfd.choice


def instance(loop: asyncio.AbstractEventLoop):
    if gwent.hal.REAL:
        return _MFDReal(loop=loop)
    else:
        return _MFDFake(loop=loop)


class _MFDFake(gwent.hal.Component):
    _task_await_choice = None

    async def present(self,
                      receiver:Callable[[gwent.messaging.mfd.choice.Message],Any],
                      mfd: gwent.messaging.mfd.mfd.Message):
        if self._task_await_choice is not None and not self._task_await_choice.done():
            self._task_await_choice.cancel()
            await aioconsole.aprint("Previous selections being replaced")

        self._task_await_choice = self._loop.create_task(
            self.await_choice(receiver, mfd))

    async def await_choice(
            self, receiver:Callable[[gwent.messaging.mfd.choice.Message],Any],
            mfd: gwent.messaging.mfd.mfd.Message):
        for choice in mfd.choice_iter():
            await aioconsole.aprint(f'{choice.id}: {choice.text}')

        id = None
        while id is None:
            id = await aioconsole.ainput("Enter choice: ")
            if not mfd.is_valid_choice(id):
                await aioconsole.aprint(
                    f'{id} is not a valid choice, please enter one of '
                    f'{[id for id in mfd.choice_id_iter()]}')
                id = None

            for choice in mfd.choice_iter():
                if choice.id == id:
                    self._log.info({
                        'action': 'valid choice',
                        'id': choice.id,
                        'text': choice.text
                    })
                    await receiver(choice)


class _MFDReal(_MFDFake):
    async def present(self,
                      receiver:Callable[[gwent.messaging.mfd.choice.Message],Any],
                      mfd: gwent.messaging.mfd.mfd.Message):
        self._log.info({
            'action': 'present',
            'choices': mfd.choices,
        })
