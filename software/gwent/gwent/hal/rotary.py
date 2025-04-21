import asyncio
import time
from typing import Any, Callable, List
import threading

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


class DirectGPIORotaryEncoder:
    """
    A class to decode mechanical rotary encoder pulses using RPi.GPIO directly.
    Adapted from various sources to work without external libraries.
    """
    
    def __init__(self, a_pin, b_pin, callback=None):
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.callback = callback
        
        self.last_state = None
        self.counter = 0
        self.direction = None
        self.lock = threading.Lock()
        
        # Import GPIO here to avoid import errors when running on non-Raspberry Pi
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
            self.GPIO.setup(self.a_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.GPIO.setup(self.b_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.available = True
        except (ImportError, RuntimeError):
            self.available = False
            
    def start(self):
        """Start the encoder monitoring"""
        if not self.available:
            return
            
        self.last_state = self._read_state()
        
        # Add event detection
        self.GPIO.add_event_detect(self.a_pin, self.GPIO.BOTH, callback=self._encoder_callback)
        self.GPIO.add_event_detect(self.b_pin, self.GPIO.BOTH, callback=self._encoder_callback)
    
    def _read_state(self):
        """Read the current state of both pins"""
        if not self.available:
            return 0
        return (self.GPIO.input(self.a_pin) << 1) | self.GPIO.input(self.b_pin)
    
    def _encoder_callback(self, channel):
        """Callback for GPIO event detection"""
        if not self.available:
            return
            
        current_state = self._read_state()
        
        if self.last_state is None:
            self.last_state = current_state
            return
            
        # State transition table for clockwise rotation:
        # 00 -> 01 -> 11 -> 10 -> 00
        # For counter-clockwise, the sequence is reversed
        
        with self.lock:
            if current_state != self.last_state:
                # Determine direction based on state transition
                if (self.last_state == 0b00 and current_state == 0b01) or \
                   (self.last_state == 0b01 and current_state == 0b11) or \
                   (self.last_state == 0b11 and current_state == 0b10) or \
                   (self.last_state == 0b10 and current_state == 0b00):
                    self.direction = 1  # Clockwise
                    if current_state == 0b00:  # Complete rotation
                        self.counter += 1
                        if self.callback:
                            self.callback(1)
                elif (self.last_state == 0b00 and current_state == 0b10) or \
                     (self.last_state == 0b10 and current_state == 0b11) or \
                     (self.last_state == 0b11 and current_state == 0b01) or \
                     (self.last_state == 0b01 and current_state == 0b00):
                    self.direction = -1  # Counter-clockwise
                    if current_state == 0b00:  # Complete rotation
                        self.counter -= 1
                        if self.callback:
                            self.callback(-1)
                
                self.last_state = current_state
    
    def get_counter(self):
        """Get the current counter value"""
        with self.lock:
            return self.counter
    
    def get_direction(self):
        """Get the last direction of rotation"""
        with self.lock:
            return self.direction
    
    def reset(self):
        """Reset the counter to 0"""
        with self.lock:
            self.counter = 0
            self.direction = None
    
    def get_cycles(self):
        """Get the number of cycles since last call and reset the delta"""
        with self.lock:
            direction = self.direction
            self.direction = None
            return direction if direction is not None else 0


class DirectGPIOSwitch:
    """A simple switch class using RPi.GPIO directly"""
    
    def __init__(self, pin):
        self.pin = pin
        self.last_state = None
        
        # Import GPIO here to avoid import errors when running on non-Raspberry Pi
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
            self.GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.available = True
        except (ImportError, RuntimeError):
            self.available = False
    
    def get_state(self):
        """Get the current state of the switch (True = pressed, False = released)"""
        if not self.available:
            return False
        # Switch is pulled up, so it's LOW when pressed
        return not self.GPIO.input(self.pin)


class RotaryEncoder(gwent.game.BaseComponent):
    """
    Rotary encoder implementation using direct GPIO access.
    """
    # BCM pin numbers (not Wiring pin numbers)
    A_PIN = 17  # GPIO17
    B_PIN = 27  # GPIO27
    SW_PIN = 22  # GPIO22

    _encoder = None
    _sw = None
    _counter = 0
    _delta = 0
    _sw_state = None
    _sw_changed = False

    def start(self):
        if self._encoder is None:
            try:
                self._log.info(f"Initializing rotary encoder with pins A={self.A_PIN}, B={self.B_PIN}, SW={self.SW_PIN}")
                self._encoder = DirectGPIORotaryEncoder(self.A_PIN, self.B_PIN)
                self._encoder.start()
                
                self._sw = DirectGPIOSwitch(self.SW_PIN)
                self._log.info("Direct GPIO rotary encoder initialized successfully")
            except Exception as e:
                self._log.warning(f"Error initializing rotary encoder: {e}")
                self._log.info("Using mock rotary encoder implementation")
                # Create mock implementations for testing
                self._encoder = MockRotaryEncoder()
                self._sw = MockSwitch()

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


class MockRotaryEncoder:
    """Mock implementation of the rotary encoder for environments where hardware is not available"""
    def __init__(self):
        self._counter = 0
        
    def start(self):
        pass
        
    def get_cycles(self):
        # Always return 0 for no movement
        return 0
        
    def reset(self):
        self._counter = 0


class MockSwitch:
    """Mock implementation of the switch for environments where hardware is not available"""
    def __init__(self):
        self._state = False
        
    def get_state(self):
        # Always return False (not pressed)
        return False
