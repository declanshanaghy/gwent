#!/usr/bin/env python3
"""
Rotary encoder implementation using lgpio.
This script uses the lgpio library which is designed for modern Raspberry Pi OS versions
and can work even when other GPIO services are running.
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
logger = logging.getLogger("rotary_lgpio")

# Default BCM pin numbers
DEFAULT_A_PIN = 17  # BCM pin 17
DEFAULT_B_PIN = 22  # BCM pin 22
DEFAULT_SW_PIN = 27  # BCM pin 27

# Global variables
counter = 0
last_a_state = None
last_b_state = None
last_sw_state = None

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting lgpio rotary encoder test...")
    sys.exit(0)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='LGPIO rotary encoder test')
    parser.add_argument('--a-pin', type=int, default=DEFAULT_A_PIN,
                        help=f'BCM pin number for A signal (default: {DEFAULT_A_PIN})')
    parser.add_argument('--b-pin', type=int, default=DEFAULT_B_PIN,
                        help=f'BCM pin number for B signal (default: {DEFAULT_B_PIN})')
    parser.add_argument('--sw-pin', type=int, default=DEFAULT_SW_PIN,
                        help=f'BCM pin number for switch (default: {DEFAULT_SW_PIN})')
    parser.add_argument('--swap-pins', action='store_true',
                        help='Swap A and B pins to test direction issues')
    return parser.parse_args()

def run():
    """Run the lgpio rotary encoder test"""
    global counter, last_a_state, last_b_state, last_sw_state
    args = parse_args()
    
    # Apply pin swapping if requested
    a_pin = args.b_pin if args.swap_pins else args.a_pin
    b_pin = args.a_pin if args.swap_pins else args.b_pin
    sw_pin = args.sw_pin
    
    print("Starting lgpio rotary encoder test...")
    print(f"Using pins: A={a_pin}, B={b_pin}, SW={sw_pin}")
    print(f"Pin swapping: {'Enabled' if args.swap_pins else 'Disabled'}")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # First, try to import lgpio
        try:
            import lgpio
        except ImportError:
            print("\nERROR: lgpio library not found.")
            print("This script requires the lgpio library, which is included in recent Raspberry Pi OS versions.")
            print("If you're using an older version, you can install it with:")
            print("sudo apt-get update")
            print("sudo apt-get install -y python3-lgpio")
            sys.exit(1)
        
        print("\nInitializing rotary encoder with lgpio...")
        print("This approach is designed to work with modern Raspberry Pi OS versions.")
        input("Press Enter to continue...")
        
        # Open the GPIO chip
        h = lgpio.gpiochip_open(0)
        
        # Configure pins as inputs with pull-up resistors
        lgpio.gpio_claim_input(h, a_pin, lgpio.SET_PULL_UP)
        lgpio.gpio_claim_input(h, b_pin, lgpio.SET_PULL_UP)
        lgpio.gpio_claim_input(h, sw_pin, lgpio.SET_PULL_UP)
        
        # Read initial states
        last_a_state = lgpio.gpio_read(h, a_pin)
        last_b_state = lgpio.gpio_read(h, b_pin)
        last_sw_state = lgpio.gpio_read(h, sw_pin)
        
        print("Initial pin states:")
        print(f"A (Pin {a_pin}): {last_a_state}")
        print(f"B (Pin {b_pin}): {last_b_state}")
        print(f"SW (Pin {sw_pin}): {last_sw_state}")
        
        print("\nRotary encoder initialized successfully")
        print("Waiting for events... (rotate the encoder or press the button)")
        
        # Main loop
        while True:
            # Read current pin states
            a_state = lgpio.gpio_read(h, a_pin)
            b_state = lgpio.gpio_read(h, b_pin)
            sw_state = lgpio.gpio_read(h, sw_pin)
            
            # Check for switch state change
            if sw_state != last_sw_state:
                print(f"Button {'released' if sw_state else 'pressed'}")
                last_sw_state = sw_state
            
            # Check for rotation
            if a_state != last_a_state or b_state != last_b_state:
                if last_a_state is not None and last_b_state is not None:
                    # State transition table for clockwise rotation:
                    # 00 -> 01 -> 11 -> 10 -> 00
                    # For counter-clockwise, the sequence is reversed
                    
                    last_state = (last_a_state << 1) | last_b_state
                    current_state = (a_state << 1) | b_state
                    
                    # Check for valid state transitions
                    if (last_state == 0b00 and current_state == 0b01) or \
                       (last_state == 0b01 and current_state == 0b11) or \
                       (last_state == 0b11 and current_state == 0b10) or \
                       (last_state == 0b10 and current_state == 0b00):
                        counter += 1
                        print(f"Clockwise rotation detected: {counter}")
                    elif (last_state == 0b00 and current_state == 0b10) or \
                         (last_state == 0b10 and current_state == 0b11) or \
                         (last_state == 0b11 and current_state == 0b01) or \
                         (last_state == 0b01 and current_state == 0b00):
                        counter -= 1
                        print(f"Counter-clockwise rotation detected: {counter}")
                
                # Update last states
                last_a_state = a_state
                last_b_state = b_state
            
            # Sleep to avoid high CPU usage
            time.sleep(0.01)
            
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nThis error might be caused by GPIO pin conflicts or permission issues.")
        print("Try the following:")
        print("1. Run with sudo:")
        print("   sudo python3 -m gwent.poc.input_tests.rotary_lgpio")
        print("2. Try different pins:")
        print(f"   python3 -m gwent.poc.input_tests.rotary_lgpio --a-pin 5 --b-pin 6 --sw-pin 13")
        print("3. Check if the lgpio library is installed and working:")
        print("   python3 -c 'import lgpio; print(\"lgpio version:\", lgpio.version())'")
        print("4. Reboot the Raspberry Pi to reset all GPIO states")
        sys.exit(1)
    finally:
        # Clean up
        try:
            lgpio.gpiochip_close(h)
        except:
            pass

if __name__ == "__main__":
    run()