import time
import threading
from typing import Any, Callable, List, Optional, Tuple

import gwent.hal.mfdi
import gwent.game
import gwent.messaging.choice
from gwent.hal.rotary_rpigpio import DirectGPIORotaryEncoder, DirectGPIOSwitch
from gwent.hal.rotary_gpiozero import GwentGPIOZeroRotaryEncoder, GPIOZeroSwitch
from enum import Enum, auto

class RotaryImplementation(Enum):
    """Enum to specify which rotary encoder implementation to use"""
    DIRECT_GPIO = auto()
    GPIOZERO = auto()


class RotaryChooser(gwent.hal.mfdi.Chooser):
    def __init__(self, implementation=RotaryImplementation.DIRECT_GPIO,
                log_verbose: bool = False):
        """
        Initialize the rotary chooser.
        
        Args:
            implementation: Which rotary encoder implementation to use
            log_verbose: Whether to enable verbose logging
        """
        super().__init__(log_verbose=log_verbose)
        self.rotary = RotaryEncoder(implementation=implementation, log_verbose=log_verbose)
        self._stop_event = threading.Event()
        self._choice = None
        self._choices = None
        self._select_callback = None

    def choose(self, choices: List[gwent.messaging.choice.Message],
                    selected_idx: int,
                    select: Callable[
                        [int, gwent.messaging.choice.Message], Any]) -> \
            gwent.messaging.choice.Message:
        self.rotary.start()
        
        self._stop_event.clear()
        self._choices = choices
        self._select_callback = select
        
        # Start with the selected choice
        choice = choices[selected_idx]
        
        # Create a thread to monitor the rotary encoder
        monitor_thread = threading.Thread(target=self._monitor_rotary, 
                                         args=(choices, selected_idx, select))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Wait for a selection to be made
        while not self._stop_event.is_set():
            time.sleep(gwent.game.DEFAULT_YIELD_TIME)
            
        monitor_thread.join(timeout=1.0)
        return self._choice

    def _monitor_rotary(self, choices, selected_idx, select):
        choice = choices[selected_idx]
        self._choice = choice
        
        while not self._stop_event.is_set():
            delta, count, sw_changed, sw_state = self.rotary.loop()
            
            if delta != 0:
                idx = count % len(choices)
                choice = choices[idx]
                self._choice = choice
                self._log.debug({
                    'action': 'select',
                    'delta': delta,
                    'count': count,
                    'len(choices)': len(choices),
                    'idx': idx,
                    'choice.id': choice.id,
                    'choice.text': choice.text,
                })
                select(delta, choice)

            if sw_changed and not sw_state:  # Release click
                self._stop_event.set()
                return
                
            time.sleep(gwent.game.DEFAULT_YIELD_TIME)


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


# No mocks in production code as per development guidelines
