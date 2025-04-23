import threading
import time
import wiringpi
from typing import Optional, Callable

from gwent.hal.rotary_base import AbstractRotaryEncoder, AbstractSwitch


class SimpleLogger:
    """A simple logger class for when a real logger is not available"""
    def info(self, msg):
        print(f"INFO: {msg}")
        
    def warning(self, msg):
        print(f"WARNING: {msg}")
        
    def debug(self, msg):
        pass  # Ignore debug messages


class WiringPiRotaryEncoder(AbstractRotaryEncoder):
    """
    A class to decode mechanical rotary encoder pulses using WiringPi.
    This implementation follows the same interface as DirectGPIORotaryEncoder
    but uses WiringPi instead of RPi.GPIO.
    """
    
    # Pin modes
    IN = 0  # WiringPi INPUT
    OUT = 1  # WiringPi OUTPUT
    
    # Pull up/down
    PUD_UP = 2  # WiringPi PUD_UP
    PUD_DOWN = 1  # WiringPi PUD_DOWN
    
    def __init__(self, a_pin: int, b_pin: int, callback: Optional[Callable[[int], None]] = None, log=None):
        """
        Initialize the rotary encoder.
        
        Args:
            a_pin: The pin number for the A signal (WiringPi pin numbering)
            b_pin: The pin number for the B signal (WiringPi pin numbering)
            callback: Optional callback function to be called when rotation is detected
            log: Optional logger instance
        """
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.callback = callback
        
        self.last_state = None
        self.counter = 0
        self.direction = None
        self.lock = threading.Lock()
        self.running = False
        self.poll_thread = None
        
        # Use provided logger or create a simple print wrapper
        self._log = log or SimpleLogger()
        
        # Initialize WiringPi
        try:
            # Setup WiringPi
            wiringpi.wiringPiSetup()
            
            # Set up the pins as inputs with pull-up resistors
            wiringpi.pinMode(self.a_pin, self.IN)
            wiringpi.pinMode(self.b_pin, self.IN)
            wiringpi.pullUpDnControl(self.a_pin, self.PUD_UP)
            wiringpi.pullUpDnControl(self.b_pin, self.PUD_UP)
            
            self._log.info(f"Initialized rotary encoder with pins A={self.a_pin}, B={self.b_pin}")
            self.available = True
        except Exception as e:
            self._log.warning(f"Error setting up WiringPi pins: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize rotary encoder WiringPi pins: {e}")
    
    def start(self):
        """Start the encoder monitoring"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        
        self.last_state = self._read_state()
        self.running = True
        
        # Start a thread to poll the WiringPi pins
        self.poll_thread = threading.Thread(target=self._poll_pins, daemon=True)
        self.poll_thread.start()
    
    def stop(self):
        """Stop the encoder monitoring"""
        self.running = False
        if self.poll_thread:
            self.poll_thread.join(timeout=1.0)
    
    def _poll_pins(self):
        """Poll the WiringPi pins for changes"""
        try:
            # WiringPi doesn't have event detection like RPi.GPIO,
            # so we need to poll the pins manually
            while self.running:
                current_state = self._read_state()
                if current_state != self.last_state:
                    self._process_state_change(current_state)
                time.sleep(0.001)  # 1ms polling interval
                
        except Exception as e:
            self._log.warning(f"Error in polling WiringPi pins: {e}")
            self.running = False
    
    def _read_state(self):
        """Read the current state of both pins"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        return (wiringpi.digitalRead(self.a_pin) << 1) | wiringpi.digitalRead(self.b_pin)
    
    def _process_state_change(self, current_state):
        """Process a state change in the rotary encoder"""
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


class WiringPiSwitch(AbstractSwitch):
    """A simple switch class using WiringPi"""
    
    def __init__(self, pin: int):
        """
        Initialize the switch.
        
        Args:
            pin: The pin number for the switch (WiringPi pin numbering)
        """
        self.pin = pin
        self.last_state = None
        
        try:
            # Setup WiringPi if not already done
            wiringpi.wiringPiSetup()
            
            # Set up the pin as an input with a pull-up resistor
            # This means the switch should connect the pin to ground when pressed
            wiringpi.pinMode(self.pin, 0)  # INPUT
            wiringpi.pullUpDnControl(self.pin, 2)  # PUD_UP
            
            print(f"Initialized switch with pin {pin}")
            self.available = True
        except Exception as e:
            print(f"Error setting up WiringPi pin for switch: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize switch WiringPi pin: {e}")
    
    def get_state(self):
        """Get the current state of the switch (True = pressed, False = released)"""
        if not self.available:
            raise RuntimeError("Switch hardware not available")
        # Switch is pulled up, so it's LOW when pressed
        return not bool(wiringpi.digitalRead(self.pin))
    
    def __del__(self):
        """Clean up resources when the object is destroyed"""
        # WiringPi doesn't have a cleanup method like RPi.GPIO
        pass