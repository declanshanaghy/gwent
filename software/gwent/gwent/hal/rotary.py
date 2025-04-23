import asyncio
import time
from typing import Any, Callable, List, Optional, Tuple

import gwent.hal.mfdi
import gwent.game
import gwent.messaging.choice
from gwent.hal.rotary_gpio import DirectGPIORotaryEncoder, DirectGPIOSwitch


class RotaryChooser(gwent.hal.mfdi.Chooser):
    def __init__(self, loop: asyncio.AbstractEventLoop,
                 log_verbose: bool = False):
        super().__init__(loop, log_verbose=log_verbose)
        self.rotary = RotaryEncoder(log_verbose=log_verbose)

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


class RotaryEncoder(gwent.game.BaseComponent):
    """
    Rotary encoder implementation using direct GPIO access.
    This class wraps the DirectGPIORotaryEncoder to provide a higher-level interface
    for use in the game system.
    """
    # BCM pin numbers (not Wiring pin numbers)
    A_PIN = 17  # GPIO17
    B_PIN = 22  # GPIO22
    SW_PIN = 27  # GPIO27

    _encoder = None
    _sw = None
    _counter = 0
    _delta = 0
    _sw_state = None
    _sw_changed = False

    def start(self):
        if self._encoder is None:
            self._log.info(f"Initializing rotary encoder with pins A={self.A_PIN}, B={self.B_PIN}, SW={self.SW_PIN}")
            self._encoder = DirectGPIORotaryEncoder(self.A_PIN, self.B_PIN, log=self._log)
            self._encoder.start()
            
            self._sw = DirectGPIOSwitch(self.SW_PIN)
            self._log.info("Direct GPIO rotary encoder initialized successfully")

        self.reset()

    def reset(self):
        self._counter = 0
        self._delta = 0
        if self._encoder:
            self._encoder.reset()
        if self._sw:
            self._sw_state = self._sw.get_state()

    def loop(self) -> (int, int, bool, bool):
        loop_start = time.time()
        should_log = self.should_log()

        self._delta = self._encoder.get_cycles() if self._encoder else 0
        if self._delta != 0:
            self._counter += self._delta
            self._log.debug(f'count is {self._counter}')

        state = self._sw.get_state() if self._sw else False
        self._sw_changed = state != self._sw_state
        if self._sw_changed:
            self._log.debug(f'switch changed to {state}')
            self._sw_state = state

        if self._delta != 0 or self._sw_changed:
            self._log.debug({
                'action': 'loop',
                'delta': self._delta,
                'counter': self._counter,
                'sw_changed': self._sw_changed,
                'sw_state': self._sw_state,
            })

        if should_log:
            self.log_time('loop', loop_start)
        return self._delta, self._counter, self._sw_changed, self._sw_state


# No mocks in production code as per development guidelines
