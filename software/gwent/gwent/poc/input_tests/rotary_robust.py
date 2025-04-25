#!/usr/bin/env python3
"""
Robust rotary encoder implementation that can work even when GPIO pins are in use.
This script uses gpiozero with the native backend, which is more tolerant of pin conflicts.
"""

import time
import signal
import sys
import argparse
import logging
from gpiozero import RotaryEncoder, Button
from gpiozero.pins.native import NativeFactory

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rotary_robust")

# Default BCM pin numbers
DEFAULT_A_PIN = 17  # BCM pin 17
DEFAULT_B_PIN = 22  # BCM pin 22
DEFAULT_SW_PIN = 27  # BCM pin 27

# Global variables
counter = 0
last_switch_state = False

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting robust rotary encoder test...")
    sys.exit(0)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Robust rotary encoder test')
    parser.add_argument('--a-pin', type=int, default=DEFAULT_A_PIN,
                        help=f'BCM pin number for A signal (default: {DEFAULT_A_PIN})')
    parser.add_argument('--b-pin', type=int, default=DEFAULT_B_PIN,
                        help=f'BCM pin number for B signal (default: {DEFAULT_B_PIN})')
    parser.add_argument('--sw-pin', type=int, default=DEFAULT_SW_PIN,
                        help=f'BCM pin number for switch (default: {DEFAULT_SW_PIN})')
    parser.add_argument('--swap-pins', action='store_true',
                        help='Swap A and B pins to test direction issues')
    parser.add_argument('--steps', type=int, default=20,
                        help='Steps per revolution (default: 20)')
    return parser.parse_args()

def run():
    """Run the robust rotary encoder test"""
    global counter, last_switch_state
    args = parse_args()
    
    # Apply pin swapping if requested
    a_pin = args.b_pin if args.swap_pins else args.a_pin
    b_pin = args.a_pin if args.swap_pins else args.b_pin
    sw_pin = args.sw_pin
    
    print("Starting robust rotary encoder test...")
    print(f"Using pins: A={a_pin}, B={b_pin}, SW={sw_pin}")
    print(f"Pin swapping: {'Enabled' if args.swap_pins else 'Disabled'}")
    print(f"Steps per revolution: {args.steps}")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Use the native pin factory for better compatibility
        factory = NativeFactory()
        
        print("\nInitializing rotary encoder with native pin factory...")
        print("This approach is more tolerant of pin conflicts.")
        input("Press Enter to continue...")
        
        # Initialize the rotary encoder with the native pin factory
        encoder = RotaryEncoder(a_pin, b_pin, wrap=True, max_steps=100, pin_factory=factory)
        button = Button(sw_pin, pull_up=True, pin_factory=factory)
        
        # Set up callbacks
        def on_clockwise():
            global counter
            counter += 1
            print(f"Clockwise rotation detected: {counter}")
        
        def on_counter_clockwise():
            global counter
            counter -= 1
            print(f"Counter-clockwise rotation detected: {counter}")
        
        def on_button_changed():
            global last_switch_state
            if button.is_pressed != last_switch_state:
                print(f"Button {'pressed' if button.is_pressed else 'released'}")
                last_switch_state = button.is_pressed
        
        # Register callbacks
        encoder.when_rotated_clockwise = on_clockwise
        encoder.when_rotated_counter_clockwise = on_counter_clockwise
        button.when_pressed = on_button_changed
        button.when_released = on_button_changed
        
        print("\nRotary encoder initialized successfully")
        print("Waiting for events... (rotate the encoder or press the button)")
        
        # Initial state
        last_switch_state = button.is_pressed
        
        # Main loop - just keep the program running
        while True:
            time.sleep(0.1)
            
    except Exception as e:
        if "GPIO" in str(e):
            print(f"\nERROR: {e}")
            print("\nThis error might be caused by GPIO pin conflicts.")
            print("Try the following:")
            print("1. Check for other processes using GPIO pins:")
            print("   ps aux | grep -i gpio")
            print("2. Stop any conflicting services:")
            print("   sudo systemctl stop gpio")
            print("3. Try different pins:")
            print(f"   python -m gwent.poc.input_tests.rotary_robust --a-pin 5 --b-pin 6 --sw-pin 13")
            print("4. Reboot the Raspberry Pi to reset all GPIO states")
        else:
            print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()