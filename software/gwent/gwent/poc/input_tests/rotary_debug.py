#!/usr/bin/env python3
"""
Diagnostic script for debugging rotary encoder issues.
This script provides detailed logging and allows testing different configurations.
"""

import time
import signal
import sys
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rotary_debug")

# Import both implementations
from gwent.hal.rotary_rpigpio import DirectGPIORotaryEncoder, DirectGPIOSwitch
from gwent.hal.rotary_gpiozero import GwentGPIOZeroRotaryEncoder, GPIOZeroSwitch

# Default BCM pin numbers
DEFAULT_A_PIN = 17  # BCM pin 17
DEFAULT_B_PIN = 22  # BCM pin 22
DEFAULT_SW_PIN = 27  # BCM pin 27

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting rotary encoder debug script...")
    sys.exit(0)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Debug rotary encoder issues')
    parser.add_argument('--implementation', type=str, choices=['direct', 'gpiozero'], default='direct',
                        help='Which implementation to use (direct or gpiozero)')
    parser.add_argument('--a-pin', type=int, default=DEFAULT_A_PIN,
                        help=f'BCM pin number for A signal (default: {DEFAULT_A_PIN})')
    parser.add_argument('--b-pin', type=int, default=DEFAULT_B_PIN,
                        help=f'BCM pin number for B signal (default: {DEFAULT_B_PIN})')
    parser.add_argument('--sw-pin', type=int, default=DEFAULT_SW_PIN,
                        help=f'BCM pin number for switch (default: {DEFAULT_SW_PIN})')
    parser.add_argument('--swap-pins', action='store_true',
                        help='Swap A and B pins to test direction issues')
    return parser.parse_args()

def rotation_callback(direction):
    """Callback function for rotary encoder rotation"""
    logger.info(f"Rotation callback: direction={direction}")

def run():
    """Run the rotary encoder debug script"""
    args = parse_args()
    
    # Apply pin swapping if requested
    a_pin = args.b_pin if args.swap_pins else args.a_pin
    b_pin = args.a_pin if args.swap_pins else args.b_pin
    sw_pin = args.sw_pin
    
    print("Starting rotary encoder debug script...")
    print(f"Implementation: {args.implementation}")
    print(f"Using pins: A={a_pin}, B={b_pin}, SW={sw_pin}")
    print(f"Pin swapping: {'Enabled' if args.swap_pins else 'Disabled'}")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Initialize the rotary encoder based on selected implementation
        if args.implementation == 'direct':
            logger.info("Initializing DirectGPIORotaryEncoder")
            encoder = DirectGPIORotaryEncoder(a_pin, b_pin, callback=rotation_callback, log=logger)
            switch = DirectGPIOSwitch(sw_pin)
            print("DirectGPIO rotary encoder initialized")
        else:
            logger.info("Initializing GwentGPIOZeroRotaryEncoder")
            encoder = GwentGPIOZeroRotaryEncoder(a_pin, b_pin, callback=rotation_callback, log=logger)
            switch = GPIOZeroSwitch(sw_pin)
            print("GPIOZero rotary encoder initialized")
        
        # Start the encoder
        encoder.start()
        
        # Initialize state variables
        last_counter = 0
        last_switch_state = switch.get_state()
        
        print("Rotary encoder initialized successfully")
        print("Waiting for events... (rotate the encoder or press the button)")
        
        # Main loop
        while True:
            # Check for rotation
            counter = encoder.get_counter()
            if counter != last_counter:
                direction = encoder.get_direction()
                print(f"Counter changed: {last_counter} -> {counter} (direction: {direction})")
                last_counter = counter
            
            # Check for button press
            switch_state = switch.get_state()
            if switch_state != last_switch_state:
                print(f"Button {'pressed' if switch_state else 'released'}")
                last_switch_state = switch_state
            
            # Sleep to avoid high CPU usage
            time.sleep(0.05)
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run()