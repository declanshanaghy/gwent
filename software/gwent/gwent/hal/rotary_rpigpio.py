import threading
import time
import asyncio
import RPi.GPIO as GPIO
from gwent.hal.rotary_base import AbstractRotaryEncoder, AbstractSwitch

class SimpleLogger:
    """A simple logger class for when a real logger is not available"""
    def info(self, msg):
        print(f"INFO: {msg}")
        
    def warning(self, msg):
        print(f"WARNING: {msg}")
        
    def debug(self, msg):
        pass  # Ignore debug messages


class DirectGPIORotaryEncoder(AbstractRotaryEncoder):
    """
    A class to decode mechanical rotary encoder pulses using RPi.GPIO.
    Implements the AbstractRotaryEncoder interface.
    """
    
    # Pin modes
    IN = GPIO.IN
    OUT = GPIO.OUT
    
    # Pull up/down
    PUD_UP = GPIO.PUD_UP
    PUD_DOWN = GPIO.PUD_DOWN
    
    # Edge detection
    RISING = GPIO.RISING
    FALLING = GPIO.FALLING
    BOTH = GPIO.BOTH
    
    def __init__(self, a_pin, b_pin, callback=None, log=None):
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
        
        # Initialize GPIO
        try:
            # Set GPIO mode to BCM (Broadcom SOC channel numbering)
            GPIO.setmode(GPIO.BCM)
            
            # Set up the pins as inputs with pull-up resistors
            GPIO.setup(self.a_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.b_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            self._log.info(f"Initialized rotary encoder with pins A={self.a_pin}, B={self.b_pin}")
            self.available = True
        except Exception as e:
            self._log.warning(f"Error setting up GPIO pins: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize rotary encoder GPIO pins: {e}")
    
    def start(self):
        """Start the encoder monitoring"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        
        self.last_state = self._read_state()
        self.running = True
        
        # Start a thread to poll the GPIO pins
        self.poll_thread = threading.Thread(target=self._poll_pins, daemon=True)
        self.poll_thread.start()
    
    def stop(self):
        """Stop the encoder monitoring"""
        self.running = False
        if self.poll_thread:
            self.poll_thread.join(timeout=1.0)
    
    def _poll_pins(self):
        """Poll the GPIO pins for changes"""
        try:
            # Add event detection for both pins
            GPIO.add_event_detect(self.a_pin, GPIO.BOTH, callback=self._pin_change_callback)
            GPIO.add_event_detect(self.b_pin, GPIO.BOTH, callback=self._pin_change_callback)
            
            # Keep the thread alive while running
            while self.running:
                time.sleep(0.1)
                
            # Remove event detection when stopping
            GPIO.remove_event_detect(self.a_pin)
            GPIO.remove_event_detect(self.b_pin)
        except Exception as e:
            self._log.warning(f"Error in polling GPIO pins: {e}")
            self.running = False
    
    def _pin_change_callback(self, channel):
        """Callback function for GPIO event detection"""
        if not self.running:
            return
            
        # Process the state change
        current_state = self._read_state()
        self._process_state_change(current_state)
    
    def _read_state(self):
        """Read the current state of both pins"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        return (GPIO.input(self.a_pin) << 1) | GPIO.input(self.b_pin)
    
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
        
        # No need to clean up GPIO here as it will be done in DirectGPIOSwitch.__del__
        # or by the application


class DirectGPIOSwitch(AbstractSwitch):
    """A simple switch class using RPi.GPIO that implements the AbstractSwitch interface"""
    
    def __init__(self, pin):
        self.pin = pin
        self.last_state = None
        
        try:
            # Set GPIO mode to BCM (Broadcom SOC channel numbering)
            # This is safe to call multiple times as RPi.GPIO will only set the mode if it hasn't been set already
            GPIO.setmode(GPIO.BCM)
            
            # Set up the pin as an input with a pull-up resistor
            # This means the switch should connect the pin to ground when pressed
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            print(f"Initialized switch with pin {pin}")
            self.available = True
        except Exception as e:
            print(f"Error setting up GPIO pin for switch: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize switch GPIO pin: {e}")
    
    def get_state(self):
        """Get the current state of the switch (True = pressed, False = released)"""
        if not self.available:
            raise RuntimeError("Switch hardware not available")
        # Switch is pulled up, so it's LOW when pressed
        return not bool(GPIO.input(self.pin))
    
    def __del__(self):
        """Clean up resources when the object is destroyed"""
        try:
            # Clean up GPIO resources
            GPIO.cleanup([self.pin])
        except:
            pass