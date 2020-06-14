import asyncio
import aioconsole
from typing import Callable, Any
import logging

import gwent.hal
import gwent.messaging.base

import gwent.messaging.mfd.mfd
import gwent.messaging.mfd.choice


def instance(loop: asyncio.AbstractEventLoop):
    if gwent.hal.REAL:
        raise NotImplementedError('Real mode not implemented')
    else:
        choice_presenter = ConsolePresenter()
        error_presenter = ConsolePresenter()
        chooser = ConsoleChooser()

    return _MFD(choice_presenter, error_presenter, chooser, loop=loop)


class IPresenter():
    lines = []

    async def clear(self):
        self.lines = []

    async def present_line(self, text: str):
        self.lines.append(text)

    async def redisplay(self):
        pass


class IChooser():
    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)

    async def choice(self, mfd: gwent.messaging.mfd.mfd.Message):
        raise NotImplementedError(f'{self.__class__.__name__} must implement '
                                  f'await_choice')


class _MFD(gwent.hal.Component):
    _task_await_choice = None

    def __init__(self, choice_presenter:IPresenter,
                 error_presenter:IPresenter, chooser: IChooser,
                 loop: asyncio.AbstractEventLoop=None):
        super().__init__(loop=loop)
        self.choice_presenter = choice_presenter
        self.error_presenter = error_presenter
        self.chooser = chooser

    async def present_error(self, mfd: gwent.messaging.mfd.mfd.Message):
        await self.error_presenter.clear()
        await self.error_presenter.present_line(mfd.error)
        await asyncio.sleep(5)
        await self.choice_presenter.redisplay()

    async def present_prompt(self, mfd: gwent.messaging.mfd.mfd.Message):
        await self.choice_presenter.clear()
        await self.error_presenter.present_line(mfd.prompt)

    async def present_choices(self, mfd: gwent.messaging.mfd.mfd.Message):
        if self._task_await_choice is not None and not self._task_await_choice.done():
            self._log.info("Previous choices being replaced")
            self._task_await_choice.cancel()

        await self.choice_presenter.clear()
        for choice in mfd.choice_iter():
            await self.choice_presenter.present_line(
                f'{choice.id}: {choice.text}')

        return await self.chooser.choice(mfd)


class ConsoleChooser(IChooser):
    async def choice(self, mfd: gwent.messaging.mfd.mfd.Message):
        while True:
            id = await aioconsole.ainput("Enter choice: ")
            for choice in mfd.choice_iter():
                if id == choice.id:
                    return choice
            self._log.error(f'{id} is not a valid choice')


class ConsolePresenter(IPresenter):
    async def redisplay(self):
        for _, line in self.lines:
            await aioconsole.aprint(line)

    async def present_line(self, text: str):
        await super().present_line(text)
        await aioconsole.aprint(text)
