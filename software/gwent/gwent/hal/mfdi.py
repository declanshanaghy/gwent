import collections
from typing import Any, Callable, List

import gwent.game
import gwent.messaging.base

import gwent.messaging.choice


class Presenter(gwent.game.BaseComponent):
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

    def redraw(self):
        pass

    @property
    def selected_idx(self):
        return self._selected_idx

    @property
    def selected(self):
        return self._selected

    def select(self, delta: int, choice: gwent.messaging.choice.Message):
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
        self.redraw()

    def is_selected(self, choice: gwent.messaging.choice.Message) -> bool:
        return self._selected is not None and self._selected.id == choice.id

    def selector_symbol(self, choice: gwent.messaging.choice.Message) -> str:
        sel = "-"
        if self.is_selected(choice):
            sel = ">"
        return sel


class Chooser(gwent.game.BaseComponent):
    def choose(self, choices: List[gwent.messaging.choice.Message],
                    selected_idx: int,
                    select: Callable[
                        [int, gwent.messaging.choice.Message], Any]) -> \
            gwent.messaging.choice.Message:
        raise NotImplementedError(f'{self.__class__.__name__} must implement '
                                 f'choose')
