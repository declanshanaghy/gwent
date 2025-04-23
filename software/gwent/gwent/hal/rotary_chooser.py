#!/usr/bin/env python3

import time
from enum import Enum, auto

import gwent.game
from gwent.hal.rotary_rawgpio import DirectGPIORotaryEncoder, DirectGPIOSwitch
from gwent.hal.rotary_gpiozero import GwentGPIOZeroRotaryEncoder, GPIOZeroSwitch


class RotaryImplementation(Enum):
    """Enum to specify which rotary encoder implementation to use"""
    DIRECT_GPIO = auto()
    GPIOZERO = auto()


class RotaryEncoder(gwent.game.BaseComponent):
    """
    Rotary encoder implementation.
    This class wraps the rotary encoder implementations to provide a higher-level interface
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
    
    def __init__(self, implementation=RotaryImplementation.DIRECT_GPIO, log_verbose=False):
        """
        Initialize the rotary encoder.
        
        Args:
            implementation: Which implementation to use (DirectGPIO or GPIOZero)
            log_verbose: Whether to enable verbose logging
        """
        super().__init__(log_verbose=log_verbose)
        self._implementation = implementation

    def start(self):
        if self._encoder is None:
            self._log.info(f"Initializing rotary encoder with pins A={self.A_PIN}, B={self.B_PIN}, SW={self.SW_PIN}")
            
            if self._implementation == RotaryImplementation.DIRECT_GPIO:
                self._encoder = DirectGPIORotaryEncoder(self.A_PIN, self.B_PIN, log=self._log)
                self._sw = DirectGPIOSwitch(self.SW_PIN)
                self._log.info("Direct GPIO rotary encoder initialized successfully")
            elif self._implementation == RotaryImplementation.GPIOZERO:
                self._encoder = GwentGPIOZeroRotaryEncoder(self.A_PIN, self.B_PIN, log=self._log)
                self._sw = GPIOZeroSwitch(self.SW_PIN)
                self._log.info("GPIOZero rotary encoder initialized successfully")
            else:
                raise ValueError(f"Unknown implementation: {self._implementation}")
                
            self._encoder.start()

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


# Simple test code when run directly
if __name__ == "__main__":
    # BCM pin numbers (not Wiring pin numbers)
    A_PIN = 23  # GPIO23
    B_PIN = 24  # GPIO24
    SW_PIN = 25  # GPIO25

    encoder = DirectGPIORotaryEncoder(A_PIN, B_PIN)
    encoder.start()

    sw = DirectGPIOSwitch(SW_PIN)
    last_state = sw.get_state()

    counter = 0

    try:
        print("Rotary encoder test running. Press Ctrl+C to exit.")
        while True:
            delta = encoder.get_cycles()
            if delta != 0:
                counter += delta
                print("count is %d" % counter)
            else:
                time.sleep(0.1)

            state = sw.get_state()
            if state != last_state:
                print("switch %d" % state)
                last_state = state
    except KeyboardInterrupt:
        print("\nExiting rotary encoder test...")