import asyncio
import aioconsole
import collections
import logging
from typing import List

import gwent.game
import gwent.hal
import gwent.messaging.base

import gwent.messaging.mfd
import gwent.messaging.choice


def instance(loop: asyncio.AbstractEventLoop):
    if gwent.hal.REAL:
        raise NotImplementedError('Real mode not implemented')
    else:
        presenter = ConsolePresenter()
        chooser = ConsoleChooser()

    return _MFD(presenter, chooser, loop=loop)


class IPresenter(object):
    # Error properties
    _display_error = False
    _error = ''

    # Prompt properties
    _prompt = ''
    _ok = None
    _cancel = None

    # Choice properties
    _choices = collections.OrderedDict()

    def clear_choices(self):
        self._choices = collections.OrderedDict()

    def clear_prompt(self):
        self._prompt = None
        self._ok = None
        self._cancel = None

    @property
    def all_choices(self) -> List[gwent.messaging.choice.Message]:
        c = self.choices
        if self._ok:
            c.extend([self._ok])
        if self._cancel:
            c.extend([self._cancel])
        return c

    @property
    def choices(self) -> List[gwent.messaging.choice.Message]:
        return [c for c in self._choices.values()]

    @choices.setter
    def choices(self, choices: List[gwent.messaging.choice.Message]):
        self.clear_choices()
        for choice in choices:
            self._choices[choice.id] = choice

    @property
    def ok(self) -> gwent.messaging.choice.Message:
        return self._ok

    @ok.setter
    def ok(self, ok: gwent.messaging.choice.Message):
        self._ok = ok

    @property
    def cancel(self) -> gwent.messaging.choice.Message:
        return self._cancel

    @cancel.setter
    def cancel(self, cancel: gwent.messaging.choice.Message):
        self._cancel = cancel

    @property
    def prompt(self) -> str:
        return self._prompt

    @prompt.setter
    def prompt(self, prompt: str):
        self._prompt = prompt

    @property
    def error(self) -> str:
        return self._error

    @error.setter
    def error(self, error: str):
        self._error = error

    def display_error(self):
        self._display_error = True

    def display_prompt(self):
        self._display_error = False

    async def redraw(self):
        pass


class IChooser(object):
    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)

    async def choose(self, choices: List[gwent.messaging.choice.Message]) -> \
            gwent.messaging.choice.Message:
        raise NotImplementedError(f'{self.__class__.__name__} must implement '
                                  f'await_choice')


class _MFD(gwent.hal.Component):

    def __init__(self, choice_presenter: IPresenter, chooser: IChooser,
                 loop: asyncio.AbstractEventLoop = None):
        super().__init__(loop=loop)
        self._presenter = choice_presenter
        self._chooser = chooser

    async def present_error(self, mfd: gwent.messaging.mfd.Message,
                            delay: int = gwent.game.DEFAULT_ERROR_TIME):
        self._presenter.error = mfd.error
        self._presenter.display_error()
        await self._presenter.redraw()

        if self._presenter.prompt:
            await asyncio.sleep(delay)
            self._presenter.display_prompt()
            await self._presenter.redraw()

        return await self._chooser.choose(self._presenter.all_choices)

    async def present_prompt(self, mfd: gwent.messaging.mfd.Message):
        self._presenter.prompt = mfd.prompt
        self._presenter.display_prompt()

        if mfd.clear_choices:
            self._presenter.clear_choices()

        if mfd.has_ok:
            if mfd.ok:
                ok = gwent.messaging.choice.Message.new_ok()
            else:
                ok = None
            self._presenter.ok = ok

        if mfd.has_cancel:
            if mfd.cancel:
                cancel = gwent.messaging.choice.Message.new_cancel()
            else:
                cancel = None
            self._presenter.cancel = cancel

        await self._presenter.redraw()
        return await self._chooser.choose(self._presenter.all_choices)

    async def present_choices(self, mfd: gwent.messaging.mfd.Message):
        if mfd.clear_prompt:
            self._presenter.clear_prompt()

        self._presenter.clear_choices()
        self._presenter.choices = [gwent.messaging.choice.Message.from_dict(c)
                                   for c in mfd.choices]

        await self._presenter.redraw()
        return await self._chooser.choose(self._presenter.all_choices)


class ConsoleChooser(IChooser):
    async def choose(self, choices: List[gwent.messaging.choice.Message]) -> \
            gwent.messaging.choice.Message:
        while True:
            cid = await aioconsole.ainput("Enter choice: ")
            for choice in choices:
                if cid == choice.id:
                    self._log.info(f'{cid} has been chosen')
                    return choice
            self._log.error(f"'{cid}' is not a valid choice")


class ConsolePresenter(IPresenter):
    async def redraw(self):
        if self._display_error:
            await aioconsole.aprint(self._error)
        else:
            if self._prompt:
                await aioconsole.aprint(self._prompt)

            for cid, choice in self._choices.items():
                await aioconsole.aprint(f'{cid}:\t{choice.text}')
            if self._ok is not None:
                await aioconsole.aprint(f'{self._ok.id}:\t{self._ok.text}')
            if self._cancel is not None:
                await aioconsole.aprint(
                    f'{self._cancel.id}:\t{self._cancel.text}')
