#!/usr/bin/env python3
"""
Enhanced diagnostic script for debugging rotary encoder issues.
This script provides detailed pin state monitoring and visualization.
"""

import time
import signal
import sys
import argparse
import logging
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rotary_diagnostic")

# Default BCM pin numbers
DEFAULT_A_PIN = 17  # BCM pin 17
DEFAULT_B_PIN = 22  # BCM pin 22
DEFAULT_SW_PIN = 27  # BCM pin 27

# Global variables for state tracking
pin_states = []
last_a_state = None
last_b_state = None
last_sw_state = None
counter = 0

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting rotary encoder diagnostic script...")
    GPIO.cleanup()
    sys.exit(0)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Advanced diagnostics for rotary encoder issues')
    parser.add_argument('--a-pin', type=int, default=DEFAULT_A_PIN,
                        help=f'BCM pin number for A signal (default: {DEFAULT_A_PIN})')
    parser.add_argument('--b-pin', type=int, default=DEFAULT_B_PIN,
                        help=f'BCM pin number for B signal (default: {DEFAULT_B_PIN})')
    parser.add_argument('--sw-pin', type=int, default=DEFAULT_SW_PIN,
                        help=f'BCM pin number for switch (default: {DEFAULT_SW_PIN})')
    parser.add_argument('--swap-pins', action='store_true',
                        help='Swap A and B pins to test direction issues')
    parser.add_argument('--monitor-time', type=float, default=0.5,
                        help='Time in seconds to monitor pin states (default: 0.5)')
    return parser.parse_args()

def pin_change_callback(channel):
    """Callback function for GPIO event detection"""
    global last_a_state, last_b_state, last_sw_state, counter, pin_states
    
    # Read current pin states
    a_state = GPIO.input(args.a_pin)
    b_state = GPIO.input(args.b_pin)
    sw_state = GPIO.input(args.sw_pin)
    
    # Record state change
    timestamp = time.time()
    pin_states.append((timestamp, channel, a_state, b_state, sw_state))
    
    # Log the state change
    logger.debug(f"Pin change on {channel}: A={a_state}, B={b_state}, SW={sw_state}")
    
    # Detect rotation based on state transitions
    if channel in [args.a_pin, args.b_pin]:
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
                logger.info(f"Clockwise rotation detected: {counter}")
                print(f"Clockwise rotation detected: {counter}")
            elif (last_state == 0b00 and current_state == 0b10) or \
                 (last_state == 0b10 and current_state == 0b11) or \
                 (last_state == 0b11 and current_state == 0b01) or \
                 (last_state == 0b01 and current_state == 0b00):
                counter -= 1
                logger.info(f"Counter-clockwise rotation detected: {counter}")
                print(f"Counter-clockwise rotation detected: {counter}")
    
    # Update last states
    last_a_state = a_state
    last_b_state = b_state
    last_sw_state = sw_state

