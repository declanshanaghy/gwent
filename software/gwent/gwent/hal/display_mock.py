#!/usr/bin/env python3

"""
Mock Display Module for Gwent
This module provides a mock implementation of the OLED display for development on non-Raspberry Pi systems.
"""

import time
import pathlib
import threading
import datetime
from PIL import Image, ImageDraw, ImageFont

class MockOLEDDisplay:
    """
    Mock class to simulate the SSD1306 OLED display.
    """
    
    def __init__(self, device_number=0, port=0, dc_pin=24, reset_pin=25):
        """
        Initialize the mock OLED display.
        
        Args:
            device_number (int): SPI device number (not used in mock)
            port (int): SPI port number (not used in mock)
            dc_pin (int): GPIO pin for data/command signal (not used in mock)
            reset_pin (int): GPIO pin for reset signal (not used in mock)
        """
        self.width = 128  # Standard SSD1306 width
        self.height = 64  # Standard SSD1306 height
        
        # Create a blank image for the display
        self.image = Image.new('1', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        
        # Find the fonts directory
        self.fonts_dir = self._find_fonts_directory()
        
        print(f"Mock OLED Display: Initialized ({self.width}x{self.height})")
    
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
            pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "scripts" / "fonts",  # /scripts/fonts (alternative path)
            pathlib.Path(__file__).parent.parent.parent / "fonts",  # /software/gwent/fonts
            pathlib.Path(__file__).parent.parent / "fonts",  # /software/gwent/gwent/fonts
            pathlib.Path(__file__).parent / "fonts",  # /software/gwent/gwent/hal/fonts
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                print(f"Mock OLED Display: Found fonts directory at {path}")
                return path
        
        # If no fonts directory is found, use the current directory
        print(f"Mock OLED Display: No fonts directory found, using {pathlib.Path(__file__).parent}")
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
                print(f"Mock OLED Display: Font file not found: {font_path}")
                return ImageFont.load_default()
        except Exception as e:
            print(f"Mock OLED Display: Using default font instead of {name}: {e}")
            return ImageFont.load_default()
    
    def clear(self):
        """
        Clear the display.
        """
        self.draw.rectangle([(0, 0), (self.width, self.height)], outline=0, fill=0)
        print("Mock OLED Display: Cleared")
    
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
        font = self.get_font(font_name, font_size)
        self.draw.text((x, y), text, font=font, fill=1)
        print(f"Mock OLED Display: Displayed text '{text}' at ({x}, {y})")
    
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
        self.clear()
        font = self.get_font(font_name, font_size)
        
        # Draw title if provided
        y_offset = 0
        if title:
            self.draw.text((0, 0), title, font=font, fill=1)
            self.draw.line([(0, font_size + 2), (self.width, font_size + 2)], fill=1)
            y_offset = font_size + 4
            print(f"Mock OLED Display: Displayed menu title '{title}'")
        
        # Calculate visible items
        max_items = (self.height - y_offset) // (font_size + 2)
        start_idx = max(0, min(selected_index, len(items) - max_items))
        end_idx = min(start_idx + max_items, len(items))
        
        # Draw menu items
        for i, item in enumerate(items[start_idx:end_idx], start=start_idx):
            y = y_offset + (i - start_idx) * (font_size + 2)
            
            # Highlight selected item
            if i == selected_index:
                self.draw.rectangle([(0, y), (self.width, y + font_size)], outline=1, fill=1)
                self.draw.text((2, y), item, font=font, fill=0)
                print(f"Mock OLED Display: Displayed selected menu item '{item}'")
            else:
                self.draw.text((2, y), item, font=font, fill=1)
                print(f"Mock OLED Display: Displayed menu item '{item}'")
    
    def display_image(self, image_path):
        """
        Display an image on the OLED.
        
        Args:
            image_path (str): Path to the image file
        """
        try:
            image = Image.open(image_path).convert('1')
            image = image.resize((self.width, self.height))
            self.image = image
            self.draw = ImageDraw.Draw(self.image)
            print(f"Mock OLED Display: Displayed image from {image_path}")
        except Exception as e:
            print(f"Mock OLED Display: Error displaying image: {e}")
    
    def display_datetime(self, x=0, y=0, font_name="pixelmix.ttf", font_size=8, fill="white", format_str="%Y-%m-%d %H:%M:%S"):
        """
        Display the current datetime on the OLED.
        
        Args:
            x (int): X coordinate
            y (int): Y coordinate
            font_name (str): Font filename
            font_size (int): Font size
            fill (str): Text color
            format_str (str): Datetime format string
        
        Returns:
            datetime.datetime: The displayed datetime
        """
        now = datetime.datetime.now()
        datetime_str = now.strftime(format_str)
        
        font = self.get_font(font_name, font_size)
        self.draw.text((x, y), datetime_str, font=font, fill=1)
        print(f"Mock OLED Display: Displayed datetime '{datetime_str}' at ({x}, {y})")
        
        return now
    
    def start_datetime_display(self, x=0, y=0, font_name="pixelmix.ttf", font_size=8, fill="white", format_str="%Y-%m-%d %H:%M:%S"):
        """
        Start a thread to continuously update the datetime display.
        
        Args:
            x (int): X coordinate
            y (int): Y coordinate
            font_name (str): Font filename
            font_size (int): Font size
            fill (str): Text color
            format_str (str): Datetime format string
            
        Returns:
            threading.Thread: The datetime update thread
        """
        self._datetime_running = True
        
        # Print font directory information
        print(f"Mock OLED Display: Using fonts directory: {self.fonts_dir}")
        print(f"Mock OLED Display: Checking if directory exists: {self.fonts_dir.exists()}")
        if self.fonts_dir.exists():
            print(f"Mock OLED Display: Directory contents: {list(self.fonts_dir.glob('*'))}")
        
        def update_datetime():
            # Check font availability once at the beginning to avoid log spam
            try:
                font_path = self.fonts_dir / font_name
                print(f"Mock OLED Display: Looking for font at: {font_path}")
                if not font_path.exists():
                    print(f"Mock OLED Display: Font file not found: {font_path}, will use default font for datetime display")
                else:
                    print(f"Mock OLED Display: Found font file: {font_path}")
            except Exception as e:
                print(f"Mock OLED Display: Will use default font for datetime display: {e}")
                
            while self._datetime_running:
                self.display_datetime(x, y, font_name, font_size, fill, format_str)
                # Sleep until the next second
                now = datetime.datetime.now()
                sleep_time = 1.0 - (now.microsecond / 1000000.0)
                time.sleep(sleep_time)
        
        self._datetime_thread = threading.Thread(target=update_datetime, daemon=True)
        self._datetime_thread.start()
        print("Mock OLED Display: Started datetime display thread")
        return self._datetime_thread
    
    def stop_datetime_display(self):
        """
        Stop the datetime display thread.
        """
        if hasattr(self, '_datetime_running') and self._datetime_running:
            self._datetime_running = False
            if hasattr(self, '_datetime_thread'):
                self._datetime_thread.join(timeout=1.0)
            print("Mock OLED Display: Stopped datetime display thread")
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_datetime_display()
        self.clear()
        print("Mock OLED Display: Cleaned up")