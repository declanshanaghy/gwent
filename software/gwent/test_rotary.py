#!/usr/bin/env python3

"""
Test script for the rotary encoder functionality.
This script simulates rotary encoder events and tests the callbacks.
"""

import time
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the mock rotary encoder
from gwent.hal.rotary_mock import MockRotaryEncoder

def on_rotation(direction):
    """
    Callback for rotary encoder rotation events.
    
    Args:
        direction (int): 1 for clockwise, -1 for counter-clockwise
    """
    direction_text = "clockwise" if direction > 0 else "counter-clockwise"
    print(f"Rotary event: Dial turned {direction_text}")

def on_button(state):
    """
    Callback for rotary encoder button events.
    
    Args:
        state (int): 1 for pressed, 0 for released
    """
    state_text = "pressed" if state == 1 else "released"
    print(f"Rotary event: Button {state_text}")

def main():
    """
    Main function to test the rotary encoder.
    """
    print("Starting rotary encoder test...")
    
    # Initialize the mock rotary encoder with callbacks
    rotary = MockRotaryEncoder(
        rotation_callback=on_rotation,
        button_callback=on_button
    )
    
    # Start monitoring
    rotary.start_monitoring()
    
    try:
        # Simulate some rotary encoder events
        print("\nSimulating clockwise rotation...")
        rotary.simulate_rotation(1)
        time.sleep(1)
        
        print("\nSimulating counter-clockwise rotation...")
        rotary.simulate_rotation(-1)
        time.sleep(1)
        
        print("\nSimulating button press...")
        rotary.simulate_button_press(1)
        time.sleep(1)
        
        print("\nSimulating button release...")
        rotary.simulate_button_press(0)
        time.sleep(1)
        
        # Simulate multiple rotations
        print("\nSimulating multiple clockwise rotations...")
        for _ in range(3):
            rotary.simulate_rotation(1)
            time.sleep(0.5)
        
        print("\nSimulating multiple counter-clockwise rotations...")
        for _ in range(3):
            rotary.simulate_rotation(-1)
            time.sleep(0.5)
        
        print("\nTest completed successfully!")
    
    finally:
        # Clean up
        rotary.cleanup()

if __name__ == "__main__":
    main()