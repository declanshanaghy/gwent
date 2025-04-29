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


def doit(displays, mux):
    """Run tests on all detected displays"""
    for display in displays:
        channel = display[0]
        matrix = display[1]
        
        try:
            print(f"\n=== Testing display on channel {channel} ===")
            print(f"Display type: {type(matrix).__name__}")
            print(f"Display dimensions: {matrix.width}x{matrix.height}")
            
            # Disable all channels and enable only the current one
            print(f"Disabling all channels and enabling channel {channel}")
            mux.disable_all()
            mux.enable_channels(channel)
            
            # List active channels
            print("Active channels:")
            mux.list_channels()
            
            # Draw border
            print("Drawing border...")
            try:
                draw_border(matrix)
                print("Border drawn successfully")
            except Exception as e:
                print(f"Error drawing border: {e}")
            
            # Draw text
            print("Drawing text...")
            try:
                draw_text(matrix, "hello")
                print("Text drawn successfully")
            except Exception as e:
                print(f"Error drawing text: {e}")
            
            # Wait to observe the display
            print("Waiting for 1 second...")
            time.sleep(1)
            
            # Clear the display
            print("Clearing display...")
            try:
                clear(matrix)
                print("Display cleared successfully")
            except Exception as e:
                print(f"Error clearing display: {e}")
                
            print(f"=== Completed test for display on channel {channel} ===\n")
            
        except Exception as e:
            print(f"Error testing display on channel {channel}: {e}")
            import traceback
            traceback.print_exc()


def clear(matrix):
    """Clear the display by setting all pixels to 0"""
    try:
        print("  Starting fade effect for clear...")
        try:
            # Fix the fade parameters to avoid "Pause out of range" error
            matrix.fade(fade_in=100, fade_out=100, pause=100)
        except AttributeError:
            print("  Fade not supported by this display, skipping")
        except Exception as e:
            print(f"  Error during fade: {e}")

        # Clear all pixels on the matrix
        print(f"  Clearing all pixels ({matrix.width}x{matrix.height})...")
        for x in range(matrix.width):
            for y in range(matrix.height):
                matrix.pixel(x, y, 0)
        print("  Display cleared successfully")
    except Exception as e:
        print(f"  Error clearing display: {e}")
        import traceback
        traceback.print_exc()


def draw_border(matrix):
    """Draw a border around the edge of the display"""
    try:
        print("  Starting fade effect for border...")
        try:
            # Fix the fade parameters to avoid "Pause out of range" error
            matrix.fade(fade_in=100, fade_out=100, pause=100)
        except AttributeError:
            print("  Fade not supported by this display, skipping")
        except Exception as e:
            print(f"  Error during fade: {e}")

        # Draw a box on the matrix
        print(f"  Drawing border on {matrix.width}x{matrix.height} display...")
        
        # First draw the top and bottom edges
        print("  Drawing top and bottom edges...")
        for x in range(matrix.width):
            matrix.pixel(x, 0, 255)
            matrix.pixel(x, matrix.height - 1, 255)
            
        # Now draw the left and right edges
        print("  Drawing left and right edges...")
        for y in range(matrix.height):
            matrix.pixel(0, y, 255)
            matrix.pixel(matrix.width - 1, y, 255)
            
        print("  Border drawn successfully")
    except Exception as e:
        print(f"  Error drawing border: {e}")
        import traceback
        traceback.print_exc()


