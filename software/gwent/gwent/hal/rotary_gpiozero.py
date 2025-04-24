"""
Rotary encoder implementation using gpiozero.
This implementation follows the same interface as the other rotary encoder implementations
but uses gpiozero instead of direct GPIO or WiringPi.
"""

import threading
import time
from typing import Optional, Callable
from gpiozero import RotaryEncoder, Button

from gwent.hal.rotary_base import AbstractRotaryEncoder, AbstractSwitch


class SimpleLogger:
    """A simple logger class for when a real logger is not available"""
    def info(self, msg):
        print(f"INFO: {msg}")
        
    def warning(self, msg):
        print(f"WARNING: {msg}")
        
    def debug(self, msg):
        pass  # Ignore debug messages


class GwentGPIOZeroRotaryEncoder(AbstractRotaryEncoder):
    """
    A class to decode mechanical rotary encoder pulses using gpiozero.
    This implementation follows the same interface as DirectGPIORotaryEncoder
    but uses gpiozero's event-based approach instead of polling.
    
    Based on the example from:
    https://gpiozero.readthedocs.io/en/v1.6.0/recipes.html#rotary-encoder
    """
    
    def __init__(self, a_pin: int, b_pin: int, callback: Optional[Callable[[int], None]] = None, log=None):
        """
        Initialize the rotary encoder.
        
        Args:
            a_pin: The pin number for the A signal (BCM pin numbering)
            b_pin: The pin number for the B signal (BCM pin numbering)
            callback: Optional callback function to be called when rotation is detected
            log: Optional logger instance
        """
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.callback = callback
        
        self.counter = 0
        self.direction = None
        self.lock = threading.Lock()
        self.available = False
        
        # Use provided logger or create a simple print wrapper
        self._log = log or SimpleLogger()
        
        # Initialize gpiozero RotaryEncoder
        try:
            # gpiozero uses BCM pin numbering
            # Set up with steps_per_revolution=20 for a typical rotary encoder
            self.encoder = RotaryEncoder(a_pin, b_pin, bounce_time=0.005)
            
            # Set up event handlers
            self.encoder.when_rotated_clockwise = self._on_clockwise
            self.encoder.when_rotated_counter_clockwise = self._on_counter_clockwise
            
            self._log.info(f"Initialized rotary encoder with pins A={a_pin}, B={b_pin}")
            self.available = True
        except Exception as e:
            self._log.warning(f"Error setting up gpiozero rotary encoder: {e}")
            raise RuntimeError(f"Failed to initialize rotary encoder gpiozero pins: {e}")
    
    def _on_clockwise(self):
        """Handler for clockwise rotation events"""
        with self.lock:
            self.counter += 1
            self.direction = 1
            if self.callback:
                self.callback(1)
    
    def _on_counter_clockwise(self):
        """Handler for counter-clockwise rotation events"""
        with self.lock:
            self.counter -= 1
            self.direction = -1
            if self.callback:
                self.callback(-1)
    
    def start(self):
        """Start the encoder monitoring"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        # No need to start anything - gpiozero handles events automatically
        self._log.info("Rotary encoder monitoring started")
    
    def stop(self):
        """Stop the encoder monitoring"""
        if not self.available:
            return
        # No need to stop anything - gpiozero handles cleanup
        self._log.info("Rotary encoder monitoring stopped")
    
    def get_counter(self):
        """Get the current counter value"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        with self.lock:
            return self.counter
    
    def get_direction(self):
        """Get the last direction of rotation"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        with self.lock:
            return self.direction
    
    def reset(self):
        """Reset the counter to 0"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        with self.lock:
            self.counter = 0
            self.direction = None
    
    def get_cycles(self):
        """Get the number of cycles since last call and reset the delta"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        with self.lock:
            direction = self.direction
            self.direction = None
            return direction if direction is not None else 0
    
    def __del__(self):
        """Clean up resources when the object is destroyed"""
        # gpiozero handles cleanup automatically
        pass

class GPIOZeroSwitch(AbstractSwitch):
    """A simple switch class using gpiozero"""
    
    def __init__(self, pin: int):
        """
        Initialize the switch.
        
        Args:
            pin: The pin number for the switch (BCM pin numbering)
        """
        self.pin = pin
        
        try:
            # gpiozero uses BCM pin numbering
            # pull_up=True means the switch should connect the pin to ground when pressed
            self.button = Button(pin, pull_up=True)
            
            print(f"Initialized switch with pin {pin}")
            self.available = True
        except Exception as e:
            print(f"Error setting up gpiozero switch: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize switch gpiozero pin: {e}")
    
    def get_state(self):
        """Get the current state of the switch (True = pressed, False = released)"""
        if not self.available:
            raise RuntimeError("Switch hardware not available")
        # Button is pulled up, so it's pressed when is_pressed is True
        return self.button.is_pressed
    
    def __del__(self):
        """Clean up resources when the object is destroyed"""
        # gpiozero handles cleanup automatically
        pass