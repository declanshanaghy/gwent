#!/usr/bin/env python3

"""
Rotary Encoder Module for Gwent
This module provides an interface to the rotary encoder.
"""

import time
import threading
import RPi.GPIO as GPIO

# Try to import gpiozero for a more modern approach
try:
    from gpiozero import RotaryEncoder as GPIOZeroRotaryEncoder
    from gpiozero import Button
    GPIOZERO_AVAILABLE = True
    print("Using gpiozero library for rotary encoder")
except ImportError:
    GPIOZERO_AVAILABLE = False
    print("gpiozero not available for rotary encoder")

# Try to import gaugette as a fallback
try:
    import gaugette.gpio
    import gaugette.rotary_encoder
    import gaugette.switch
    GAUGETTE_AVAILABLE = True
except (ImportError, RuntimeError):
    GAUGETTE_AVAILABLE = False
    print("Warning: gaugette library not available or not supported on this platform. Using direct GPIO fallback.")

class RotaryEncoder:
    """
    Class to handle rotary encoder input.
    Uses the PEC11 Series Rotary Encoder connected via GPIO.
    """
    
    def __init__(self, a_pin=17, b_pin=18, sw_pin=27,
                 rotation_callback=None, button_callback=None):
        """
        Initialize the rotary encoder.
        
        Args:
            a_pin (int): GPIO pin for encoder A signal (Wiring pin number)
            b_pin (int): GPIO pin for encoder B signal (Wiring pin number)
            sw_pin (int): GPIO pin for encoder switch (Wiring pin number)
            rotation_callback (callable, optional): Function to call when rotation is detected.
                The callback will receive the direction (1 for clockwise, -1 for counter-clockwise) as an argument.
            button_callback (callable, optional): Function to call when button press is detected.
                The callback will receive the button state (1 for pressed, 0 for released) as an argument.
        """
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.sw_pin = sw_pin
        self.rotation_callback = rotation_callback
        self.button_callback = button_callback
        self.running = False
        self.thread = None
        self.position = 0
        self.last_a = 0
        self.last_b = 0
        
        try:
            if GPIOZERO_AVAILABLE:
                # Try to use gpiozero library (most modern approach)
                self.use_gpiozero = True
                self.use_gaugette = False
                
                # Create the rotary encoder with gpiozero
                self.encoder = GPIOZeroRotaryEncoder(a=a_pin, b=b_pin)
                self.button = Button(sw_pin, pull_up=True)
                
                # Set up callbacks
                self.encoder.when_rotated_clockwise = lambda: self._handle_rotation(1)
                self.encoder.when_rotated_counter_clockwise = lambda: self._handle_rotation(-1)
                self.button.when_pressed = lambda: self._handle_button(1)
                self.button.when_released = lambda: self._handle_button(0)
                
                print(f"Rotary encoder initialized with gpiozero: A={a_pin}, B={b_pin}, SW={sw_pin}")
            elif GAUGETTE_AVAILABLE:
                # Try to use gaugette library
                self.use_gpiozero = False
                self.use_gaugette = True
                
                self.gpio = gaugette.gpio.GPIO()
                self.encoder = gaugette.rotary_encoder.RotaryEncoder(self.gpio, a_pin, b_pin)
                self.switch = gaugette.switch.Switch(self.gpio, sw_pin)
                
                # Start the encoder
                self.encoder.start()
                print("Using gaugette library for rotary encoder")
            else:
                raise ImportError("Neither gpiozero nor gaugette available")
        except Exception as e:
            # Fallback to direct GPIO
            print(f"Falling back to RPi.GPIO for rotary encoder: {e}")
            self.use_gpiozero = False
            self.use_gaugette = False
            
            # Set up GPIO
            try:
                # Set mode to BCM without cleaning up existing pins
                # This avoids interfering with other components like the display
                if GPIO.getmode() != GPIO.BCM:
                    GPIO.setmode(GPIO.BCM)  # Use BCM numbering
                
                # Use BCM pin numbering directly
                # Skip the WiringPi to BCM conversion as it might be causing issues
                self.a_pin_bcm = a_pin
                self.b_pin_bcm = b_pin
                self.sw_pin_bcm = sw_pin
                
                print(f"Rotary encoder pins: A={a_pin}→{self.a_pin_bcm}, B={b_pin}→{self.b_pin_bcm}, SW={sw_pin}→{self.sw_pin_bcm}")
                
                # Set up pins
                GPIO.setup(self.a_pin_bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(self.b_pin_bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(self.sw_pin_bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                # Read initial states
                self.last_a = GPIO.input(self.a_pin_bcm)
                self.last_b = GPIO.input(self.b_pin_bcm)
                self.last_button_state = GPIO.input(self.sw_pin_bcm)
                
                print(f"Initial pin states: A={self.last_a}, B={self.last_b}, SW={self.last_button_state}")
            except Exception as gpio_error:
                print(f"Error setting up GPIO pins: {gpio_error}")
                # Try one more time with different pin numbers
                try:
                    # Use different pin numbers that might be more compatible
                    self.a_pin_bcm = 23  # Try a different pin
                    self.b_pin_bcm = 24  # Try a different pin
                    self.sw_pin_bcm = 25  # Try a different pin
                    
                    print(f"Retrying with different pins: A={self.a_pin_bcm}, B={self.b_pin_bcm}, SW={self.sw_pin_bcm}")
                    
                    # Set up pins
                    GPIO.setup(self.a_pin_bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    GPIO.setup(self.b_pin_bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    GPIO.setup(self.sw_pin_bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    
                    # Read initial states
                    self.last_a = GPIO.input(self.a_pin_bcm)
                    self.last_b = GPIO.input(self.b_pin_bcm)
                    self.last_button_state = GPIO.input(self.sw_pin_bcm)
                except Exception as retry_error:
                    print(f"Error setting up GPIO pins (retry): {retry_error}")
    
    def start_monitoring(self):
        """
        Start a background thread to monitor the encoder.
        """
        if self.thread is not None and self.thread.is_alive():
            return  # Already running
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_thread)
        self.thread.daemon = True
        self.thread.start()
    
    def stop_monitoring(self):
        """
        Stop the background monitoring thread.
        """
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
    
    def _handle_rotation(self, direction):
        """
        Handle rotation events from gpiozero.
        
        Args:
            direction (int): 1 for clockwise, -1 for counter-clockwise
        """
        self.position += direction
        print(f"ROTATION DETECTED: {'Clockwise' if direction > 0 else 'Counter-clockwise'}")
        if self.rotation_callback is not None:
            self.rotation_callback(direction)
    
    def _handle_button(self, state):
        """
        Handle button events from gpiozero.
        
        Args:
            state (int): 1 for pressed, 0 for released
        """
        if self.button_callback is not None:
            self.button_callback(state)
    
    def _monitor_thread(self):
        """
        Background thread function to monitor the encoder.
        """
        # If using gpiozero, we don't need to poll as it uses callbacks
        if self.use_gpiozero:
            while self.running:
                time.sleep(0.1)  # Just keep the thread alive
            return
            
        # For gaugette
        if self.use_gaugette:
            last_button_state = self.switch.get_state()
        else:
            last_button_state = self.last_button_state
        
        while self.running:
            try:
                if self.use_gaugette:
                    # Check for rotation using gaugette
                    delta = self.encoder.get_cycles()
                    if delta != 0 and self.rotation_callback is not None:
                        self.rotation_callback(delta)
                    
                    # Check for button press using gaugette
                    button_state = self.switch.get_state()
                    if button_state != last_button_state and self.button_callback is not None:
                        self.button_callback(button_state)
                        last_button_state = button_state
                else:
                    # Check for rotation using direct GPIO
                    try:
                        # Make sure GPIO is set up properly - but don't check with gpio_function
                        # as it can interfere with other components
                        try:
                            # Just try to read the pins directly
                            GPIO.setup(self.a_pin_bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                            GPIO.setup(self.b_pin_bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                            GPIO.setup(self.sw_pin_bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                        except Exception as setup_error:
                            print(f"Error setting up GPIO pins: {setup_error}")
                        
                        a = GPIO.input(self.a_pin_bcm)
                        b = GPIO.input(self.b_pin_bcm)
                        
                        # Always log pin states for debugging
                        print(f"Rotary encoder pin states: A={a} (BCM {self.a_pin_bcm}), B={b} (BCM {self.b_pin_bcm}), Last A={self.last_a}, Last B={self.last_b}")
                    except Exception as e:
                        print(f"Error reading rotary encoder pins: {e}")
                        time.sleep(0.5)
                        continue
                    
                    # Super simple rotation detection - just detect any change and log it
                    delta = 0
                    
                    # If either pin changed state, consider it a rotation
                    if a != self.last_a or b != self.last_b:
                        # Determine direction based on A pin
                        if a != self.last_a:
                            if a == 1:  # Rising edge on A
                                delta = 1  # Assume clockwise
                                print("ROTATION DETECTED: Clockwise")
                            else:
                                delta = -1  # Assume counter-clockwise
                                print("ROTATION DETECTED: Counter-clockwise")
                        # If A didn't change but B did, use B for direction
                        elif b != self.last_b:
                            if b == 1:  # Rising edge on B
                                delta = -1  # Assume counter-clockwise
                                print("ROTATION DETECTED: Counter-clockwise (B pin)")
                            else:
                                delta = 1  # Assume clockwise
                                print("ROTATION DETECTED: Clockwise (B pin)")
                        
                        if delta != 0:
                            self.position += delta
                            if self.rotation_callback is not None:
                                self.rotation_callback(delta)
                        
                        # Update last states
                        self.last_a = a
                        self.last_b = b
                    
                    # Check for button press using direct GPIO
                    button_state = GPIO.input(self.sw_pin_bcm)
                    # Button is active low (pressed = 0)
                    button_state = 1 if button_state == 0 else 0
                    
                    if button_state != last_button_state and self.button_callback is not None:
                        self.button_callback(button_state)
                        last_button_state = button_state
                
                # Small delay to prevent CPU hogging
                time.sleep(0.01)
                
            except Exception as e:
                print(f"Error in rotary encoder monitoring thread: {e}")
                time.sleep(0.5)  # Longer delay on error
    
    def get_position(self):
        """
        Get the current encoder position.
        
        Returns:
            int: The current encoder position.
        """
        if self.use_gpiozero:
            return self.position  # gpiozero doesn't track position, so we use our own
        elif self.use_gaugette:
            return self.encoder.get_position()
        else:
            return self.position
    
    def set_position(self, position):
        """
        Set the current encoder position.
        
        Args:
            position (int): The position to set.
        """
        if self.use_gpiozero:
            self.position = position  # gpiozero doesn't track position, so we use our own
        elif self.use_gaugette:
            self.encoder.set_position(position)
        else:
            self.position = position
    
    def get_button_state(self):
        """
        Get the current button state.
        
        Returns:
            int: 1 if pressed, 0 if released.
        """
        if self.use_gpiozero:
            return 1 if self.button.is_pressed else 0
        elif self.use_gaugette:
            return self.switch.get_state()
        else:
            # Button is active low (pressed = 0)
            state = GPIO.input(self.sw_pin_bcm)
            return 1 if state == 0 else 0
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_monitoring()
        
        # Clean up resources based on the implementation used
        if self.use_gpiozero:
            # gpiozero handles cleanup automatically
            pass
        elif not self.use_gaugette:
            # Don't clean up GPIO pins as they might be shared with other components
            # Just log that we're done
            print("Rotary encoder cleaned up (GPIO pins left intact)")