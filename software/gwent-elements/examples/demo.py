#!/usr/bin/env python3

"""
Gwent Elements Demo

This script demonstrates the usage of the gwent-elements package.
"""

import time
import asyncio
import argparse
from gwent_elements.utils.blinka import BlinkaTest
from gwent_elements.display.ssd1306 import SSD1306Display
from gwent_elements.input.rotary import RotaryEncoder


async def display_demo():
    """
    Demonstrate the SSD1306 display
    """
    print("Initializing SSD1306 display...")
    try:
        display = SSD1306Display()
        
        print("Displaying menu...")
        display.clear()
        display.menu([
            "Gwent Elements",
            "Display Demo",
            "Option 1",
            "Option 2",
            "Option 3",
        ], selected_index=1)
        
        # Wait for 5 seconds
        await asyncio.sleep(5)
        
        print("Displaying text...")
        display.clear()
        display.puts("Gwent Elements\n")
        display.puts("Display Demo\n")
        display.puts("Press Ctrl+C to exit")
        
        # Wait for 5 seconds
        await asyncio.sleep(5)
        
        print("Display demo completed.")
    except Exception as e:
        print(f"Display demo failed: {e}")


async def rotary_demo():
    """
    Demonstrate the rotary encoder
    """
    print("Initializing rotary encoder...")
    try:
        encoder = RotaryEncoder()
        
        # Set callbacks
        def on_rotation(delta):
            print(f"Rotated: {delta}, Counter: {encoder.get_counter()}")
        
        def on_switch(state):
            print(f"Switch: {'Pressed' if state == 0 else 'Released'}")
        
        encoder.set_rotation_callback(on_rotation)
        encoder.set_switch_callback(on_switch)
        
        print("Rotary encoder initialized. Turn the knob or press the button.")
        print("Press Ctrl+C to exit.")
        
        # Run for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            encoder.update()
            await asyncio.sleep(0.1)
            
        print("Rotary demo completed.")
    except Exception as e:
        print(f"Rotary demo failed: {e}")


async def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description="Gwent Elements Demo")
    parser.add_argument("--test", action="store_true", help="Run CircuitPython/Blinka tests")
    parser.add_argument("--display", action="store_true", help="Run display demo")
    parser.add_argument("--rotary", action="store_true", help="Run rotary encoder demo")
    parser.add_argument("--all", action="store_true", help="Run all demos")
    
    args = parser.parse_args()
    
    # If no arguments are provided, run all demos
    if not (args.test or args.display or args.rotary or args.all):
        args.all = True
        
    # Run CircuitPython/Blinka tests
    if args.test or args.all:
        print("\n=== CircuitPython/Blinka Tests ===")
        BlinkaTest.test_all()
        
    # Run display demo
    if args.display or args.all:
        print("\n=== Display Demo ===")
        await display_demo()
        
    # Run rotary encoder demo
    if args.rotary or args.all:
        print("\n=== Rotary Encoder Demo ===")
        await rotary_demo()
        
    print("\nDemo completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nDemo failed: {e}")