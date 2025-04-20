#!/usr/bin/env python3

"""
Display Module for Gwent
This module provides interfaces to the OLED display and LED matrix displays.
"""

import time
import threading
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import spi
from luma.oled.device import ssd1306
from luma.core.render import canvas
import os
import pathlib

class OLEDDisplay:
    """
    Class to handle the SSD1306 OLED display.
    Uses the SSD1306 OLED display connected via SPI.
    """
    
    def __init__(self, device_number=0, port=0, dc_pin=24, reset_pin=25):
        """
        Initialize the OLED display.
        
        Args:
            device_number (int): SPI device number
            port (int): SPI port number
            dc_pin (int): GPIO pin for data/command signal
            reset_pin (int): GPIO pin for reset signal
        """
        self.serial = spi(device=device_number, port=port, gpio_DC=dc_pin, gpio_RST=reset_pin)
        self.device = ssd1306(self.serial)
        self.width = self.device.width
        self.height = self.device.height
        
        # Find the fonts directory
        self.fonts_dir = self._find_fonts_directory()
    
    def _find_fonts_directory(self):
        """
        Find the fonts directory.
        
        Returns:
            pathlib.Path: Path to the fonts directory.
        """
        # Try to find the fonts directory in several possible locations
        possible_paths = [
            pathlib.Path(__file__).parent.parent.parent.parent.parent / "poc" / "fonts",  # /software/poc/fonts
            pathlib.Path(__file__).parent.parent.parent / "fonts",  # /software/gwent/fonts
            pathlib.Path(__file__).parent.parent / "fonts",  # /software/gwent/gwent/fonts
            pathlib.Path(__file__).parent / "fonts",  # /software/gwent/gwent/hal/fonts
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                return path
        
        # If no fonts directory is found, use the current directory
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
            return ImageFont.truetype(str(font_path), size)
        except Exception as e:
            print(f"Error loading font {name}: {e}")
            return ImageFont.load_default()
    
    def clear(self):
        """
        Clear the display.
        """
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
    
    def display_text(self, text, x=0, y=0, font_name="pixelmix.ttf", font_size=8, fill="white"):
        """
        Display text on the OLED.
        
        Args:
            text (str): Text to display
            x (int): X coordinate
            y (int): Y coordinate
            font_name (str): Font filename
            font_size (int): Font size
            fill (str): Text color
        """
        with canvas(self.device) as draw:
            font = self.get_font(font_name, font_size)
            draw.text((x, y), text, font=font, fill=fill)
    
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
            font = self.get_font(font_name, font_size)
            
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
            image = Image.open(image_path).convert(self.device.mode)
            image = image.resize((self.width, self.height))
            self.device.display(image)
        except Exception as e:
            print(f"Error displaying image: {e}")
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.clear()