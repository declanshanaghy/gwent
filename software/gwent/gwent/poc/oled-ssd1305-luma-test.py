#!/usr/bin/env python3

"""
This demo will fill the screen with white, draw a black box on top
and then print Hello World! in the center of the display

This version uses the luma.oled library instead of Adafruit CircuitPython
"""

from time import sleep
import signal
import sys

from luma.core.interface.serial import spi
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

# Define the dimensions
WIDTH = 128
HEIGHT = 64
BORDER = 8

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    print("\nExiting OLED SSD1305 Luma test...")
    sys.exit(0)

def run():
    """Run the OLED SSD1305 test with luma.oled"""
    print("Starting OLED SSD1305 test using luma.oled with SSD1306 driver...")
    print("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Use for SPI
        serial = spi(device=1, port=0)
        device = ssd1306(serial)
        
        print("SSD1306 driver initialized successfully for SSD1305 display")
        
        # Clear display
        device.clear()
        
        # Create blank image for drawing
        # Make sure to create image with mode '1' for 1-bit color
        image = Image.new("1", (device.width, device.height))
        
        # Get drawing object to draw on image
        draw = ImageDraw.Draw(image)
        
        # Draw a white background
        draw.rectangle((0, 0, device.width, device.height), outline=255, fill=255)
        
        # Draw a smaller inner rectangle
        draw.rectangle(
            (BORDER, BORDER, device.width - BORDER - 1, device.height - BORDER - 1),
            outline=0,
            fill=0,
        )
        
        # Load default font
        font = ImageFont.load_default()
        
        # Draw Some Text
        text = "Hello World 3"
        # Use getbbox() instead of deprecated getsize()
        bbox = font.getbbox(text)
        font_width = bbox[2] - bbox[0]
        font_height = bbox[3] - bbox[1]
        draw.text(
            (device.width // 2 - font_width // 2, device.height // 2 - font_height // 2),
            text,
            font=font,
            fill=255,
        )
        
        # Display image
        device.display(image)
        
        print("Image displayed successfully")
        print("Display will remain active until Ctrl+C is pressed")
        
        # Keep the display on until interrupted
        while True:
            sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()