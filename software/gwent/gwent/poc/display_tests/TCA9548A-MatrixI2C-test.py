#!/usr/bin/env python3
"""
Simple test script for multiple displays using a TCA9548A I2C multiplexer.
This script will cycle through connected displays, drawing borders and text on each.
"""

import time
import signal
import sys

import qwiic_tca9548a
import board
import busio
import adafruit_is31fl3731
import adafruit_framebuf


def doit(displays, mux):
    """Run tests on all detected displays"""
    for display in displays:
        print(f"Testing display on channel {display[0]}")
        mux.disable_all()
        mux.enable_channels(display[0])

        mux.list_channels()

        matrix = display[1]
        draw_border(matrix)
        draw_text(matrix, "hello")

        time.sleep(1)

        clear(matrix)


def clear(matrix):
    matrix.fade(fade_in=500, fade_out=500, pause=1000)

    # draw a box on the matrix
    # first draw the top and bottom edges
    for x in range(matrix.width):
        for y in range(matrix.height):
            matrix.pixel(x, y, 0)


def draw_border(matrix):
    matrix.fade(fade_in=500, fade_out=500, pause=1000)

    # draw a box on the matrix
    # first draw the top and bottom edges
    for x in range(matrix.width):
        matrix.pixel(x, 0, 255)
        matrix.pixel(x, matrix.height - 1, 255)
    # now draw the left and right edges
    for y in range(matrix.height):
        matrix.pixel(0, y, 255)
        matrix.pixel(matrix.width - 1, y, 255)


def draw_text(display, text_to_show):
    """Draw text on the display using simple pixel patterns instead of fonts"""
    print(f"Drawing text pattern for '{text_to_show}'")
    
    # Simple approach - just draw a pattern instead of trying to use a font file
    frame = 0  # start with frame 0
    
    # Draw a simple pattern that represents text
    display.frame(frame, show=False)
    display.fill(0)  # Clear the display
    
    # Draw a simple pattern in the center of the display
    center_x = display.width // 2
    center_y = display.height // 2
    
    # Draw a simple pattern (like a letter 'A')
    for i in range(5):
        # Draw a triangle pattern
        display.pixel(center_x - 2 + i, center_y + 2, 50)  # Bottom line
        display.pixel(center_x - 2, center_y - i, 50)      # Left line
        display.pixel(center_x + 2, center_y - i, 50)      # Right line
        if i == 2:  # Middle line
            display.pixel(center_x - 1, center_y, 50)
            display.pixel(center_x, center_y, 50)
            display.pixel(center_x + 1, center_y, 50)
    
    # Show the frame
    display.frame(frame, show=True)


def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting display test...")
    sys.exit(0)


def run():
    """Run the display test - this is the entry point for the console script"""
    print("Starting TCA9548A Matrix I2C display test...")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Initialize Mux and i2C bus
        mux = qwiic_tca9548a.QwiicTCA9548A(address=0x70)
        print("Mux connected:", mux.is_connected())
        
        if not mux.is_connected():
            print("ERROR: TCA9548A multiplexer not found!")
            print("Check your connections and I2C configuration.")
            return
        
        i2c = busio.I2C(board.SCL, board.SDA)
        
        displays = []
        channels = [0, 7]  # Default channels to check
        
        print(f"Scanning channels: {channels}")
        for ch in channels:
            print(f"Checking channel {ch}...")
            mux.enable_channels(ch)
            try:
                display = adafruit_is31fl3731.Matrix(i2c, address=0x74)
                displays.append((ch, display))
                print(f"Display found on channel {ch}")
            except Exception as e:
                print(f"No display found on channel {ch}: {e}")
            finally:
                mux.disable_all()
        
        if not displays:
            print("No displays found! Check your connections.")
            return
            
        print(f"Found {len(displays)} display(s)")
        doit(displays, mux)
        
    except Exception as e:
        print(f"Error: {e}")
        if "No I2C device at address" in str(e):
            print("This may be because the I2C multiplexer is not connected")
            print("or the I2C interface is not enabled on your Raspberry Pi.")
            print("To enable I2C: sudo raspi-config > Interface Options > I2C > Enable")
        sys.exit(1)


if __name__ == "__main__":
    run()