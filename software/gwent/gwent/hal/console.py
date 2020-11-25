import asyncio
import aioconsole
from typing import Any, Callable, List

import gwent.game
import gwent.hal
import gwent.hal.rotary
import gwent.hal.mfdi
import gwent.messaging.base

import gwent.messaging.mfd
import gwent.messaging.choice


class ConsoleChooser(gwent.hal.mfdi.Chooser):
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


class ConsolePresenter(gwent.hal.mfdi.Presenter):
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

