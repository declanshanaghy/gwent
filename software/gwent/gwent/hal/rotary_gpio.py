import threading
import os
import time
import select
import asyncio

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
    A class to decode mechanical rotary encoder pulses using direct GPIO sysfs interface.
    No dependency on RPi.GPIO or other libraries.
    """
    
    # GPIO sysfs paths
    GPIO_PATH = "/sys/class/gpio"
    
    # Pin modes
    IN = "in"
    OUT = "out"
    
    # Pull up/down resistors (for documentation, not used in sysfs)
    PUD_UP = "up"
    PUD_DOWN = "down"
    
    # Edge detection
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"
    
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
        
        try:
            # Export pins if not already exported
            self._export_pin(self.a_pin)
            self._export_pin(self.b_pin)
            
            # Set pins as inputs with pull-up resistors (note: pull-up must be handled in hardware)
            self._set_pin_direction(self.a_pin, self.IN)
            self._set_pin_direction(self.b_pin, self.IN)
            
            # Set edge detection
            self._set_pin_edge(self.a_pin, self.BOTH)
            self._set_pin_edge(self.b_pin, self.BOTH)
            
            self._log.info(f"Initialized rotary encoder with pins A={self.a_pin}, B={self.b_pin}")
            self.available = True
        except Exception as e:
            self._log.warning(f"Error setting up GPIO pins: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize rotary encoder GPIO pins: {e}")
    
    def _export_pin(self, pin):
        """Export a GPIO pin if it's not already exported"""
        if not os.path.exists(f"{self.GPIO_PATH}/gpio{pin}"):
            with open(f"{self.GPIO_PATH}/export", "w") as f:
                f.write(str(pin))
            # Wait for the pin to be exported
            timeout = 0.1
            start_time = time.time()
            while not os.path.exists(f"{self.GPIO_PATH}/gpio{pin}/direction"):
                if time.time() - start_time > timeout:
                    raise RuntimeError(f"Timeout waiting for GPIO{pin} to be exported")
                time.sleep(0.01)
    
    def _unexport_pin(self, pin):
        """Unexport a GPIO pin"""
        if os.path.exists(f"{self.GPIO_PATH}/gpio{pin}"):
            with open(f"{self.GPIO_PATH}/unexport", "w") as f:
                f.write(str(pin))
    
    def _set_pin_direction(self, pin, direction):
        """Set the direction of a GPIO pin (in/out)"""
        with open(f"{self.GPIO_PATH}/gpio{pin}/direction", "w") as f:
            f.write(direction)
    
    def _set_pin_edge(self, pin, edge):
        """Set the edge detection of a GPIO pin (rising/falling/both/none)"""
        with open(f"{self.GPIO_PATH}/gpio{pin}/edge", "w") as f:
            f.write(edge)
    
    def _read_pin(self, pin):
        """Read the value of a GPIO pin"""
        with open(f"{self.GPIO_PATH}/gpio{pin}/value", "r") as f:
            return int(f.read().strip())
    
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
        # Open the value files for both pins
        a_path = f"{self.GPIO_PATH}/gpio{self.a_pin}/value"
        b_path = f"{self.GPIO_PATH}/gpio{self.b_pin}/value"
        
        try:
            with open(a_path, "r") as a_file, open(b_path, "r") as b_file:
                # Create poll object
                poller = select.poll()
                poller.register(a_file, select.POLLPRI | select.POLLERR)
                poller.register(b_file, select.POLLPRI | select.POLLERR)
                
                # Initial read to clear any pending events
                a_file.seek(0)
                a_file.read()
                b_file.seek(0)
                b_file.read()
                
                while self.running:
                    # Wait for an event on either pin (timeout after 100ms)
                    events = poller.poll(100)
                    if events:
                        # Reread the values
                        a_file.seek(0)
                        a_file.read()
                        b_file.seek(0)
                        b_file.read()
                        
                        # Process the state change
                        current_state = self._read_state()
                        self._process_state_change(current_state)
        except Exception as e:
            self._log.warning(f"Error polling GPIO pins: {e}")
            self.running = False
    
    def _read_state(self):
        """Read the current state of both pins"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        return (self._read_pin(self.a_pin) << 1) | self._read_pin(self.b_pin)
    
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
        self.stop()
        try:
            # Unexport pins
            self._unexport_pin(self.a_pin)
            self._unexport_pin(self.b_pin)
        except:
            pass


class DirectGPIOSwitch:
    """A simple switch class using direct GPIO sysfs interface"""
    
    # GPIO sysfs paths
    GPIO_PATH = "/sys/class/gpio"
    
    # Pin modes
    IN = "in"
    OUT = "out"
    
    def __init__(self, pin):
        self.pin = pin
        self.last_state = None
        
        try:
            # Export pin if not already exported
            self._export_pin(self.pin)
            
            # Set pin as input (pull-up must be handled in hardware)
            self._set_pin_direction(self.pin, self.IN)
            
            self.available = True
        except Exception as e:
            print(f"Error setting up GPIO pin for switch: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize switch GPIO pin: {e}")
    
    def _export_pin(self, pin):
        """Export a GPIO pin if it's not already exported"""
        if not os.path.exists(f"{self.GPIO_PATH}/gpio{pin}"):
            with open(f"{self.GPIO_PATH}/export", "w") as f:
                f.write(str(pin))
            # Wait for the pin to be exported
            timeout = 0.1
            start_time = time.time()
            while not os.path.exists(f"{self.GPIO_PATH}/gpio{pin}/direction"):
                if time.time() - start_time > timeout:
                    raise RuntimeError(f"Timeout waiting for GPIO{pin} to be exported")
                time.sleep(0.01)
    
    def _unexport_pin(self, pin):
        """Unexport a GPIO pin"""
        if os.path.exists(f"{self.GPIO_PATH}/gpio{pin}"):
            with open(f"{self.GPIO_PATH}/unexport", "w") as f:
                f.write(str(pin))
    
    def _set_pin_direction(self, pin, direction):
        """Set the direction of a GPIO pin (in/out)"""
        with open(f"{self.GPIO_PATH}/gpio{pin}/direction", "w") as f:
            f.write(direction)
    
    def _read_pin(self, pin):
        """Read the value of a GPIO pin"""
        with open(f"{self.GPIO_PATH}/gpio{pin}/value", "r") as f:
            return int(f.read().strip())
    
    def get_state(self):
        """Get the current state of the switch (True = pressed, False = released)"""
        if not self.available:
            raise RuntimeError("Switch hardware not available")
        # Switch is pulled up, so it's LOW when pressed
        return not bool(self._read_pin(self.pin))
    
    def __del__(self):
        """Clean up resources when the object is destroyed"""
        try:
            # Unexport pin
            self._unexport_pin(self.pin)
        except:
            pass