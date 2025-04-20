#!/usr/bin/env python3

"""
Rotary Encoder Module for Gwent
This module provides an interface to the rotary encoder.
"""

import time
import threading
import RPi.GPIO as GPIO
import gaugette.gpio
import gaugette.rotary_encoder
import gaugette.switch

class RotaryEncoder:
    """
    Class to handle rotary encoder input.
    Uses the PEC11 Series Rotary Encoder connected via GPIO.
    """
    
    def __init__(self, a_pin=7, b_pin=9, sw_pin=2, 
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
        self.gpio = gaugette.gpio.GPIO()
        self.encoder = gaugette.rotary_encoder.RotaryEncoder(self.gpio, a_pin, b_pin)
        self.switch = gaugette.switch.Switch(self.gpio, sw_pin)
        
        self.rotation_callback = rotation_callback
        self.button_callback = button_callback
        
        self.running = False
        self.thread = None
        
        # Start the encoder
        self.encoder.start()
    
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
    
    def _monitor_thread(self):
        """
        Background thread function to monitor the encoder.
        """
        last_button_state = self.switch.get_state()
        
        while self.running:
            try:
                # Check for rotation
                delta = self.encoder.get_cycles()
                if delta != 0 and self.rotation_callback is not None:
                    self.rotation_callback(delta)
                
                # Check for button press
                button_state = self.switch.get_state()
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
        return self.encoder.get_position()
    
    def set_position(self, position):
        """
        Set the current encoder position.
        
        Args:
            position (int): The position to set.
        """
        self.encoder.set_position(position)
    
    def get_button_state(self):
        """
        Get the current button state.
        
        Returns:
            int: 1 if pressed, 0 if released.
        """
        return self.switch.get_state()
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_monitoring()