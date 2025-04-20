#!/usr/bin/env python3

"""
Display Module for Gwent
This module provides interfaces to the OLED display and LED matrix displays.
"""

import time
import threading
import os
import pathlib
import sys
import datetime
from PIL import Image, ImageDraw, ImageFont

# Add the luma.examples virtual environment to the path
sys.path.append('/home/dshanaghy/luma.examples/venv/lib/python3.11/site-packages')

from luma.core.interface.serial import spi
from luma.oled.device import ssd1306
from luma.core.render import canvas

class OLEDDisplay:
    """
    Class to handle the SSD1306 OLED display.
    Uses the SSD1306 OLED display connected via SPI.
    """
    
    def __init__(self, width=128, height=64, dc_pin=24, reset_pin=25, cs_pin=7):
        """
        Initialize the OLED display.
        
        Args:
            width (int): Display width in pixels
            height (int): Display height in pixels
            dc_pin: Data/command pin (GPIO24)
            reset_pin: Reset pin (GPIO25)
            cs_pin: Chip select pin (GPIO7/CE1)
        """
        try:
            # Initialize SPI interface
            # Using GPIO11 for SCK and GPIO10 for MOSI as per hardware specs
            self.serial = spi(device=1, port=0, gpio_DC=dc_pin, gpio_RST=reset_pin, gpio_CS=cs_pin)
            
            # Print debug information
            print(f"SPI Configuration: device=1, port=0, gpio_DC={dc_pin}, gpio_RST={reset_pin}, gpio_CS={cs_pin}")
        except Exception as e:
            print(f"Error initializing SPI interface: {e}")
            raise
        
        # Initialize SSD1306 display
        self.device = ssd1306(self.serial, width=width, height=height, rotate=0)
        self.width = self.device.width
        self.height = self.device.height
        print(f"Initialized display: SSD1306 with dimensions {self.width}x{self.height}")
        
        # Use the absolute path to the fonts directory
        self.fonts_dir = pathlib.Path("/home/dshanaghy/fonts")
        
        # If the fonts directory doesn't exist, try to find it
        if not self.fonts_dir.exists():
            self.fonts_dir = self._find_fonts_directory()
            print(f"Using fonts directory: {self.fonts_dir}")
    
    def _find_fonts_directory(self):
        """
        Find the fonts directory.
        
        Returns:
            pathlib.Path: Path to the fonts directory.
        """
        # Try to find the fonts directory in several possible locations
        possible_paths = [
            # First check the project root scripts/fonts directory
            pathlib.Path(__file__).parent.parent.parent.parent.parent / "scripts" / "fonts",  # /scripts/fonts
            # Then check other possible locations
            pathlib.Path("/home/dshanaghy/gwent/scripts/fonts"),
            pathlib.Path("/home/dshanaghy/fonts"),
            pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "scripts" / "fonts",  # /scripts/fonts (alternative path)
            pathlib.Path(__file__).parent.parent.parent / "fonts",  # /software/gwent/fonts
            pathlib.Path(__file__).parent.parent / "fonts",  # /software/gwent/gwent/fonts
            pathlib.Path(__file__).parent / "fonts",  # /software/gwent/gwent/hal/fonts
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                print(f"Found fonts directory at: {path}")
                return path
        
        # If no fonts directory is found, use the current directory
        print(f"No fonts directory found, using: {pathlib.Path(__file__).parent}")
        return pathlib.Path(__file__).parent
    
    def get_font(self, name="pixelmix.ttf", size=8):
        """
        Get a font for text rendering.
        
        Args:
            name (str): Font filename
            size (int): Font size
        
        Returns:
            PIL.ImageFont: Font object
        """
        try:
            font_path = self.fonts_dir / name
            if font_path.exists():
                return ImageFont.truetype(str(font_path), size)
            else:
                print(f"Font file not found: {font_path}")
                return ImageFont.load_default()
        except Exception as e:
            print(f"Using default font instead of {name}: {e}")
            return ImageFont.load_default()
    
    def clear(self):
        """
        Clear the display.
        """
        with canvas(self.device) as draw:
            # Draw a black rectangle to clear the display
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
        print("Display cleared")
    
    def display_text(self, text, x=0, y=0, font_name="pixelmix.ttf", font_size=8, fill="white"):
        """
        Display text on the OLED.
        
        Args:
            text (str): Text to display
            x (int): X coordinate
            y (int): Y coordinate
            font_name (str): Font filename
            font_size (int): Font size
            fill (str): Text color ("white" for white, "black" for black)
        """
        with canvas(self.device) as draw:
            try:
                font = self.get_font(font_name, font_size)
                draw.text((x, y), text, font=font, fill=fill)
                print(f"Displayed text: '{text}' using font: {font_name}")
            except Exception as e:
                print(f"Error displaying text with font {font_name}: {e}")
                # Try with default font
                draw.text((x, y), text, fill=fill)
                print(f"Displayed text: '{text}' using default font")
    
    def display_menu(self, items, selected_index=0, title=None, font_name="pixelmix.ttf", font_size=8):
        """
        Display a menu on the OLED.
        
        Args:
            items (list): List of menu items
            selected_index (int): Index of the selected item
            title (str, optional): Menu title
            font_name (str): Font filename
            font_size (int): Font size
        """
        with canvas(self.device) as draw:
            try:
                font = self.get_font(font_name, font_size)
                print(f"Using font: {font_name} for menu display")
            except Exception as e:
                print(f"Error loading font {font_name} for menu: {e}")
                # Use default font
                font = None
                print("Using default font for menu display")
            
            # Draw title if provided
            y_offset = 0
            if title:
                draw.text((0, 0), title, font=font, fill="white")
                draw.line([(0, font_size + 2), (self.width, font_size + 2)], fill="white")
                y_offset = font_size + 4
            
            # Calculate visible items
            max_items = (self.height - y_offset) // (font_size + 2)
            start_idx = max(0, min(selected_index, len(items) - max_items))
            end_idx = min(start_idx + max_items, len(items))
            
            # Draw menu items
            for i, item in enumerate(items[start_idx:end_idx], start=start_idx):
                y = y_offset + (i - start_idx) * (font_size + 2)
                
                # Highlight selected item
                if i == selected_index:
                    draw.rectangle([(0, y), (self.width, y + font_size)], outline="white", fill="white")
                    draw.text((2, y), item, font=font, fill="black")
                else:
                    draw.text((2, y), item, font=font, fill="white")
    
    def display_image(self, image_path):
        """
        Display an image on the OLED.
        
        Args:
            image_path (str): Path to the image file
        """
        try:
            # Open the image
            image = Image.open(image_path)
            # Convert to mode compatible with the display
            image = image.convert(self.device.mode)
            # Resize to fit the display
            image = image.resize((self.width, self.height))
            # Display the image
            self.device.display(image)
            print(f"Displayed image: {image_path}")
        except Exception as e:
            print(f"Error displaying image: {e}")
    
    def display_datetime(self, x=0, y=0, font_name="pixelmix.ttf", font_size=8, fill="white", format_str="%Y-%m-%d %H:%M:%S"):
        """
        Display the current datetime on the OLED.
        
        Args:
            x (int): X coordinate
            y (int): Y coordinate
            font_name (str): Font filename
            font_size (int): Font size
            fill (str): Text color ("white" for white, "black" for black)
            format_str (str): Datetime format string
        
        Returns:
            datetime.datetime: The displayed datetime
        """
        now = datetime.datetime.now()
        datetime_str = now.strftime(format_str)
        
        with canvas(self.device) as draw:
            try:
                font = self.get_font(font_name, font_size)
                draw.text((x, y), datetime_str, font=font, fill=fill)
                print(f"Displayed datetime: '{datetime_str}' using font: {font_name}")
            except Exception as e:
                print(f"Error displaying datetime with font {font_name}: {e}")
                # Try with default font
                draw.text((x, y), datetime_str, fill=fill)
                print(f"Displayed datetime: '{datetime_str}' using default font")
        
        return now
    
    def start_datetime_display(self, x=0, y=0, font_name="pixelmix.ttf", font_size=8, fill="white", format_str="%Y-%m-%d %H:%M:%S"):
        """
        Start a thread to continuously update the datetime display.
        
        Args:
            x (int): X coordinate
            y (int): Y coordinate
            font_name (str): Font filename
            font_size (int): Font size
            fill (str): Text color ("white" for white, "black" for black)
            format_str (str): Datetime format string
            
        Returns:
            threading.Thread: The datetime update thread
        """
        self._datetime_running = True
        
        # Print font directory information
        print(f"Using fonts directory: {self.fonts_dir}")
        print(f"Checking if directory exists: {self.fonts_dir.exists()}")
        if self.fonts_dir.exists():
            print(f"Directory contents: {list(self.fonts_dir.glob('*'))}")
        
        def update_datetime():
            # Check font availability once at the beginning to avoid log spam
            try:
                font_path = self.fonts_dir / font_name
                print(f"Looking for font at: {font_path}")
                if not font_path.exists():
                    print(f"Font file not found: {font_path}, will use default font for datetime display")
                else:
                    print(f"Found font file: {font_path}")
            except Exception as e:
                print(f"Will use default font for datetime display: {e}")
                
            while self._datetime_running:
                self.display_datetime(x, y, font_name, font_size, fill, format_str)
                # Sleep until the next second
                now = datetime.datetime.now()
                sleep_time = 1.0 - (now.microsecond / 1000000.0)
                time.sleep(sleep_time)
        
        self._datetime_thread = threading.Thread(target=update_datetime, daemon=True)
        self._datetime_thread.start()
        print("Started datetime display thread")
        return self._datetime_thread
    
    def stop_datetime_display(self):
        """
        Stop the datetime display thread.
        """
        if hasattr(self, '_datetime_running') and self._datetime_running:
            self._datetime_running = False
            if hasattr(self, '_datetime_thread'):
                self._datetime_thread.join(timeout=1.0)
            print("Stopped datetime display thread")
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_datetime_display()
        self.clear()
        print("Display cleaned up")