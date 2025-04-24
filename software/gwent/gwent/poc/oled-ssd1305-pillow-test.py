#!/usr/bin/env python3

"""
This demo will fill the screen with white, draw a black box on top
and then print Hello World! in the center of the display

This example is for use on (Linux) computers that are using CPython with
Adafruit Blinka to support CircuitPython libraries. CircuitPython does
not support PIL/pillow (python imaging library)!
"""

import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1305
import signal
import sys
import time

# Define constants
WIDTH = 128
HEIGHT = 64  # Change to 32 if needed
BORDER = 8

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting OLED SSD1305 Pillow test...")
    sys.exit(0)

def run():
    """Run the OLED SSD1305 test with Pillow"""
    print("Starting OLED SSD1305 test using Adafruit CircuitPython and Pillow...")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Define the Reset Pin
        oled_reset = digitalio.DigitalInOut(board.D25)
        
        # Use for SPI
        spi = board.SPI()
        # oled_cs = digitalio.DigitalInOut(board.D8)  # CE0
        oled_cs = digitalio.DigitalInOut(board.D7)    # CE1
        # oled_cs = digitalio.DigitalInOut(board.D21) # random pin
        oled_dc = digitalio.DigitalInOut(board.D24)
        oled = adafruit_ssd1305.SSD1305_SPI(WIDTH, HEIGHT, spi, oled_dc, oled_reset, oled_cs)
        
        print("SSD1305 OLED display initialized successfully")
        
        # Clear display.
        oled.fill(0)
        oled.show()
        
        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        image = Image.new("1", (oled.width, oled.height))
        
        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)
        
        # Draw a white background
        draw.rectangle((0, 0, oled.width, oled.height), outline=255, fill=255)
        
        # Draw a smaller inner rectangle
        draw.rectangle(
            (BORDER, BORDER, oled.width - BORDER - 1, oled.height - BORDER - 1),
            outline=0,
            fill=0,
        )
        
        # Load default font.
        font = ImageFont.load_default()
        
        # Draw Some Text
        text = "Hello World 3"
        (font_width, font_height) = font.getsize(text)
        draw.text(
            (oled.width // 2 - font_width // 2, oled.height // 2 - font_height // 2),
            text,
            font=font,
            fill=255,
        )
        
        # Display image
        oled.image(image)
        oled.show()
        
        print("Image displayed successfully")
        print("Display will remain active until Ctrl+C is pressed")
        
        # Keep the display on until interrupted
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()