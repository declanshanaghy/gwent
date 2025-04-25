#!/usr/bin/env python3
"""
Rotary encoder implementation using pigpio.
This script uses the pigpio library which can work alongside other GPIO services
and is often pre-installed on Raspberry Pi OS.
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
logger = logging.getLogger("rotary_pigpio")

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
    print("\nExiting pigpio rotary encoder test...")
    if 'pi' in globals():
        pi.stop()
    sys.exit(0)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='PIGPIO rotary encoder test')
    parser.add_argument('--a-pin', type=int, default=DEFAULT_A_PIN,
                        help=f'BCM pin number for A signal (default: {DEFAULT_A_PIN})')
    parser.add_argument('--b-pin', type=int, default=DEFAULT_B_PIN,
                        help=f'BCM pin number for B signal (default: {DEFAULT_B_PIN})')
    parser.add_argument('--sw-pin', type=int, default=DEFAULT_SW_PIN,
                        help=f'BCM pin number for switch (default: {DEFAULT_SW_PIN})')
    parser.add_argument('--swap-pins', action='store_true',
                        help='Swap A and B pins to test direction issues')
    parser.add_argument('--host', type=str, default='localhost',
                        help='pigpiod host (default: localhost)')
    parser.add_argument('--port', type=int, default=8888,
                        help='pigpiod port (default: 8888)')
    return parser.parse_args()

class RotaryEncoder:
    """A class to decode mechanical rotary encoder pulses using pigpio."""
    
    def __init__(self, pi, a_pin, b_pin, callback=None):
        """
        Initialize the rotary encoder.
        
        Args:
            pi: pigpio instance
            a_pin: The pin number for the A signal
            b_pin: The pin number for the B signal
            callback: Optional callback function to be called when rotation is detected
        """
        self.pi = pi
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.callback = callback
        
        self.last_gpio = None
        self.counter = 0
        self.direction = None
        
        # Set up pins as inputs with pull-up resistors
        self.pi.set_mode(a_pin, pigpio.INPUT)
        self.pi.set_mode(b_pin, pigpio.INPUT)
        self.pi.set_pull_up_down(a_pin, pigpio.PUD_UP)
        self.pi.set_pull_up_down(b_pin, pigpio.PUD_UP)
        
        # Set up callbacks for both pins
        self.cb_a = self.pi.callback(a_pin, pigpio.EITHER_EDGE, self._pulse)
        self.cb_b = self.pi.callback(b_pin, pigpio.EITHER_EDGE, self._pulse)
        
        # Initialize state
        self.levA = self.pi.read(a_pin)
        self.levB = self.pi.read(b_pin)
        self.lastGpio = None
    
    def _pulse(self, gpio, level, tick):
        """
        Decode the rotary encoder pulse.
        
        Args:
            gpio: The GPIO that changed state
            level: The new level
            tick: The timestamp of the change
        """
        if gpio == self.a_pin:
            self.levA = level
        else:
            self.levB = level
        
        if gpio != self.lastGpio:  # Debounce
            self.lastGpio = gpio
            
            if gpio == self.a_pin and level == 1:
                if self.levB == 1:
                    self.counter += 1
                    self.direction = 1
                    if self.callback:
                        self.callback(1)
            elif gpio == self.b_pin and level == 1:
                if self.levA == 1:
                    self.counter -= 1
                    self.direction = -1
                    if self.callback:
                        self.callback(-1)
    
    def get_counter(self):
        """Get the current counter value"""
        return self.counter
    
    def get_direction(self):
        """Get the last direction of rotation"""
        return self.direction
    
    def reset(self):
        """Reset the counter to 0"""
        self.counter = 0
        self.direction = None
    
    def cancel(self):
        """Cancel the callbacks"""
        self.cb_a.cancel()
        self.cb_b.cancel()

class Switch:
    """A simple switch class using pigpio."""
    
    def __init__(self, pi, pin):
        """
        Initialize the switch.
        
        Args:
            pi: pigpio instance
            pin: The pin number for the switch
        """
        self.pi = pi
        self.pin = pin
        
        # Set up pin as input with pull-up resistor
        self.pi.set_mode(pin, pigpio.INPUT)
        self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
        
        # Set up callback for the pin
        self.cb = self.pi.callback(pin, pigpio.EITHER_EDGE, self._pulse)
        
        # Initialize state
        self.state = self.pi.read(pin)
        self.last_state = self.state
    
    def _pulse(self, gpio, level, tick):
        """
        Update the switch state.
        
        Args:
            gpio: The GPIO that changed state
            level: The new level
            tick: The timestamp of the change
        """
        self.state = level
    
    def get_state(self):
        """Get the current state of the switch (True = pressed, False = released)"""
        # Switch is pulled up, so it's LOW when pressed
        return not self.state
    
    def cancel(self):
        """Cancel the callback"""
        self.cb.cancel()

def rotation_callback(direction):
    """Callback function for rotary encoder rotation"""
    global counter
    counter += direction
    print(f"Rotation detected: direction={direction}, counter={counter}")

def run():
    """Run the pigpio rotary encoder test"""
    global counter, last_a_state, last_b_state, last_sw_state, pi
    args = parse_args()
    
    # Apply pin swapping if requested
    a_pin = args.b_pin if args.swap_pins else args.a_pin
    b_pin = args.a_pin if args.swap_pins else args.b_pin
    sw_pin = args.sw_pin
    
    print("Starting pigpio rotary encoder test...")
    print(f"Using pins: A={a_pin}, B={b_pin}, SW={sw_pin}")
    print(f"Pin swapping: {'Enabled' if args.swap_pins else 'Disabled'}")
    print(f"Connecting to pigpiod at {args.host}:{args.port}")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # First, try to import pigpio
        try:
            import pigpio
            globals()['pigpio'] = pigpio
        except ImportError:
            print("\nERROR: pigpio library not found.")
            print("This script requires the pigpio library, which is often pre-installed on Raspberry Pi OS.")
            print("If it's not installed, you can install it with:")
            print("sudo apt-get update")
            print("sudo apt-get install -y pigpio python3-pigpio")
            print("sudo systemctl start pigpiod")
            sys.exit(1)
        
        print("\nInitializing rotary encoder with pigpio...")
        print("This approach can work alongside other GPIO services.")
        input("Press Enter to continue...")
        
        # Connect to the pigpio daemon
        pi = pigpio.pi(args.host, args.port)
        if not pi.connected:
            print("\nERROR: Could not connect to pigpio daemon.")
            print("Make sure the pigpio daemon is running with:")
            print("sudo systemctl start pigpiod")
            sys.exit(1)
        
        # Initialize the rotary encoder and switch
        encoder = RotaryEncoder(pi, a_pin, b_pin, callback=rotation_callback)
        switch = Switch(pi, sw_pin)
        
        print("Initial switch state:", "Pressed" if switch.get_state() else "Released")
        
        print("\nRotary encoder initialized successfully")
        print("Waiting for events... (rotate the encoder or press the button)")
        
        # Main loop
        last_switch_state = switch.get_state()
        while True:
            # Check for switch state change
            switch_state = switch.get_state()
            if switch_state != last_switch_state:
                print(f"Button {'pressed' if switch_state else 'released'}")
                last_switch_state = switch_state
            
            # Sleep to avoid high CPU usage
            time.sleep(0.05)
            
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nThis error might be caused by GPIO pin conflicts or permission issues.")
        print("Try the following:")
        print("1. Make sure the pigpio daemon is running:")
        print("   sudo systemctl start pigpiod")
        print("2. Try different pins:")
        print(f"   python3 -m gwent.poc.input_tests.rotary_pigpio --a-pin 5 --b-pin 6 --sw-pin 13")
        print("3. Check if the pigpio library is installed and working:")
        print("   python3 -c 'import pigpio; print(\"pigpio version:\", pigpio.version)'")
        sys.exit(1)
    finally:
        # Clean up
        if 'pi' in locals() and pi.connected:
            if 'encoder' in locals():
                encoder.cancel()
            if 'switch' in locals():
                switch.cancel()
            pi.stop()

if __name__ == "__main__":
    run()