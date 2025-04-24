#!/usr/bin/env python3
"""
Simple test script for the rotary encoder using gpiozero.
This script will run until the user presses Ctrl+C and will output events
when rotation is detected and the button is clicked.
"""

import time
import signal
import sys
import argparse
import threading
from gwent.hal.rotary_gpiozero import GwentGPIOZeroRotaryEncoder, GPIOZeroSwitch

# Default BCM pin numbers (not physical pin numbers)
# These can be overridden with command-line arguments
DEFAULT_A_PIN = 17  # BCM pin 17
DEFAULT_B_PIN = 27  # BCM pin 27
DEFAULT_SW_PIN = 22  # BCM pin 22

# Global variables
encoder = None
switch = None
last_switch_state = False
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting rotary encoder test (gpiozero)...")
    sys.exit(0)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Test rotary encoder using gpiozero')
    parser.add_argument('--a-pin', type=int, default=DEFAULT_A_PIN,
                        help=f'BCM pin number for A signal (default: {DEFAULT_A_PIN})')
    parser.add_argument('--b-pin', type=int, default=DEFAULT_B_PIN,
                        help=f'BCM pin number for B signal (default: {DEFAULT_B_PIN})')
    parser.add_argument('--sw-pin', type=int, default=DEFAULT_SW_PIN,
                        help=f'BCM pin number for switch (default: {DEFAULT_SW_PIN})')
    return parser.parse_args()

def rotation_callback(direction):
    """Callback function for rotary encoder rotation"""
    counter = encoder.get_counter()
    print(f"Rotation detected: direction={direction}, counter={counter}")

def button_callback():
    """Callback function for button state changes"""
    global last_switch_state
    switch_state = switch.get_state()
    if switch_state != last_switch_state:
        print(f"Button {'pressed' if switch_state else 'released'}")
        last_switch_state = switch_state

def check_button():
    """Check button state periodically"""
    global running
    while running:
        button_callback()
        time.sleep(0.05)

def run():
    """Run the rotary encoder test"""
    global encoder, switch, last_switch_state, running
    
    args = parse_args()
    a_pin = args.a_pin
    b_pin = args.b_pin
    sw_pin = args.sw_pin
    
    print("Starting rotary encoder test using gpiozero...")
    print(f"Using pins: A={a_pin}, B={b_pin}, SW={sw_pin}")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Initialize state variables
        running = True
        last_switch_state = False
        
        # Initialize the rotary encoder with callback
        encoder = GwentGPIOZeroRotaryEncoder(a_pin, b_pin, callback=rotation_callback)
        switch = GPIOZeroSwitch(sw_pin)
        
        # Start the encoder
        encoder.start()
        
        print("GPIOZero rotary encoder initialized successfully")
        print("Waiting for events...")
        
        # Start button checking thread
        button_thread = threading.Thread(target=check_button, daemon=True)
        button_thread.start()
        
        # Main loop - just keep the program running
        while True:
            time.sleep(0.1)
            
    except Exception as e:
        if "GPIO busy" in str(e):
            print(f"\nERROR: {e}")
            print(f"Pins in use: A={a_pin}, B={b_pin}, SW={sw_pin}")
            print("Try one of the following:")
            print("1. Stop any other processes that might be using these GPIO pins")
            print("2. Try different pins using command-line arguments:")
            print(f"   python -m gwent.poc.rotary-gpiozero-test --a-pin 5 --b-pin 6 --sw-pin 13")
        else:
            print(f"ERROR: {e}")
        running = False
        sys.exit(1)

if __name__ == "__main__":
    run()