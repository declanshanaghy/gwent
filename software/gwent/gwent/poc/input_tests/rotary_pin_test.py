#!/usr/bin/env python3
"""
Test script to try different pin configurations for the rotary encoder.
This script will test multiple pin configurations to help identify the correct one.
"""

import time
import signal
import sys
import argparse
import RPi.GPIO as GPIO

# Define possible pin configurations to test
PIN_CONFIGS = [
    # Format: (A_PIN, B_PIN, SW_PIN, Description)
    (17, 22, 27, "Default configuration from rotary.py"),
    (22, 17, 27, "Swapped A/B pins from rotary_rpigpio.py"),
    (17, 27, 22, "Configuration from rotary_gpiozero.py"),
    # Add more configurations if needed
]

# Global variables
current_config = 0
counter = 0
last_a_state = None
last_b_state = None
last_sw_state = None

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting rotary encoder pin test script...")
    GPIO.cleanup()
    sys.exit(0)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Test different pin configurations for rotary encoder')
    parser.add_argument('--start-config', type=int, default=0,
                        help='Starting configuration index (default: 0)')
    return parser.parse_args()

def setup_pins(a_pin, b_pin, sw_pin):
    """Set up GPIO pins for the current configuration"""
    # Clean up any previous configuration
    GPIO.cleanup()
    
    # Set GPIO mode to BCM
    GPIO.setmode(GPIO.BCM)
    
    # Set up pins with pull-up resistors
    GPIO.setup(a_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(b_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    # Read initial states
    global last_a_state, last_b_state, last_sw_state
    last_a_state = GPIO.input(a_pin)
    last_b_state = GPIO.input(b_pin)
    last_sw_state = GPIO.input(sw_pin)
    
    # Add event detection
    GPIO.add_event_detect(a_pin, GPIO.BOTH, callback=lambda channel: pin_change_callback(channel, a_pin, b_pin, sw_pin))
    GPIO.add_event_detect(b_pin, GPIO.BOTH, callback=lambda channel: pin_change_callback(channel, a_pin, b_pin, sw_pin))
    GPIO.add_event_detect(sw_pin, GPIO.BOTH, callback=lambda channel: pin_change_callback(channel, a_pin, b_pin, sw_pin))

def pin_change_callback(channel, a_pin, b_pin, sw_pin):
    """Callback function for GPIO event detection"""
    global last_a_state, last_b_state, last_sw_state, counter
    
    # Read current pin states
    a_state = GPIO.input(a_pin)
    b_state = GPIO.input(b_pin)
    sw_state = GPIO.input(sw_pin)
    
    # Check for switch state change
    if channel == sw_pin and sw_state != last_sw_state:
        print(f"Button {'released' if sw_state else 'pressed'}")
        last_sw_state = sw_state
    
    # Check for rotation
    if channel in [a_pin, b_pin]:
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

def test_configuration(config_index):
    """Test a specific pin configuration"""
    global counter
    counter = 0
    
    a_pin, b_pin, sw_pin, description = PIN_CONFIGS[config_index]
    
    print("\n" + "=" * 60)
    print(f"Testing Configuration #{config_index}: {description}")
    print(f"A_PIN={a_pin}, B_PIN={b_pin}, SW_PIN={sw_pin}")
    print("=" * 60)
    
    # Wait for user to be ready
    print("\nPreparing to test this pin configuration.")
    input("Press Enter when ready to set up this configuration...")
    
    # Set up pins for this configuration
    setup_pins(a_pin, b_pin, sw_pin)
    
    print("Initial pin states:")
    print(f"A (Pin {a_pin}): {GPIO.input(a_pin)}")
    print(f"B (Pin {b_pin}): {GPIO.input(b_pin)}")
    print(f"SW (Pin {sw_pin}): {GPIO.input(sw_pin)}")
    
    print("\nNow test this configuration:")
    print("1. Rotate the encoder clockwise and counter-clockwise")
    print("2. Press and release the button")
    print("3. Observe if the events are detected correctly")
    print("\nPress Enter to try the next configuration or Ctrl+C to exit")
    
    # Wait for user input
    input()

def run():
    """Run the rotary encoder pin test script"""
    args = parse_args()
    
    print("Starting rotary encoder pin test script...")
    print(f"This script will test {len(PIN_CONFIGS)} different pin configurations")
    print("For each configuration, you'll test if rotation and button press are detected correctly")
    print("\nThis will help identify which pin configuration works for your hardware")
    input("Press Enter to begin testing...")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Test each configuration
        config_index = args.start_config
        while config_index < len(PIN_CONFIGS):
            test_configuration(config_index)
            config_index += 1
        
        print("\nAll configurations tested!")
        print("Did any configuration work correctly? If so, note which one.")
        input("Press Enter to continue or Ctrl+C to exit...")
        
        print("\nRecommendation: Use the configuration that worked in your application.")
        print("Press Ctrl+C to exit")
        
        # Keep the script running
        while True:
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Error: {e}")
        GPIO.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    run()