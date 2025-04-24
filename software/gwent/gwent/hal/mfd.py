import time
from typing import Any, Callable

import gwent.game
import gwent.hal
import gwent.hal.mfdi
import gwent.hal.rotary
import gwent.hal.console
import gwent.hal.oled_ssd1306
import gwent.messaging.base

import gwent.messaging.mfd
import gwent.messaging.choice


def instance():
    if gwent.hal.real_mode():
        # Use device=1, port=0 as seen in the working POC demo
        presenter = gwent.hal.oled_ssd1306.SSD1306Presenter(device=1, port=0)
        chooser = gwent.hal.rotary.RotaryChooser()
    else:
        presenter = gwent.hal.console.ConsolePresenter()
        chooser = gwent.hal.console.ConsoleChooser()

    return _MFD(presenter, chooser)


class _MFD(gwent.game.BaseComponent):

    def __init__(self, choice_presenter: gwent.hal.mfdi.Presenter, chooser: gwent.hal.mfdi.Chooser):
        super().__init__()
        self._presenter = choice_presenter
        self._chooser = chooser

    def present_error(
            self, mfd: gwent.messaging.mfd.Message,
            select: Callable[[int, gwent.messaging.choice.Message], Any],
            delay: int = gwent.game.DEFAULT_ERROR_TIME):
        self._log.debug({
            'action': 'present_error',
            'error': mfd.error,
        })

        self._presenter.error = mfd.error
        self._presenter.display_error()
        self._presenter.redraw()

        if self._presenter.prompt:
            time.sleep(delay)
            self._presenter.display_prompt()
            self._presenter.redraw()

        def _select(delta: int, choice: gwent.messaging.choice.Message):
            self._presenter.select(delta, choice)
            select(delta, choice)

        if len(self._presenter.all_choices) > 0:
            return self._chooser.choose(
                self._presenter.all_choices,
                self._presenter.selected_idx,
                _select)

    def present_prompt(
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
            self._presenter.select(0, all_choices[0])
        else:
            self._presenter.redraw()

        def _select(delta: int, choice: gwent.messaging.choice.Message):
            self._presenter.select(delta, choice)
            select(delta, choice)

        if len(all_choices) > 0:
            return self._chooser.choose(
                all_choices, self._presenter.selected_idx, _select)

    def present_choices(
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
            self._presenter.select(0, all_choices[0])
        else:
            self._presenter.redraw()

        def _select(delta: int, choice: gwent.messaging.choice.Message):
            self._presenter.select(delta, choice)
            select(delta, choice)

        if len(all_choices) > 0:
            return self._chooser.choose(
                all_choices, self._presenter.selected_idx, _select)
