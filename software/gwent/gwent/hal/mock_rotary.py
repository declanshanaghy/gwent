#!/usr/bin/env python3

"""
Mock Rotary Encoder Module for Gwent
This module provides a mock implementation of the rotary encoder for development on non-Raspberry Pi systems.
"""

import time
import threading

class MockRotaryEncoder:
    """
    Mock class to simulate rotary encoder input.
    """
    
    def __init__(self, a_pin=7, b_pin=9, sw_pin=2, 
                 rotation_callback=None, button_callback=None):
        """
        Initialize the mock rotary encoder.
        
        Args:
            a_pin (int): GPIO pin for encoder A signal (not used in mock)
            b_pin (int): GPIO pin for encoder B signal (not used in mock)
            sw_pin (int): GPIO pin for encoder switch (not used in mock)
            rotation_callback (callable, optional): Function to call when rotation is detected.
                The callback will receive the direction (1 for clockwise, -1 for counter-clockwise) as an argument.
            button_callback (callable, optional): Function to call when button press is detected.
                The callback will receive the button state (1 for pressed, 0 for released) as an argument.
        """
        self.rotation_callback = rotation_callback
        self.button_callback = button_callback
        
        self.position = 0
        self.button_state = 0
        
        self.running = False
        self.thread = None
        
        print("Mock Rotary Encoder: Initialized")
    
    def start_monitoring(self):
        """
        Start a background thread to simulate monitoring the encoder.
        """
        if self.thread is not None and self.thread.is_alive():
            return  # Already running
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_thread)
        self.thread.daemon = True
        self.thread.start()
        print("Mock Rotary Encoder: Started monitoring")
    
    def stop_monitoring(self):
        """
        Stop the background monitoring thread.
        """
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
        print("Mock Rotary Encoder: Stopped monitoring")
    
    def _monitor_thread(self):
        """
        Background thread function to simulate monitoring the encoder.
        """
        print("Mock Rotary Encoder: Monitoring thread started")
        
        while self.running:
            time.sleep(0.1)  # Just sleep, no actual monitoring
    
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
        return self.button_state
    
    def simulate_rotation(self, direction):
        """
        Simulate a rotation event.
        
        Args:
            direction (int): 1 for clockwise, -1 for counter-clockwise
        """
        self.position += direction
        if self.rotation_callback is not None:
            self.rotation_callback(direction)
        print(f"Mock Rotary Encoder: Simulated rotation {direction}, position now {self.position}")
    
    def simulate_button_press(self, state):
        """
        Simulate a button press event.
        
        Args:
            state (int): 1 for pressed, 0 for released
        """
        self.button_state = state
        if self.button_callback is not None:
            self.button_callback(state)
        print(f"Mock Rotary Encoder: Simulated button {'press' if state == 1 else 'release'}")
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_monitoring()
        print("Mock Rotary Encoder: Cleaned up")