#!/usr/bin/env python3
"""
Simple test script for the rotary encoder using WiringPi.
This script will run until the user presses Ctrl+C and will output events
when rotation is detected and the button is clicked.
"""

import time
import signal
import sys
from gwent.hal.rotary_wiringpi import WiringPiRotaryEncoder, WiringPiSwitch

# WiringPi pin numbers (not BCM or physical pin numbers)
# You may need to adjust these based on your wiring
A_PIN = 4  # WiringPi pin 4
B_PIN = 5  # WiringPi pin 5
SW_PIN = 6  # WiringPi pin 6

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting rotary encoder test (WiringPi)...")
    sys.exit(0)

def run():
    """Run the rotary encoder test"""
    print("Starting rotary encoder test using WiringPi...")
    print(f"Using pins: A={A_PIN}, B={B_PIN}, SW={SW_PIN}")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Initialize the rotary encoder and switch
        encoder = WiringPiRotaryEncoder(A_PIN, B_PIN)
        switch = WiringPiSwitch(SW_PIN)
        
        # Start the encoder
        encoder.start()
        
        # Initialize state variables
        last_counter = 0
        last_switch_state = switch.get_state()
        
        print("WiringPi rotary encoder initialized successfully")
        print("Waiting for events...")
        
        # Main loop
        while True:
            # Check for rotation
            direction = encoder.get_cycles()
            if direction != 0:
                counter = encoder.get_counter()
                print(f"Rotation detected: direction={direction}, counter={counter}")
                last_counter = counter
            
            # Check for button press
            switch_state = switch.get_state()
            if switch_state != last_switch_state:
                print(f"Button {'pressed' if switch_state else 'released'}")
                last_switch_state = switch_state
            
            # Sleep to avoid high CPU usage
            time.sleep(0.05)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()