#!/usr/bin/env python3

"""
Gwent Elements Mock Demo

This script demonstrates the usage of the gwent-elements package without requiring actual hardware.
It mocks the hardware interfaces to show how the API would be used.
"""

import time
import asyncio
import argparse


class MockDisplay:
    """Mock display for demonstration purposes"""
    
    def __init__(self):
        print("Initializing mock display...")
        
    def clear(self):
        print("Clearing display")
        
    def menu(self, items, selected_index=0):
        print("\n=== DISPLAY MENU ===")
        for i, item in enumerate(items):
            prefix = "> " if i == selected_index else "  "
            print(f"{prefix}{item}")
        print("===================\n")
        
    def puts(self, text):
        print(f"DISPLAY: {text}", end="")


class MockRotaryEncoder:
    """Mock rotary encoder for demonstration purposes"""
    
    def __init__(self):
        print("Initializing mock rotary encoder...")
        self.counter = 0
        self.rotation_callback = None
        self.switch_callback = None
        
    def get_counter(self):
        return self.counter
        
    def set_counter(self, value):
        self.counter = value
        
    def set_rotation_callback(self, callback):
        self.rotation_callback = callback
        
    def set_switch_callback(self, callback):
        self.switch_callback = callback
        
    def update(self):
        # Simulate random rotary events
        import random
        if random.random() < 0.2:  # 20% chance of rotation
            delta = random.choice([-1, 1])
            self.counter += delta
            if self.rotation_callback:
                self.rotation_callback(delta)
                
        # Simulate random switch events
        if random.random() < 0.1:  # 10% chance of switch press/release
            state = random.choice([0, 1])
            if self.switch_callback:
                self.switch_callback(state)
                
        return (0, False, 1)  # Default return values


class MockBlinkaTest:
    """Mock CircuitPython/Blinka test for demonstration purposes"""
    
    @staticmethod
    def test_digital_io():
        print("Testing digital I/O... OK!")
        return True
        
    @staticmethod
    def test_i2c():
        print("Testing I2C... OK!")
        return True
        
    @staticmethod
    def test_spi():
        print("Testing SPI... OK!")
        return True
        
    @classmethod
    def test_all(cls):
        print("\n=== CircuitPython/Blinka Tests (MOCK) ===")
        cls.test_digital_io()
        cls.test_i2c()
        cls.test_spi()
        print("All tests passed!")
        return True


async def display_demo():
    """
    Demonstrate the display
    """
    print("Initializing display...")
    try:
        display = MockDisplay()
        
        print("Displaying menu...")
        display.clear()
        display.menu([
            "Gwent Elements",
            "Display Demo",
            "Option 1",
            "Option 2",
            "Option 3",
        ], selected_index=1)
        
        # Wait for 2 seconds
        await asyncio.sleep(2)
        
        print("Displaying text...")
        display.clear()
        display.puts("Gwent Elements\n")
        display.puts("Display Demo\n")
        display.puts("Press Ctrl+C to exit\n")
        
        # Wait for 2 seconds
        await asyncio.sleep(2)
        
        print("Display demo completed.")
    except Exception as e:
        print(f"Display demo failed: {e}")


async def rotary_demo():
    """
    Demonstrate the rotary encoder
    """
    print("Initializing rotary encoder...")
    try:
        encoder = MockRotaryEncoder()
        
        # Set callbacks
        def on_rotation(delta):
            print(f"Rotated: {delta}, Counter: {encoder.get_counter()}")
        
        def on_switch(state):
            print(f"Switch: {'Pressed' if state == 0 else 'Released'}")
        
        encoder.set_rotation_callback(on_rotation)
        encoder.set_switch_callback(on_switch)
        
        print("Rotary encoder initialized. Simulating rotary events...")
        print("Press Ctrl+C to exit.")
        
        # Run for 10 seconds
        start_time = time.time()
        while time.time() - start_time < 10:
            encoder.update()
            await asyncio.sleep(0.1)
            
        print("Rotary demo completed.")
    except Exception as e:
        print(f"Rotary demo failed: {e}")


async def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description="Gwent Elements Mock Demo")
    parser.add_argument("--test", action="store_true", help="Run mock CircuitPython/Blinka tests")
    parser.add_argument("--display", action="store_true", help="Run mock display demo")
    parser.add_argument("--rotary", action="store_true", help="Run mock rotary encoder demo")
    parser.add_argument("--all", action="store_true", help="Run all mock demos")
    
    args = parser.parse_args()
    
    # If no arguments are provided, run all demos
    if not (args.test or args.display or args.rotary or args.all):
        args.all = True
        
    # Run CircuitPython/Blinka tests
    if args.test or args.all:
        MockBlinkaTest.test_all()
        
    # Run display demo
    if args.display or args.all:
        print("\n=== Display Demo (MOCK) ===")
        await display_demo()
        
    # Run rotary encoder demo
    if args.rotary or args.all:
        print("\n=== Rotary Encoder Demo (MOCK) ===")
        await rotary_demo()
        
    print("\nMock demo completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nDemo failed: {e}")