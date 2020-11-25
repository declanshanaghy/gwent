import asyncio
import time
from typing import Any, Callable, List

import gwent.hal.mfdi
import gwent.game
import gwent.messaging.choice


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


# Not exposing these as customizable
# Pin numbers are Wiring pin numbers.
# They differ from hardware pin or GPIO ids.
# Connect your C pin of the encoder to Ground.
A_PIN = 1
B_PIN = 0
SW_PIN = 2


# References:
# https://learn.adafruit.com/pro-trinket-rotary-encoder/example-rotary-encoder-volume-control
# https://github.com/guyc/py-gaugette
class RotaryEncoder(gwent.game.BaseComponent):
    _encoder = None
    _sw = None
    _counter = 0
    _delta = 0
    _sw_state = None
    _sw_changed = False

    def start(self):
        if self._encoder is None:
            import gaugette.gpio
            import gaugette.rotary_encoder
            gpio = gaugette.gpio.GPIO()
            self._encoder = gaugette.rotary_encoder.RotaryEncoder(
                gpio, A_PIN, B_PIN)
            self._encoder.start()

            import gaugette.switch
            self._sw = gaugette.switch.Switch(gpio, SW_PIN)

        self.reset()

    def reset(self):
        self._counter = 0
        self._delta = 0
        self._sw_state = self._sw.get_state()

    def loop(self) -> (int, int, bool, bool):
        loop_start = time.time()
        should_log = self.should_log()

        self._delta = self._encoder.get_cycles()
        if self._delta != 0:
            self._counter += self._delta
            self._log.debug(f'count is {self._counter}')

        state = self._sw.get_state()
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
