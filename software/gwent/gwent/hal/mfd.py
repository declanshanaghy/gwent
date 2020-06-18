import asyncio
import aioconsole
import collections
from typing import Any, Callable, List

import gwent.game
import gwent.hal
import gwent.hal.rotary
import gwent.messaging.base

import gwent.messaging.mfd
import gwent.messaging.choice


async def instance(loop: asyncio.AbstractEventLoop):
    if await gwent.hal.real_mode():
        presenter = ConsolePresenter()
        chooser = RotaryChooser(loop)
        # chooser = ConsoleChooser(loop)
    else:
        presenter = ConsolePresenter()
        chooser = ConsoleChooser(loop)

    return _MFD(presenter, chooser)


class IPresenter(gwent.game.BaseComponent):
    # Error properties
    _display_error = False
    _error = ''

    # Prompt properties
    _prompt = ''
    _ok = None
    _cancel = None

    # Choice properties
    _choices = collections.OrderedDict()
    _selected = None
    _selected_idx = None

    def clear_choices(self):
        self._selected = None
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

    @property
    def selected_idx(self):
        return self._selected_idx

    @property
    def selected(self):
        return self._selected

    async def select(self, delta: int, choice: gwent.messaging.choice.Message):
        self._selected_idx = 0
        self._selected = choice
        for choice2 in self.all_choices:
            if choice.id == choice2.id:
                break
            self._selected_idx += 1

        self._log.debug({
            'action': 'select',
            'selected': self._selected.body,
            'selected_idx': self._selected_idx,
            'delta': delta,
            'id': choice.id,
            'text': choice.text,
        })
        await self.redraw()

    def is_selected(self, choice: gwent.messaging.choice.Message) -> bool:
        return self._selected is not None and self._selected.id == choice.id

    def selector_symbol(self, choice: gwent.messaging.choice.Message) -> str:
        sel = "-"
        if self.is_selected(choice):
            sel = ">"
        return sel


class IChooser(gwent.game.GameComponent):
    async def choose(self, choices: List[gwent.messaging.choice.Message],
                     selected_idx: int,
                     select: Callable[
                         [int, gwent.messaging.choice.Message], Any]) -> \
            gwent.messaging.choice.Message:
        raise NotImplementedError(f'{self.__class__.__name__} must implement '
                                  f'await_choice')


class _MFD(gwent.game.BaseComponent):

    def __init__(self, choice_presenter: IPresenter, chooser: IChooser):
        super().__init__()
        self._presenter = choice_presenter
        self._chooser = chooser

    async def present_error(
            self, mfd: gwent.messaging.mfd.Message,
            select: Callable[[int, gwent.messaging.choice.Message], Any],
            delay: int = gwent.game.DEFAULT_ERROR_TIME):
        self._log.debug({
            'action': 'present_error',
            'error': mfd.error,
        })

        self._presenter.error = mfd.error
        self._presenter.display_error()
        await self._presenter.redraw()

        if self._presenter.prompt:
            await asyncio.sleep(delay)
            self._presenter.display_prompt()
            await self._presenter.redraw()

        async def _select(delta: int, choice: gwent.messaging.choice.Message):
            await self._presenter.select(delta, choice)
            await select(delta, choice)

        if len(self._presenter.all_choices) > 0:
            return await self._chooser.choose(
                self._presenter.all_choices,
                self._presenter.selected_idx,
                _select)

    async def present_prompt(
            self, mfd: gwent.messaging.mfd.Message,
            select: Callable[[int, gwent.messaging.choice.Message], Any]):
        self._log.debug({
            'action': 'present_prompt',
            'prompt': mfd.prompt,
        })
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

        all_choices = self._presenter.all_choices
        if self._presenter.selected is None and len(all_choices) > 0:
            await self._presenter.select(0, all_choices[0])
        else:
            await self._presenter.redraw()

        async def _select(delta: int, choice: gwent.messaging.choice.Message):
            await self._presenter.select(delta, choice)
            await select(delta, choice)

        if len(all_choices) > 0:
            return await self._chooser.choose(
                all_choices, self._presenter.selected_idx, _select)

    async def present_choices(
            self, mfd: gwent.messaging.mfd.Message,
            select: Callable[[int, gwent.messaging.choice.Message], Any]):
        self._log.debug({
            'action': 'present_choices',
            'choices': mfd.choices,
        })
        if mfd.clear_prompt:
            self._presenter.clear_prompt()

        self._presenter.clear_choices()
        self._presenter.choices = [gwent.messaging.choice.Message.from_dict(c)
                                   for c in mfd.choices]

        all_choices = self._presenter.all_choices
        if self._presenter.selected is None and len(all_choices) > 0:
            await self._presenter.select(0, all_choices[0])
        else:
            await self._presenter.redraw()

        async def _select(delta: int, choice: gwent.messaging.choice.Message):
            await self._presenter.select(delta, choice)
            await select(delta, choice)

        if len(all_choices) > 0:
            return await self._chooser.choose(
                all_choices, self._presenter.selected_idx, _select)


