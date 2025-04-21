import threading

class SimpleLogger:
    """A simple logger class for when a real logger is not available"""
    def info(self, msg):
        print(f"INFO: {msg}")
        
    def warning(self, msg):
        print(f"WARNING: {msg}")
        
    def debug(self, msg):
        pass  # Ignore debug messages


class DirectGPIORotaryEncoder:
    """
    A class to decode mechanical rotary encoder pulses using RPi.GPIO directly.
    Adapted from various sources to work without external libraries.
    """
    
    def __init__(self, a_pin, b_pin, callback=None, log=None):
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.callback = callback
        
        self.last_state = None
        self.counter = 0
        self.direction = None
        self.lock = threading.Lock()
        
        # Use provided logger or create a simple print wrapper
        self._log = log or SimpleLogger()
        
        # Import GPIO here to avoid import errors when running on non-Raspberry Pi
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            
            # Check if GPIO mode is already set and use that mode
            # This avoids conflicts with other libraries that might have set the mode
            try:
                mode = self.GPIO.getmode()
                if mode is None:
                    self.GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering if not set
                    self._log.info("Setting GPIO mode to BCM")
                else:
                    self._log.info(f"Using existing GPIO mode: {mode}")
                
                # Convert pin numbers if needed
                a_pin = self.a_pin
                b_pin = self.b_pin
                if mode == GPIO.BOARD:
                    # Convert BCM pins to BOARD pins if needed
                    # This is a simplified mapping - you may need to adjust for your specific Pi model
                    bcm_to_board = {
                        17: 11,  # GPIO17 -> Pin 11
                        23: 16,  # GPIO23 -> Pin 16
                        24: 18,  # GPIO24 -> Pin 18
                        25: 22,  # GPIO25 -> Pin 22
                        27: 13,  # GPIO27 -> Pin 13
                    }
                    a_pin = bcm_to_board.get(self.a_pin, self.a_pin)
                    b_pin = bcm_to_board.get(self.b_pin, self.b_pin)
                
                self.GPIO.setup(a_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.GPIO.setup(b_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.available = True
            except Exception as e:
                self._log.warning(f"Error setting up GPIO pins: {e}")
                raise RuntimeError(f"Failed to initialize rotary encoder GPIO pins: {e}")
        except (ImportError, RuntimeError) as e:
            self._log.warning(f"Error importing RPi.GPIO: {e}")
            raise RuntimeError(f"RPi.GPIO module not available: {e}")
            
    def start(self):
        """Start the encoder monitoring"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
            
        self.last_state = self._read_state()
        
        # Add event detection
        self.GPIO.add_event_detect(self.a_pin, self.GPIO.BOTH, callback=self._encoder_callback)
        self.GPIO.add_event_detect(self.b_pin, self.GPIO.BOTH, callback=self._encoder_callback)
    
    def _read_state(self):
        """Read the current state of both pins"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        return (self.GPIO.input(self.a_pin) << 1) | self.GPIO.input(self.b_pin)
    
    def _encoder_callback(self, channel):
        """Callback for GPIO event detection"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
            
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


class DirectGPIOSwitch:
    """A simple switch class using RPi.GPIO directly"""
    
    def __init__(self, pin):
        self.pin = pin
        self.last_state = None
        
        # Import GPIO here to avoid import errors when running on non-Raspberry Pi
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            
            # Check if GPIO mode is already set and use that mode
            try:
                mode = self.GPIO.getmode()
                if mode is None:
                    self.GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering if not set
                else:
                    # Use existing mode
                    pass
                
                # Convert pin number if needed
                pin = self.pin
                if mode == GPIO.BOARD:
                    # Convert BCM pins to BOARD pins if needed
                    bcm_to_board = {
                        22: 15,  # GPIO22 -> Pin 15
                        25: 22,  # GPIO25 -> Pin 22
                    }
                    pin = bcm_to_board.get(self.pin, self.pin)
                
                self.GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.available = True
            except Exception as e:
                print(f"Error setting up GPIO pin for switch: {e}")
                raise RuntimeError(f"Failed to initialize switch GPIO pin: {e}")
        except (ImportError, RuntimeError) as e:
            raise RuntimeError(f"RPi.GPIO module not available: {e}")
    
    def get_state(self):
        """Get the current state of the switch (True = pressed, False = released)"""
        if not self.available:
            raise RuntimeError("Switch hardware not available")
        # Switch is pulled up, so it's LOW when pressed
        return not self.GPIO.input(self.pin)