def monitor_pins(duration):
    """Monitor pin states for a specified duration"""
    global pin_states
    pin_states = []
    
    print(f"Preparing to monitor pin states for {duration} seconds...")
    print("When ready, rotate the encoder slowly during the monitoring period.")
    input("Press Enter to start monitoring...")
    
    start_time = time.time()
    end_time = start_time + duration
    
    print(f"Monitoring started! Rotate the encoder slowly for {duration} seconds...")
    
    # Read initial states
    a_state = GPIO.input(args.a_pin)
    b_state = GPIO.input(args.b_pin)
    sw_state = GPIO.input(args.sw_pin)
    
    pin_states.append((start_time, None, a_state, b_state, sw_state))
    
    while time.time() < end_time:
        # Read current pin states
        current_a_state = GPIO.input(args.a_pin)
        current_b_state = GPIO.input(args.b_pin)
        current_sw_state = GPIO.input(args.sw_pin)
        
        # Check for changes
        if current_a_state != a_state or current_b_state != b_state or current_sw_state != sw_state:
            timestamp = time.time()
            pin_states.append((timestamp, None, current_a_state, current_b_state, current_sw_state))
            
            # Update states
            a_state = current_a_state
            b_state = current_b_state
            sw_state = current_sw_state
        
        time.sleep(0.001)  # Poll at 1kHz
    
    print("Monitoring complete!")
    
    # Print the results
    print("\nPin state changes during monitoring:")
    print("Timestamp\tChannel\tA\tB\tSW")
    
    for state in pin_states:
        timestamp, channel, a, b, sw = state
        rel_time = timestamp - start_time
        channel_str = str(channel) if channel is not None else "-"
        print(f"{rel_time:.3f}s\t{channel_str}\t{a}\t{b}\t{sw}")
    
    # Analyze the results
    if len(pin_states) <= 1:
        print("\nNo pin state changes detected. Possible issues:")
        print("1. Rotary encoder is not connected properly")
        print("2. Pins are not configured correctly")
        print("3. Rotary encoder is faulty")
    else:
        print(f"\nDetected {len(pin_states)} pin state changes")
        
        # Check for valid state transitions
        valid_transitions = 0
        invalid_transitions = 0
        
        for i in range(1, len(pin_states)):
            prev_a = pin_states[i-1][2]
            prev_b = pin_states[i-1][3]
            curr_a = pin_states[i][2]
            curr_b = pin_states[i][3]
            
            prev_state = (prev_a << 1) | prev_b
            curr_state = (curr_a << 1) | curr_b
            
            # Check if this is a valid transition
            valid = False
            if (prev_state == 0b00 and curr_state == 0b01) or \
               (prev_state == 0b01 and curr_state == 0b11) or \
               (prev_state == 0b11 and curr_state == 0b10) or \
               (prev_state == 0b10 and curr_state == 0b00) or \
               (prev_state == 0b00 and curr_state == 0b10) or \
               (prev_state == 0b10 and curr_state == 0b11) or \
               (prev_state == 0b11 and curr_state == 0b01) or \
               (prev_state == 0b01 and curr_state == 0b00):
                valid_transitions += 1
            else:
                invalid_transitions += 1
        
        print(f"Valid state transitions: {valid_transitions}")
        print(f"Invalid state transitions: {invalid_transitions}")
        
        if invalid_transitions > 0:
            print("\nDetected invalid state transitions. Possible issues:")
            print("1. Noisy signals - consider adding hardware debouncing")
            print("2. Rotary encoder might be faulty")
            print("3. Polling rate might be too slow to catch all transitions")

def run():
    """Run the rotary encoder diagnostic script"""
    global args
    args = parse_args()
    
    # Apply pin swapping if requested
    if args.swap_pins:
        args.a_pin, args.b_pin = args.b_pin, args.a_pin
    
    print("Starting enhanced rotary encoder diagnostic script...")
    print(f"Using pins: A={args.a_pin}, B={args.b_pin}, SW={args.sw_pin}")
    print(f"Pin swapping: {'Enabled' if args.swap_pins else 'Disabled'}")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(args.a_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(args.b_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(args.sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Read initial states
        global last_a_state, last_b_state, last_sw_state
        last_a_state = GPIO.input(args.a_pin)
        last_b_state = GPIO.input(args.b_pin)
        last_sw_state = GPIO.input(args.sw_pin)
        
        print("Initial pin states:")
        print(f"A (Pin {args.a_pin}): {last_a_state}")
        print(f"B (Pin {args.b_pin}): {last_b_state}")
        print(f"SW (Pin {args.sw_pin}): {last_sw_state}")
        
        # Monitor pin states for a while
        monitor_pins(args.monitor_time)
        
        # Wait for user input before enabling event detection
        print("\nMonitoring phase complete. Now we'll enable event detection.")
        print("This will allow real-time tracking of encoder movements.")
        input("Press Enter to enable event detection...")
        
        # Add event detection for all pins
        GPIO.add_event_detect(args.a_pin, GPIO.BOTH, callback=pin_change_callback, bouncetime=1)
        GPIO.add_event_detect(args.b_pin, GPIO.BOTH, callback=pin_change_callback, bouncetime=1)
        GPIO.add_event_detect(args.sw_pin, GPIO.BOTH, callback=pin_change_callback, bouncetime=50)
        
        print("\nEvent detection enabled. Rotate the encoder or press the button...")
        print("You should see real-time feedback on state changes.")
        print("Press Ctrl+C to exit")
        
        # Keep the script running
        while True:
            time.sleep(0.1)
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        GPIO.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    run()