#!/usr/bin/env python3

"""
Rotary Encoder Module for Gwent
This module provides an interface to the rotary encoder using direct GPIO access with RPi.GPIO.
"""

import time
import threading
import queue
from enum import Enum

# Import the logging module
from ..utils.logging import get_logger, set_log_level, INFO, DEBUG, WARNING, ERROR, VERBOSE

# Get a logger for this module
logger = get_logger("gwent.hal.rotary")
set_log_level("gwent.hal.rotary", INFO)

# Import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    logger.warning("RPi.GPIO module not available, will use dummy implementation")
    GPIO_AVAILABLE = False

# Define event types
class EventType(Enum):
    ROTATION = 1
    BUTTON = 2

class EncoderEvent:
    """
    Class representing an encoder event.
    """
    def __init__(self, event_type, value):
        self.event_type = event_type
        self.value = value
        self.timestamp = time.time()

class RotaryEncoder:
    """
    Class to handle rotary encoder input using direct GPIO access with RPi.GPIO.
    Uses the PEC11 Series Rotary Encoder connected via GPIO.
    """
    
    def __init__(self, a_pin=22, b_pin=17, sw_pin=27,
                 rotation_callback=None, button_callback=None):
        """
        Initialize the rotary encoder using RPi.GPIO library.
        
        Args:
            a_pin (int): GPIO pin for encoder A/DT signal (BCM numbering) - Connected to GPIO22
            b_pin (int): GPIO pin for encoder B/CLK signal (BCM numbering) - Connected to GPIO17
            sw_pin (int): GPIO pin for encoder switch (BCM numbering) - Connected to GPIO27
            rotation_callback (callable, optional): Function to call when rotation is detected.
                The callback will receive the direction (1 for clockwise, -1 for counter-clockwise) as an argument.
            button_callback (callable, optional): Function to call when button press is detected.
                The callback will receive the button state (1 for pressed, 0 for released) as an argument.
        """
        self.a_pin = int(a_pin)
        self.b_pin = int(b_pin)
        self.sw_pin = int(sw_pin)
        self.rotation_callback = rotation_callback
        self.button_callback = button_callback
        self.running = False
        self.thread = None
        self.position = 0
        
        # Create an event queue for guaranteed delivery
        self.event_queue = queue.Queue()
        
        # Variables to track encoder state
        self.current_a = 1
        self.current_b = 1
        self.last_a = 1
        self.last_b = 1
        self.last_button_state = 1  # Pull-up resistor means 1 is not pressed, 0 is pressed
        self.button_pressed = False
        
        # Variables for debouncing and detecting full clicks
        self.last_encoded = 0
        self.encoder_value = 0
        self.last_encoder_value = 0
        self.last_transition_time = time.time()
        self.last_button_time = time.time()
        self.debounce_time = 0.005  # 5ms debounce time for encoder (balanced for reliability and responsiveness)
        self.button_debounce_time = 0.02  # 20ms debounce time for button (balanced for reliability and responsiveness)
        
        self.initialized = False
        
        if GPIO_AVAILABLE:
            try:
                # Set up GPIO
                GPIO.setmode(GPIO.BCM)
                
                # Set up pins as inputs with pull-up resistors
                GPIO.setup(self.a_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(self.b_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(self.sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                self.initialized = True
                logger.info(f"Rotary encoder initialized with RPi.GPIO: A={self.a_pin}, B={self.b_pin}, SW={self.sw_pin}")
            except Exception as e:
                logger.error(f"Error initializing rotary encoder with RPi.GPIO: {e}")
                logger.error(f"Pin values: a_pin={a_pin}, b_pin={b_pin}, sw_pin={sw_pin}")
                logger.error(f"Pin types: a_pin={type(a_pin)}, b_pin={type(b_pin)}, sw_pin={type(sw_pin)}")
                logger.warning("Creating dummy rotary encoder that will not affect hardware")
                self._setup_dummy()
        else:
            logger.warning("RPi.GPIO not available, using dummy implementation")
            self._setup_dummy()
    
    def _setup_dummy(self):
        """
        Set up a dummy implementation when GPIO is not available
        """
        self.initialized = True
        logger.info("Using dummy rotary encoder (hardware access not available)")
    
    def _read_encoder(self):
        """
        Read the encoder state and detect rotation.
        Uses a simplified algorithm that's more reliable for detecting full clicks.
        """
        if not GPIO_AVAILABLE or not self.initialized:
            return
        
        # Read current state of encoder pins
        self.current_a = GPIO.input(self.a_pin)
        self.current_b = GPIO.input(self.b_pin)
        
        # Convert the two separate pins into a single number
        encoded = (self.current_a << 1) | self.current_b
        
        # Store the previous state
        previous_encoded = self.last_encoded
        
        # Only process if the state has changed
        if encoded != previous_encoded:
            # Simple state transition detection
            current_time = time.time()
            
            # Only process if enough time has passed since the last transition
            if current_time - self.last_transition_time > self.debounce_time:
                # Initialize counter if it doesn't exist
                if not hasattr(self, 'transition_counter'):
                    self.transition_counter = 0
                    self.last_direction = 0
                
                # Determine direction based on the state transition
                # Gray code pattern: 00 -> 01 -> 11 -> 10 -> 00 (clockwise)
                # Gray code pattern: 00 -> 10 -> 11 -> 01 -> 00 (counter-clockwise)
                if ((previous_encoded == 0b00 and encoded == 0b01) or
                    (previous_encoded == 0b01 and encoded == 0b11) or
                    (previous_encoded == 0b11 and encoded == 0b10) or
                    (previous_encoded == 0b10 and encoded == 0b00)):
                    # Clockwise transition
                    if self.last_direction <= 0:
                        # Direction changed or first movement
                        self.transition_counter = 1
                    else:
                        # Same direction, increment counter
                        self.transition_counter += 1
                    self.last_direction = 1
                elif ((previous_encoded == 0b00 and encoded == 0b10) or
                      (previous_encoded == 0b10 and encoded == 0b11) or
                      (previous_encoded == 0b11 and encoded == 0b01) or
                      (previous_encoded == 0b01 and encoded == 0b00)):
                    # Counter-clockwise transition
                    if self.last_direction >= 0:
                        # Direction changed or first movement
                        self.transition_counter = 1
                    else:
                        # Same direction, increment counter
                        self.transition_counter += 1
                    self.last_direction = -1
                
                # Register a full click after 2 transitions in the same direction
                # This is more reliable than waiting for 4 specific states
                if self.transition_counter >= 2:
                    direction = self.last_direction
                    self.position += direction
                    
                    if direction > 0:
                        logger.info("ROTATION DETECTED: Clockwise")
                    else:
                        logger.info("ROTATION DETECTED: Counter-clockwise")
                    
                    # Add event to queue for guaranteed delivery
                    self.event_queue.put(EncoderEvent(EventType.ROTATION, direction))
                    
                    # Also call the callback for backward compatibility
                    if self.rotation_callback is not None:
                        self.rotation_callback(direction)
                    
                    # Reset counter after registering a click
                    self.transition_counter = 0
                
                # Update the last transition time
                self.last_transition_time = current_time
        
        # Store the current state for next time
        self.last_encoded = encoded
    
    def _read_button(self):
        """
        Read the button state and detect presses with debouncing.
        """
        if not GPIO_AVAILABLE or not self.initialized:
            return
        
        # Read current button state
        button_state = GPIO.input(self.sw_pin)
        current_time = time.time()
        
        # Only process button changes after debounce time has passed
        if current_time - self.last_button_time > self.button_debounce_time:
            # Button is pressed (active low with pull-up)
            if button_state == 0 and self.last_button_state == 1:
                logger.info("Button PRESSED (Debounced)")
                self.button_pressed = True
                
                # Add event to queue for guaranteed delivery
                self.event_queue.put(EncoderEvent(EventType.BUTTON, 1))  # 1 for pressed
                
                # Also call the callback for backward compatibility
                if self.button_callback is not None:
                    self.button_callback(1)  # 1 for pressed
                self.last_button_time = current_time
            
            # Button is released
            elif button_state == 1 and self.last_button_state == 0:
                logger.info("Button RELEASED (Debounced)")
                self.button_pressed = False
                
                # Add event to queue for guaranteed delivery
                self.event_queue.put(EncoderEvent(EventType.BUTTON, 0))  # 0 for released
                
                # Also call the callback for backward compatibility
                if self.button_callback is not None:
                    self.button_callback(0)  # 0 for released
                self.last_button_time = current_time
        
        # Update previous state
        self.last_button_state = button_state
    
    def start_monitoring(self):
        """
        Start monitoring the encoder in a background thread.
        """
        if self.thread is not None and self.thread.is_alive():
            return  # Already running
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_thread)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Rotary encoder monitoring started")
    
    def stop_monitoring(self):
        """
        Stop monitoring the encoder.
        """
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
        logger.info("Rotary encoder monitoring stopped")
    
    def _monitor_thread(self):
        """
        Background thread function that continuously polls the encoder and button.
        """
        while self.running:
            if GPIO_AVAILABLE and self.initialized:
                self._read_encoder()
                self._read_button()
            
            # Small delay to prevent CPU hogging
            time.sleep(0.0005)  # Reduced sleep time for faster response
    
    def get_position(self):
        """
        Get the current encoder position.
        
        Returns:
            int: The current encoder position.
        """
        return self.position
    
    def set_position(self, position):
        """
        Set the current encoder position.
        
        Args:
            position (int): The position to set.
        """
        self.position = position
    
    def get_button_state(self):
        """
        Get the current button state.
        
        Returns:
            int: 1 if pressed, 0 if released.
        """
        if not GPIO_AVAILABLE or not self.initialized:
            return 0
        
        # Read current button state directly from GPIO
        button_state = GPIO.input(self.sw_pin)
        # Return 1 if pressed (button_state is 0 due to pull-up), 0 if released
        return 1 if button_state == 0 else 0
    
    def get_next_event(self, block=False, timeout=None):
        """
        Get the next event from the queue.
        
        Args:
            block (bool): Whether to block until an event is available
            timeout (float): Timeout in seconds if block is True
            
        Returns:
            EncoderEvent or None: The next event, or None if no event is available
        """
        try:
            return self.event_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_monitoring()
        
        # Clean up GPIO resources if we initialized them
        if GPIO_AVAILABLE and self.initialized:
            # Don't call GPIO.cleanup() here as it would affect all pins
            # Just log that we're done
            pass
            
        logger.info("Rotary encoder cleaned up")
