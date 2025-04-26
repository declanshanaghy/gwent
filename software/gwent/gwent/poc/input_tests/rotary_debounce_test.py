#!/usr/bin/env python3
"""
Test script to experiment with different debouncing settings for the rotary encoder.
This script will test different debouncing configurations to help identify the optimal settings.
"""

import time
import signal
import sys
import argparse
import RPi.GPIO as GPIO

# Default BCM pin numbers
DEFAULT_A_PIN = 17  # BCM pin 17
DEFAULT_B_PIN = 22  # BCM pin 22
DEFAULT_SW_PIN = 27  # BCM pin 27

# Global variables
counter = 0
last_a_state = None
last_b_state = None
last_sw_state = None
last_rotation_time = 0
rotation_events = []

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting rotary encoder debounce test script...")
    
    # Print statistics
    if rotation_events:
        intervals = [rotation_events[i] - rotation_events[i-1] for i in range(1, len(rotation_events))]
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)
            print(f"\nRotation event statistics:")
            print(f"Total events: {len(rotation_events)}")
            print(f"Average interval: {avg_interval:.6f} seconds")
            print(f"Minimum interval: {min_interval:.6f} seconds")
            print(f"Maximum interval: {max_interval:.6f} seconds")
    
    GPIO.cleanup()
    sys.exit(0)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Test different debouncing settings for rotary encoder')
    parser.add_argument('--a-pin', type=int, default=DEFAULT_A_PIN,
                        help=f'BCM pin number for A signal (default: {DEFAULT_A_PIN})')
    parser.add_argument('--b-pin', type=int, default=DEFAULT_B_PIN,
                        help=f'BCM pin number for B signal (default: {DEFAULT_B_PIN})')
    parser.add_argument('--sw-pin', type=int, default=DEFAULT_SW_PIN,
                        help=f'BCM pin number for switch (default: {DEFAULT_SW_PIN})')
    parser.add_argument('--bounce-time', type=int, default=0,
                        help='Bounce time in ms for rotation detection (default: 0)')
    parser.add_argument('--sw-bounce-time', type=int, default=50,
                        help='Bounce time in ms for switch detection (default: 50)')
    parser.add_argument('--min-interval', type=float, default=0.0,
                        help='Minimum interval between rotation events in seconds (default: 0.0)')
    return parser.parse_args()

def pin_change_callback(channel):
    """Callback function for GPIO event detection"""
    global last_a_state, last_b_state, last_sw_state, counter, last_rotation_time, rotation_events
    
    # Read current pin states
    a_state = GPIO.input(args.a_pin)
    b_state = GPIO.input(args.b_pin)
    sw_state = GPIO.input(args.sw_pin)
    
    # Check for switch state change
    if channel == args.sw_pin and sw_state != last_sw_state:
        print(f"Button {'released' if sw_state else 'pressed'}")
        last_sw_state = sw_state
    
    # Check for rotation
    if channel in [args.a_pin, args.b_pin]:
        current_time = time.time()
        
        # Apply software debouncing if min_interval is set
        if args.min_interval > 0 and current_time - last_rotation_time < args.min_interval:
            return
        
        if last_a_state is not None and last_b_state is not None:
            # State transition table for clockwise rotation:
            # 00 -> 01 -> 11 -> 10 -> 00
            # For counter-clockwise, the sequence is reversed
            
            last_state = (last_a_state << 1) | last_b_state
            current_state = (a_state << 1) | b_state
            
            # Check for valid state transitions
            direction = None
            if (last_state == 0b00 and current_state == 0b01) or \
               (last_state == 0b01 and current_state == 0b11) or \
               (last_state == 0b11 and current_state == 0b10) or \
               (last_state == 0b10 and current_state == 0b00):
                direction = 1  # Clockwise
                if current_state == 0b00:  # Complete rotation
                    counter += 1
                    print(f"Clockwise rotation detected: {counter}")
                    rotation_events.append(current_time)
                    last_rotation_time = current_time
            elif (last_state == 0b00 and current_state == 0b10) or \
                 (last_state == 0b10 and current_state == 0b11) or \
                 (last_state == 0b11 and current_state == 0b01) or \
                 (last_state == 0b01 and current_state == 0b00):
                direction = -1  # Counter-clockwise
                if current_state == 0b00:  # Complete rotation
                    counter -= 1
                    print(f"Counter-clockwise rotation detected: {counter}")
                    rotation_events.append(current_time)
                    last_rotation_time = current_time
            
            # Print detailed state information
            if direction is not None:
                print(f"  State transition: {bin(last_state)[2:].zfill(2)} -> {bin(current_state)[2:].zfill(2)}")
    
    # Update last states
    last_a_state = a_state
    last_b_state = b_state

def run():
    """Run the rotary encoder debounce test script"""
    global args, last_a_state, last_b_state, last_sw_state
    args = parse_args()
    
    print("Starting rotary encoder debounce test script...")
    print(f"Using pins: A={args.a_pin}, B={args.b_pin}, SW={args.sw_pin}")
    print(f"Bounce time for rotation: {args.bounce_time} ms")
    print(f"Bounce time for switch: {args.sw_bounce_time} ms")
    print(f"Minimum interval between events: {args.min_interval} seconds")
    
    print("\nThis test will help identify optimal debouncing settings.")
    print("We'll monitor how the encoder responds with the current settings.")
    input("Press Enter when ready to begin setup...")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Initialize GPIO
        print("\nInitializing GPIO pins...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(args.a_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(args.b_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(args.sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Read initial states
        last_a_state = GPIO.input(args.a_pin)
        last_b_state = GPIO.input(args.b_pin)
        last_sw_state = GPIO.input(args.sw_pin)
        
        print("Initial pin states:")
        print(f"A (Pin {args.a_pin}): {last_a_state}")
        print(f"B (Pin {args.b_pin}): {last_b_state}")
        print(f"SW (Pin {args.sw_pin}): {last_sw_state}")
        
        print("\nNow we'll set up event detection with the specified debounce settings.")
        print("This will help determine if the current settings work well.")
        input("Press Enter to enable event detection...")
        
        # Add event detection for all pins
        GPIO.add_event_detect(args.a_pin, GPIO.BOTH, callback=pin_change_callback, bouncetime=args.bounce_time)
        GPIO.add_event_detect(args.b_pin, GPIO.BOTH, callback=pin_change_callback, bouncetime=args.bounce_time)
        GPIO.add_event_detect(args.sw_pin, GPIO.BOTH, callback=pin_change_callback, bouncetime=args.sw_bounce_time)
        
        print("\nEvent detection enabled with the following settings:")
        print(f"- Rotation bounce time: {args.bounce_time} ms")
        print(f"- Switch bounce time: {args.sw_bounce_time} ms")
        print(f"- Minimum interval: {args.min_interval} seconds")
        print("\nNow test the encoder by rotating it slowly and pressing the button.")
        print("Observe if there are any false readings or missed detections.")
        print("Press Ctrl+C to exit and see statistics")
        
        # Keep the script running
        while True:
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Error: {e}")
        GPIO.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    run()