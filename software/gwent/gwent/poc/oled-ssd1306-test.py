#!/usr/bin/env python3
"""
Simple test script for SSD1306 OLED display using luma.oled library.
This script will display some text on the OLED display.
"""

from time import sleep
import signal
import sys

from luma.core.interface.serial import spi
from luma.oled.device import ssd1306

from pathlib import Path
from luma.core.virtual import terminal
from PIL import ImageFont


def make_font(name, size):
    font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
    return ImageFont.truetype(font_path, size)


def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting OLED SSD1306 test...")
    sys.exit(0)


def run():
    """Run the OLED SSD1306 test"""
    print("Starting OLED SSD1306 test using luma.oled...")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        interface = spi(device=1, port=0)
        device = ssd1306(interface)
        
        font = make_font("pixelmix.ttf", 8)
        term = terminal(device, font)
        
        print("SSD1306 OLED display initialized successfully")
        print("Displaying test text...")
        
        term.puts("  Thing One\n")
        term.puts("> Thingotwo\n")
        term.puts("  Third Thing\n")
        term.puts("  Here's the fourth\n")
        term.puts("  Another fifth\n")
        term.puts("  Sixth is the best\n")
        
        print("Text displayed successfully")
        print("Display will remain active until Ctrl+C is pressed")
        
        # Keep the display on until interrupted
        while True:
            sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()