#!/usr/bin/env python3

"""
SSD1306 OLED display driver using luma.oled
"""

import os
from pathlib import Path
from PIL import ImageFont
from luma.core.interface.serial import spi
from luma.oled.device import ssd1306
from luma.core.virtual import terminal


class SSD1306Display:
    """
    SSD1306 OLED display driver using luma.oled
    """
    
    def __init__(self, device=1, port=0, font_name="pixelmix.ttf", font_size=8):
        """
        Initialize the SSD1306 display
        
        Args:
            device (int): SPI device number (default: 1)
            port (int): SPI port number (default: 0)
            font_name (str): Font name (default: pixelmix.ttf)
            font_size (int): Font size (default: 8)
        """
        # Initialize SPI interface
        self.interface = spi(device=device, port=port)
        
        # Initialize display
        self.device = ssd1306(self.interface)
        
        # Load font
        self.font = self._make_font(font_name, font_size)
        
        # Create terminal
        self.term = terminal(self.device, self.font)
        
    def _make_font(self, name, size):
        """
        Create a font object
        
        Args:
            name (str): Font name
            size (int): Font size
            
        Returns:
            PIL.ImageFont: Font object
        """
        try:
            # Try to use the font from the gwent_elements.fonts package
            from gwent_elements.fonts import get_font_path
            font_path = get_font_path(name)
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except (ImportError, FileNotFoundError):
            pass
            
        # Look for the font in the current directory
        font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        
        # If all else fails, use the default font
        return ImageFont.load_default()
        
    def clear(self):
        """Clear the display"""
        self.term.clear()
        
    def println(self, text):
        """
        Print a line of text to the display
        
        Args:
            text (str): Text to display
        """
        self.term.println(text)
        
    def puts(self, text):
        """
        Print text to the display without a newline
        
        Args:
            text (str): Text to display
        """
        self.term.puts(text)
        
    def menu(self, items, selected_index=0):
        """
        Display a menu on the screen
        
        Args:
            items (list): List of menu items
            selected_index (int): Index of the selected item (default: 0)
        """
        self.clear()
        
        # Display each menu item
        for i, item in enumerate(items):
            # Add a selection indicator for the selected item
            if i == selected_index:
                self.term.puts("> ")
            else:
                self.term.puts("  ")
                
            self.term.puts(item)
            self.term.puts("\n")