"""
Rotary encoder implementation using gpiozero.
This implementation follows the same interface as the other rotary encoder implementations
but uses gpiozero instead of direct GPIO or WiringPi.
"""

import threading
import time
from typing import Optional, Callable
from gpiozero import RotaryEncoder as GPIOZeroRotaryEncoder, Button

from gwent.hal.rotary_base import AbstractRotaryEncoder, AbstractSwitch


class SimpleLogger:
    """A simple logger class for when a real logger is not available"""
    def info(self, msg):
        print(f"INFO: {msg}")
        
    def warning(self, msg):
        print(f"WARNING: {msg}")
        
    def debug(self, msg):
        pass  # Ignore debug messages


class GPIOZeroRotaryEncoder(AbstractRotaryEncoder):
    """
    A class to decode mechanical rotary encoder pulses using gpiozero.
    This implementation follows the same interface as DirectGPIORotaryEncoder
    but uses gpiozero instead of RPi.GPIO.
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
        self.running = False
        self.poll_thread = None
        
        # Use provided logger or create a simple print wrapper
        self._log = log or SimpleLogger()
        
        # Initialize gpiozero RotaryEncoder
        try:
            # gpiozero uses BCM pin numbering
            self.encoder = GPIOZeroRotaryEncoder(a_pin, b_pin, wrap=False)
            self._log.info(f"Initialized rotary encoder with pins A={a_pin}, B={b_pin}")
            self.available = True
        except Exception as e:
            self._log.warning(f"Error setting up gpiozero rotary encoder: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize rotary encoder gpiozero pins: {e}")
    
    def start(self):
        """Start the encoder monitoring"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        
        self.running = True
        
        # Start a thread to poll the encoder
        self.poll_thread = threading.Thread(target=self._poll_encoder, daemon=True)
        self.poll_thread.start()
    
    def stop(self):
        """Stop the encoder monitoring"""
        self.running = False
        if self.poll_thread:
            self.poll_thread.join(timeout=1.0)
    
    def _poll_encoder(self):
        """Poll the encoder for changes"""
        try:
            last_value = self.encoder.value
            
            while self.running:
                current_value = self.encoder.value
                
                if current_value != last_value:
                    # Calculate direction
                    direction = 1 if current_value > last_value else -1
                    
                    with self.lock:
                        self.counter += direction
                        self.direction = direction
                        
                        if self.callback:
                            self.callback(direction)
                    
                    last_value = current_value
                
                time.sleep(0.001)  # 1ms polling interval
                
        except Exception as e:
            self._log.warning(f"Error in polling gpiozero encoder: {e}")
            self.running = False
    
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
        # Only stop if we're not in the current thread
        # This avoids the "cannot join current thread" error
        import threading
        if self.poll_thread and self.poll_thread != threading.current_thread():
            self.stop()


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