import functools
import time

import gwent.game

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
class RotaryEncoder(gwent.game.GameComponent):
    _encoder = None
    _sw = None

    async def start(self):
        if self._encoder is None:
            import gaugette.gpio
            import gaugette.rotary_encoder
            gpio = gaugette.gpio.GPIO()
            self._encoder = await self._loop.run_in_executor(
                None, functools.partial(gaugette.rotary_encoder.RotaryEncoder,
                                        gpio, A_PIN, B_PIN))
            await self._loop.run_in_executor(None, self._encoder.start)

            import gaugette.switch
            self._sw = await self._loop.run_in_executor(
                None, functools.partial(gaugette.switch.Switch, gpio, SW_PIN))

        await self.reset()

    async def reset(self):
        self._counter = 0
        self._delta = 0
        self._sw_state = await self._loop.run_in_executor(
            None, self._sw.get_state)

    async def loop(self) -> (int, int, bool, bool):
        should_log = self.should_log()

        start = time.time()
        self._delta = self._encoder.get_cycles()
        end = time.time()
        if should_log:
            self._log.debug({
                'action': 'get_cycles',
                'start': start,
                'end': end,
                'duration': end - start,
            })

        if self._delta != 0:
            self._counter += self._delta
            self._log.debug(f'count is {self._counter}')

        start = time.time()
        state = await self._loop.run_in_executor(None, self._sw.get_state)
        end = time.time()
        if should_log:
            self._log.debug({
                'action': 'get switch state',
                'start': start,
                'end': end,
                'duration': end - start,
            })

        self._sw_changed = state != self._sw_state
        if self._sw_changed:
            self._log.debug(f'switch is {state}')
            self._sw_state = state

        if self._delta != 0 or self._sw_changed:
            self._log.debug({
                'action': 'loop',
                'delta': self._delta,
                'counter': self._counter,
                'sw_changed': self._sw_changed,
                'sw_state': self._sw_state,
            })

        return self._delta, self._counter, self._sw_changed, self._sw_state
