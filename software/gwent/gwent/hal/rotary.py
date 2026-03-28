import time
import threading
from typing import Any, Callable, List

import gwent.hal.mfdi
import gwent.game
import gwent.messaging.choice
from gwent.hal.rotary_pigpio import PiGPIORotaryEncoder, PiGPIOSwitch


class RotaryChooser(gwent.hal.mfdi.Chooser):
    def __init__(self):
        super().__init__()
        self.rotary = RotaryEncoder()
        self._stop_event = threading.Event()
        self._choice = None

    def cancel(self):
        self._stop_event.set()

    def choose(self, choices: List[gwent.messaging.choice.Message],
               selected_idx: int,
               select: Callable[[int, gwent.messaging.choice.Message], Any]) -> \
            gwent.messaging.choice.Message:

        if not choices:
            return None

        selected_idx = max(0, min(selected_idx, len(choices) - 1))
        self.rotary.start()
        self._stop_event.clear()
        self._choice = choices[selected_idx]

        monitor_thread = threading.Thread(
            target=self._monitor_rotary,
            args=(choices, selected_idx, select),
            daemon=True)
        monitor_thread.start()

        self._stop_event.wait()
        monitor_thread.join(timeout=1.0)
        return self._choice

    def _monitor_rotary(self, choices, selected_idx, select):
        self._choice = choices[selected_idx]

        # Brief delay to avoid catching tail end of previous button press
        time.sleep(0.3)

        while not self._stop_event.is_set():
            delta, count, sw_changed, sw_state = self.rotary.loop()

            if delta != 0:
                idx = count % len(choices)
                self._choice = choices[idx]
                self._log.info({
                    'action': 'select',
                    'delta': delta,
                    'idx': idx,
                    'choice': self._choice.text,
                })
                select(delta, self._choice)

            if sw_changed and not sw_state:
                self._stop_event.set()
                return

            time.sleep(0.1)


class RotaryEncoder(gwent.game.BaseComponent):
    """Rotary encoder using PiGPIO."""

    A_PIN = 17
    B_PIN = 22
    SW_PIN = 27
    DEBOUNCE_TIME = 0.05

    def __init__(self):
        super().__init__()
        self._encoder = None
        self._sw = None
        self._counter = 0
        self._delta = 0
        self._sw_state = None
        self._sw_changed = False
        self._last_sw_change_time = 0
        self._last_sw_raw_state = None

    def start(self):
        if self._encoder is None:
            self._encoder = PiGPIORotaryEncoder(self.A_PIN, self.B_PIN, log=self._log)
            self._sw = PiGPIOSwitch(self.SW_PIN)
            self._encoder.start()
        self.reset()

    def reset(self):
        self._counter = 0
        self._delta = 0
        self._last_sw_change_time = time.time()
        self._last_sw_raw_state = None
        if self._encoder:
            self._encoder.reset()
        if self._sw:
            self._sw_state = self._sw.get_state()
            self._last_sw_raw_state = self._sw_state

    def loop(self):
        self._delta = self._encoder.get_cycles()
        if self._delta != 0:
            self._counter += self._delta

        raw_state = self._sw.get_state()
        self._last_sw_raw_state = raw_state
        self._sw_changed = False

        if raw_state != self._sw_state:
            if time.time() - self._last_sw_change_time >= self.DEBOUNCE_TIME:
                self._sw_changed = True
                self._sw_state = raw_state
                self._last_sw_change_time = time.time()

        if self._delta != 0 or self._sw_changed:
            self._log.info({
                'action': 'loop',
                'delta': self._delta,
                'counter': self._counter,
                'sw_changed': self._sw_changed,
                'sw_state': self._sw_state,
            })

        return self._delta, self._counter, self._sw_changed, self._sw_state
