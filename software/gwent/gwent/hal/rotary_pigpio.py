import threading
import time
import pigpio
from gwent.hal.rotary_base import AbstractRotaryEncoder, AbstractSwitch

class SimpleLogger:
    """A simple logger class for when a real logger is not available"""
    def info(self, msg):
        print(f"INFO: {msg}")
        
    def warning(self, msg):
        print(f"WARNING: {msg}")
        
    def debug(self, msg):
        pass  # Ignore debug messages


class PiGPIORotaryEncoder(AbstractRotaryEncoder):
    """
    A class to decode mechanical rotary encoder pulses using pigpio.
    Implements the AbstractRotaryEncoder interface.
    
    This implementation uses the pigpio library which can work alongside other GPIO services,
    making it more robust than the RPi.GPIO implementation.
    """
    
    def __init__(self, a_pin, b_pin, callback=None, log=None, host='localhost', port=8888):
        """
        Initialize the rotary encoder.
        
        Args:
            a_pin: The pin number for the A signal (BCM pin numbering)
            b_pin: The pin number for the B signal (BCM pin numbering)
            callback: Optional callback function to be called when rotation is detected
            log: Optional logger instance
            host: pigpio daemon host (default: localhost)
            port: pigpio daemon port (default: 8888)
        """
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.callback = callback
        self.host = host
        self.port = port
        
        self.counter = 0
        self.direction = None
        self.lock = threading.Lock()
        self.running = False
        self.available = False
        
        # Use provided logger or create a simple print wrapper
        self._log = log or SimpleLogger()
        
        # Initialize pigpio
        try:
            self.pi = pigpio.pi(self.host, self.port)
            if not self.pi.connected:
                self._log.warning("Could not connect to pigpio daemon")
                raise RuntimeError("Could not connect to pigpio daemon")
            
            # Set up pins as inputs with pull-up resistors
            self.pi.set_mode(self.a_pin, pigpio.INPUT)
            self.pi.set_mode(self.b_pin, pigpio.INPUT)
            self.pi.set_pull_up_down(self.a_pin, pigpio.PUD_UP)
            self.pi.set_pull_up_down(self.b_pin, pigpio.PUD_UP)
            
            self._log.info(f"Initialized rotary encoder with pins A={self.a_pin}, B={self.b_pin}")
            self.available = True
        except Exception as e:
            self._log.warning(f"Error setting up pigpio pins: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize rotary encoder pigpio pins: {e}")
    
    def start(self):
        """Start the encoder monitoring"""
        if not self.available:
            raise RuntimeError("Rotary encoder hardware not available")
        
        self.running = True
        
        # Initialize state
        self.levA = self.pi.read(self.a_pin)
        self.levB = self.pi.read(self.b_pin)
        self.lastGpio = None
        
        # Set up callbacks for both pins
        self.cb_a = self.pi.callback(self.a_pin, pigpio.EITHER_EDGE, self._pulse)
        self.cb_b = self.pi.callback(self.b_pin, pigpio.EITHER_EDGE, self._pulse)
        
        self._log.info("Rotary encoder monitoring started")
    
    def stop(self):
        """Stop the encoder monitoring"""
        self.running = False
        if hasattr(self, 'cb_a') and self.cb_a:
            self.cb_a.cancel()
        if hasattr(self, 'cb_b') and self.cb_b:
            self.cb_b.cancel()
        self._log.info("Rotary encoder monitoring stopped")
    
    def _pulse(self, gpio, level, tick):
        """
        Decode the rotary encoder pulse.
        
        Args:
            gpio: The GPIO that changed state
            level: The new level
            tick: The timestamp of the change
        """
        if not self.running:
            return
            
        if gpio == self.a_pin:
            self.levA = level
        else:
            self.levB = level
        
        if gpio != self.lastGpio:  # Debounce
            self.lastGpio = gpio
            
            with self.lock:
                if gpio == self.a_pin and level == 1:
                    if self.levB == 1:
                        self.counter += 1
                        self.direction = 1
                        if self.callback:
                            self.callback(1)
                elif gpio == self.b_pin and level == 1:
                    if self.levA == 1:
                        self.counter -= 1
                        self.direction = -1
                        if self.callback:
                            self.callback(-1)
    
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
        if hasattr(self, 'pi') and self.pi.connected:
            self.pi.stop()


class PiGPIOSwitch(AbstractSwitch):
    """A switch class using pigpio that implements the AbstractSwitch interface"""
    
    def __init__(self, pin, host='localhost', port=8888):
        """
        Initialize the switch.
        
        Args:
            pin: The pin number for the switch (BCM pin numbering)
            host: pigpio daemon host (default: localhost)
            port: pigpio daemon port (default: 8888)
        """
        self.pin = pin
        self.host = host
        self.port = port
        self.available = False
        
        try:
            # Connect to pigpio daemon
            self.pi = pigpio.pi(self.host, self.port)
            if not self.pi.connected:
                print("Could not connect to pigpio daemon")
                raise RuntimeError("Could not connect to pigpio daemon")
            
            # Set up pin as input with pull-up resistor
            self.pi.set_mode(self.pin, pigpio.INPUT)
            self.pi.set_pull_up_down(self.pin, pigpio.PUD_UP)
            
            # Set up callback for the pin
            self.cb = self.pi.callback(self.pin, pigpio.EITHER_EDGE, self._pulse)
            
            # Initialize state
            self.state = self.pi.read(self.pin)
            
            print(f"Initialized switch with pin {pin}")
            self.available = True
        except Exception as e:
            print(f"Error setting up pigpio pin for switch: {e}")
            self.available = False
            raise RuntimeError(f"Failed to initialize switch pigpio pin: {e}")
    
    def _pulse(self, gpio, level, tick):
        """
        Update the switch state.
        
        Args:
            gpio: The GPIO that changed state
            level: The new level
            tick: The timestamp of the change
        """
        self.state = level
    
    def get_state(self):
        """Get the current state of the switch (True = pressed, False = released)"""
        if not self.available:
            raise RuntimeError("Switch hardware not available")
        # Switch is pulled up, so it's LOW when pressed
        return not self.state
    
    def __del__(self):
        """Clean up resources when the object is destroyed"""
        if hasattr(self, 'cb'):
            self.cb.cancel()
        if hasattr(self, 'pi') and self.pi.connected:
            self.pi.stop()