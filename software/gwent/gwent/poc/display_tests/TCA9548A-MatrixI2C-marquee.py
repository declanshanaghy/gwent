#!/usr/bin/env python3
"""
Scrolling marquee script for IS31FL3731 displays using a TCA9548A I2C multiplexer.
Based on the Adafruit scrolling marquee example.
"""

import time
import signal
import sys
import math
import random
import os
import logging

import qwiic_tca9548a
import board
import busio
import adafruit_is31fl3731
from PIL import Image, ImageDraw, ImageFont

# Import gwent logging utilities
from gwent.utils.logging import configure_logging, get_logger

# Text to scroll
DEFAULT_TEXT = "GWENT"

# Font size for the pixelmix font - adjusted for the IS31FL3731 display (16x9)
FONT_SIZE = 7  # This size works well for the 16x9 display

# Path to the pixelmix font file - use absolute path to avoid "cannot open resource" error
FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         '..', '..', 'fonts', 'pixelmix.ttf'))

# Initialize logger
logger = get_logger("gwent.poc.display_tests.marquee")

def configure_stdout_logging(level=logging.INFO):
    """
    Configure logging to stdout instead of a log file.
    This is a custom version of configure_logging that redirects logs to stdout.
    
    Args:
        level (int): The log level to use
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create a formatter for the console handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create a console handler and set its formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Add the console handler to the root logger
    root_logger.addHandler(console_handler)
    
    # Set the log level
    root_logger.setLevel(level)

def load_font():
    """Load the pixelmix font"""
    # Try the main font path first
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        logger.info(f"Font loaded from {FONT_PATH}")
        return font
    except Exception as e:
        logger.warning(f"Error loading font from primary path: {e}")
        
    # If all else fails, use the default font
    logger.warning("All font paths failed, falling back to default font")
    return ImageFont.load_default()

def render_text_to_bitmap(text, font):
    # Get text dimensions
    try:
        # For newer versions of PIL
        bbox = font.getbbox(text)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        # For older versions of PIL
        text_width, text_height = font.getsize(text)
    
    # Create image with white text on black background
    image = Image.new('1', (text_width, text_height), 0)
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), text, font=font, fill=1)
    
    # Convert image to bitmap
    bitmap = []
    for y in range(image.height):
        row = []
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            row.append(pixel)
        bitmap.append(row)
    
    return bitmap, text_width, text_height

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    logger.info("Exiting marquee display...")
    # Don't use sys.exit() as it can cause issues with SSH connections
    # Instead, we'll raise a KeyboardInterrupt that will be caught in the main loop
    raise KeyboardInterrupt()

def draw_text(display, text, font, x_offset, brightness=50):
    """Draw text at the specified x offset using the pixelmix font"""
    # Clear the display first
    display.fill(0)
    
    # Load font and render text to bitmap
    bitmap, text_width, text_height = render_text_to_bitmap(text, font)
    
    # Calculate the vertical offset to center the text
    y_offset = (display.height - text_height) // 2
    if y_offset < 0:
        y_offset = 0
    
    # Draw the bitmap on the display
    for y in range(min(text_height, display.height)):
        for x in range(text_width):
            # Skip if the pixel is outside the display
            if x_offset + x < 0 or x_offset + x >= display.width:
                continue
                
            # Only draw if the pixel is lit in the bitmap and within bounds
            if y < len(bitmap) and x < len(bitmap[y]) and bitmap[y][x]:
                display.pixel(x_offset + x, y_offset + y, brightness)

def run_marquee(display, mux, channel, text=DEFAULT_TEXT, brightness=50, speed=0.1):
    """Run a scrolling marquee on the specified display"""
    # Enable the channel for this display
    mux.disable_all()
    mux.enable_channels(channel)
    
    # Load font and render text to get dimensions
    font = load_font()
    bitmap, text_width, text_height = render_text_to_bitmap(text, font)
    
    # Start with the text off the right side of the display
    x_offset = display.width
    
    try:
        # Loop until interrupted
        while True:
            # Draw the text at the current offset
            draw_text(display, text, font, x_offset, brightness)
            
            # Move the text to the left
            x_offset -= 1
            
            # If the text has scrolled completely off the left side, reset to the right
            if x_offset < -text_width:
                x_offset = display.width
                
            # Wait before the next update
            time.sleep(speed)
    except KeyboardInterrupt:
        # Clear the display when exiting
        try:
            display.fill(0)
            # Ensure the changes are visible
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        logger.info("Marquee stopped")
    finally:
        # Make sure to disable all channels when exiting
        try:
            mux.disable_all()
        except Exception as e:
            logger.error(f"Error disabling multiplexer channels: {e}")

def run(text=DEFAULT_TEXT, channel=0, brightness=50, speed=0.1, log_to_stdout=True):
    """Run the marquee display test - this is the entry point for the console script
    
    Args:
        text (str): Text to display in the marquee
        channel (int): Multiplexer channel (0-7)
        brightness (int): Brightness level (0-255)
        speed (float): Scroll speed in seconds per step
        log_to_stdout (bool): If True, logs go to stdout; if False, logs go to file
    """
    # Configure logging based on the log_to_stdout parameter
    if log_to_stdout:
        # Configure logging to stdout with our custom function
        configure_stdout_logging(level=logging.INFO)
    else:
        # Configure logging to file (default behavior)
        configure_logging(level=logging.INFO, log_file="/tmp/logs/matrix_marquee.log")
    
    logger.info("Starting TCA9548A Matrix I2C marquee display...")
    logger.info(f"Text: '{text}'")
    logger.info(f"Channel: {channel}")
    logger.info(f"Brightness: {brightness}")
    logger.info(f"Speed: {speed}")
    logger.info("Press Ctrl+C to exit")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize variables to None so we can clean up properly in finally block
    mux = None
    display = None
    
    try:
        # Initialize Mux and i2C bus
        logger.info("Initializing TCA9548A multiplexer...")
        mux = qwiic_tca9548a.QwiicTCA9548A(address=0x70)
        logger.info(f"Mux connected: {mux.is_connected()}")
        
        if not mux.is_connected():
            logger.error("TCA9548A multiplexer not found!")
            logger.error("Check your connections and I2C configuration.")
            return
        
        logger.info("Initializing I2C bus...")
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # Enable the specified channel
        logger.info(f"Enabling channel {channel}...")
        mux.disable_all()
        mux.enable_channels(channel)
        
        # Initialize the display
        logger.info("Initializing display...")
        display = adafruit_is31fl3731.IS31FL3731(i2c, address=0x74)
        
        # Run the marquee
        logger.info("Starting marquee...")
        run_marquee(display, mux, channel, text, brightness, speed)
        
    except KeyboardInterrupt:
        logger.info("Marquee stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error("Traceback: " + "".join(traceback.format_exc()))
    finally:
        # Clean up resources
        if display:
            try:
                display.fill(0)  # Clear the display
                time.sleep(0.1)  # Give it time to update
                logger.info("Display cleared")
            except Exception as e:
                logger.error(f"Error clearing display during cleanup: {e}")
                
        if mux:
            try:
                mux.disable_all()  # Disable all multiplexer channels
                logger.info("Multiplexer channels disabled")
            except Exception as e:
                logger.error(f"Error disabling multiplexer during cleanup: {e}")
                
        logger.info("Cleanup complete")

if __name__ == "__main__":
    # Parse command line arguments if provided
    import argparse
    parser = argparse.ArgumentParser(description='Run a scrolling marquee on an IS31FL3731 display')
    parser.add_argument('--text', type=str, default=DEFAULT_TEXT, help='Text to display')
    parser.add_argument('--channel', type=int, default=0, help='Multiplexer channel (0-7)')
    parser.add_argument('--brightness', type=int, default=50, help='Brightness (0-255)')
    parser.add_argument('--speed', type=float, default=0.1, help='Scroll speed (seconds per step)')
    parser.add_argument('--log-to-file', action='store_true', help='Log to file instead of stdout')
    args = parser.parse_args()
    
    # Run with log_to_stdout=True by default, unless --log-to-file is specified
    run(args.text, args.channel, args.brightness, args.speed, log_to_stdout=not args.log_to_file)