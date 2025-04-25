#!/usr/bin/env python3
"""
Test script to compare different rotary encoder implementations.
This script allows you to test and compare the different rotary encoder implementations
to see which one works best for your setup.
"""

import time
import argparse
import signal
import sys

from gwent.hal.rotary import RotaryImplementation
from gwent.hal.rotary_rpigpio import DirectGPIORotaryEncoder, DirectGPIOSwitch
from gwent.hal.rotary_gpiozero import GwentGPIOZeroRotaryEncoder, GPIOZeroSwitch
from gwent.hal.rotary_pigpio import PiGPIORotaryEncoder, PiGPIOSwitch

# Default BCM pin numbers
DEFAULT_A_PIN = 17  # BCM pin 17
DEFAULT_B_PIN = 22  # BCM pin 22
DEFAULT_SW_PIN = 27  # BCM pin 27

# Global variables
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    global running
    print("\nExiting rotary encoder test...")
    running = False

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Test different rotary encoder implementations')
    parser.add_argument('--implementation', type=str, choices=['rpigpio', 'gpiozero', 'pigpio'],
                        default='pigpio', help='Rotary encoder implementation to test')
    parser.add_argument('--a-pin', type=int, default=DEFAULT_A_PIN,
                        help=f'BCM pin number for A signal (default: {DEFAULT_A_PIN})')
    parser.add_argument('--b-pin', type=int, default=DEFAULT_B_PIN,
                        help=f'BCM pin number for B signal (default: {DEFAULT_B_PIN})')
    parser.add_argument('--sw-pin', type=int, default=DEFAULT_SW_PIN,
                        help=f'BCM pin number for switch (default: {DEFAULT_SW_PIN})')
    return parser.parse_args()

def run():
    """Run the rotary encoder test"""
    args = parse_args()
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"Testing rotary encoder implementation: {args.implementation}")
    print(f"Using pins: A={args.a_pin}, B={args.b_pin}, SW={args.sw_pin}")
    
    # Initialize the appropriate implementation
    if args.implementation == 'rpigpio':
        print("Using RPi.GPIO implementation")
        encoder = DirectGPIORotaryEncoder(args.a_pin, args.b_pin)
        switch = DirectGPIOSwitch(args.sw_pin)
    elif args.implementation == 'gpiozero':
        print("Using GPIOZero implementation")
        encoder = GwentGPIOZeroRotaryEncoder(args.a_pin, args.b_pin)
        switch = GPIOZeroSwitch(args.sw_pin)
    elif args.implementation == 'pigpio':
        print("Using PiGPIO implementation")
        encoder = PiGPIORotaryEncoder(args.a_pin, args.b_pin)
        switch = PiGPIOSwitch(args.sw_pin)
    else:
        print(f"Unknown implementation: {args.implementation}")
        return 1
    
    # Start the encoder
    encoder.start()
    
    # Get initial switch state
    last_switch_state = switch.get_state()
    print(f"Initial switch state: {'Pressed' if last_switch_state else 'Released'}")
    
    counter = 0
    
    print("\nRotary encoder test running. Press Ctrl+C to exit.")
    print("Rotate the encoder or press the button to see events.")
    
    # Main loop
    while running:
        # Check for rotation
        delta = encoder.get_cycles()
        if delta != 0:
            counter += delta
            direction = "clockwise" if delta > 0 else "counter-clockwise"
            print(f"Rotation detected: direction={direction}, counter={counter}")
        
        # Check for switch state change
        switch_state = switch.get_state()
        if switch_state != last_switch_state:
            print(f"Button {'pressed' if switch_state else 'released'}")
            last_switch_state = switch_state
        
        # Sleep to avoid high CPU usage
        time.sleep(0.05)
    
    # Clean up
    if hasattr(encoder, 'stop'):
        encoder.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(run())