def draw_text(display, text_to_show):
    """Draw text on the display using simple pixel patterns instead of fonts"""
    try:
        print(f"  Drawing text pattern for '{text_to_show}'")
        
        # Simple approach - just draw a pattern instead of trying to use a font file
        frame = 0  # start with frame 0
        
        # Draw a simple pattern that represents text
        print("  Setting up frame...")
        try:
            display.frame(frame, show=False)
        except AttributeError:
            print("  Frame method not supported by this display, continuing anyway")
        except Exception as e:
            print(f"  Error setting frame: {e}")
            
        print("  Clearing display...")
        try:
            display.fill(0)  # Clear the display
        except AttributeError:
            print("  Fill method not supported by this display, clearing manually")
            for x in range(display.width):
                for y in range(display.height):
                    display.pixel(x, y, 0)
        except Exception as e:
            print(f"  Error clearing display: {e}")
        
        # Draw a simple pattern in the center of the display
        center_x = display.width // 2
        center_y = display.height // 2
        
        print(f"  Drawing pattern at center ({center_x}, {center_y})...")
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
        print("  Showing frame...")
        try:
            display.frame(frame, show=True)
        except AttributeError:
            print("  Frame method not supported by this display, continuing anyway")
        except Exception as e:
            print(f"  Error showing frame: {e}")
            
        print("  Text pattern drawn successfully")
    except Exception as e:
        print(f"  Error drawing text: {e}")
        import traceback
        traceback.print_exc()


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
    
    # Print basic library information
    print("\nLibrary information:")
    print(f"Python version: {sys.version.split()[0]}")
    print(f"adafruit_is31fl3731 version: {getattr(adafruit_is31fl3731, '__version__', 'unknown')}")
    print("")
    
    try:
        # Initialize Mux and i2C bus
        print("Initializing TCA9548A multiplexer...")
        mux = qwiic_tca9548a.QwiicTCA9548A(address=0x70)
        print("Mux connected:", mux.is_connected())
        
        if not mux.is_connected():
            print("ERROR: TCA9548A multiplexer not found!")
            print("Check your connections and I2C configuration.")
            return
        
        print("Initializing I2C bus...")
        i2c = busio.I2C(board.SCL, board.SDA)
        
        displays = []
        channels = [0, 7]  # Default channels to check
        
        print(f"Scanning channels: {channels}")
        for ch in channels:
            print(f"Checking channel {ch}...")
            mux.enable_channels(ch)
            try:
                print(f"Initializing display on channel {ch}...")
                
                # Use the correct IS31FL3731 class directly
                try:
                    display = adafruit_is31fl3731.IS31FL3731(i2c, address=0x74)
                    displays.append((ch, display))
                    print(f"Display found on channel {ch}")
                except Exception as e:
                    print(f"No display found on channel {ch}: {e}")
            except Exception as e:
                print(f"Unexpected error on channel {ch}: {e}")
            finally:
                print(f"Disabling all channels after checking channel {ch}")
                mux.disable_all()
        
        if not displays:
            print("No displays found! Check your connections.")
            print("Troubleshooting steps:")
            print("1. Check that the TCA9548A multiplexer is properly connected")
            print("2. Verify that the matrix displays are connected to the correct channels")
            print("3. Ensure I2C is enabled on your Raspberry Pi (sudo raspi-config)")
            print("4. Check that the adafruit-circuitpython-is31fl3731 library is installed")
            print("   Run: pip install adafruit-circuitpython-is31fl3731")
            return
            
        print(f"Found {len(displays)} display(s)")
        doit(displays, mux)
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("Traceback:")
        traceback.print_exc()
        
        if "No I2C device at address" in str(e):
            print("\nThis may be because the I2C multiplexer is not connected")
            print("or the I2C interface is not enabled on your Raspberry Pi.")
            print("To enable I2C: sudo raspi-config > Interface Options > I2C > Enable")
        
        print("\nTroubleshooting steps:")
        print("1. Check all hardware connections")
        print("2. Verify that the required libraries are installed:")
        print("   - pip install adafruit-circuitpython-is31fl3731")
        print("   - pip install sparkfun-qwiic-tca9548a")
        print("3. Check I2C is enabled: sudo raspi-config")
        print("4. Try running i2cdetect -y 1 to see available I2C devices")
        sys.exit(1)


if __name__ == "__main__":
    run()