class ConsoleChooser(IChooser):
    async def choose(self, choices: List[gwent.messaging.choice.Message],
                     selected_idx: int,
                     select: Callable[
                         [int, gwent.messaging.choice.Message], Any]) -> \
            gwent.messaging.choice.Message:
        idx = selected_idx
        while True:
            cid = await aioconsole.ainput("Enter choice: ")
            if cid == 's':
                return choices[idx]
            elif cid == 'u' or cid == 'd':
                delta = 0
                if cid == 'u':
                    delta -= 1
                if cid == 'd':
                    delta += 1
                idx += delta

                self._log.debug({
                    'action': 'set idx unbounded',
                    'delta': delta,
                    'idx': idx,
                })

                if idx < 0:
                    idx = len(choices) - 1
                    self._log.debug({
                        'action': 'idx wrapped down',
                        'idx': idx,
                    })
                elif idx >= len(choices):
                    idx = 0
                    self._log.debug({
                        'action': 'idx wrapped up',
                        'idx': idx,
                    })
                await select(delta, choices[idx])
            else:
                for choice in choices:
                    if cid == choice.id:
                        self._log.info(f'{cid} has been chosen')
                        return choice
                self._log.error(f"'{cid}' is not a valid choice")

            await asyncio.sleep(gwent.game.DEFAULT_YIELD_TIME)


class RotaryChooser(IChooser):
    def __init__(self, loop: asyncio.AbstractEventLoop,
                 log_verbose: bool = False):
        super().__init__(loop, log_verbose=log_verbose)
        self.rotary = gwent.hal.rotary.RotaryEncoder(log_verbose=log_verbose)

    async def choose(self, choices: List[gwent.messaging.choice.Message],
                     selected_idx: int,
                     select: Callable[
                         [int, gwent.messaging.choice.Message], Any]) -> \
            gwent.messaging.choice.Message:
        await self._loop.run_in_executor(None, self.rotary.start)

        choice = choices[selected_idx]
        while True:
            delta, count, sw_changed, sw_state = await self._loop.run_in_executor(
                None, self.rotary.loop)
            if delta != 0:
                idx = count % len(choices)
                choice = choices[idx]
                self._log.debug({
                    'action': 'select',
                    'delta': delta,
                    'count': count,
                    'len(choices)': len(choices),
                    'idx': idx,
                    'choice.id': choice.id,
                    'choice.text': choice.text,
                })
                await select(delta, choice)

            if sw_changed and not sw_state:  # Release click
                return choice

            await asyncio.sleep(gwent.game.DEFAULT_YIELD_TIME)


class ConsolePresenter(IPresenter):
    async def redraw(self):
        if self._display_error:
            await aioconsole.aprint(self._error)
        else:
            await aioconsole.aprint('----------------------------------')

            if self._prompt:
                await aioconsole.aprint(self._prompt)

            for cid, choice in self._choices.items():
                sel = self.selector_symbol(choice)
                await aioconsole.aprint(f'{sel} ({choice.id}):\t{choice.text}')
            if self._ok is not None:
                sel = self.selector_symbol(self._ok)
                await aioconsole.aprint(
                    f'{sel} ({self._ok.id}):\t{self._ok.text}')
            if self._cancel is not None:
                sel = self.selector_symbol(self._cancel)
                await aioconsole.aprint(
                    f'{sel} ({self._cancel.id}):\t{self._cancel.text}')
