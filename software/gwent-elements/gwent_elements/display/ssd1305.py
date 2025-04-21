#!/usr/bin/env python3

"""
SSD1305 OLED display driver using Adafruit CircuitPython
"""

import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1305


class SSD1305Display:
    """
    SSD1305 OLED display driver using Adafruit CircuitPython
    """
    
    def __init__(self, width=128, height=64, reset_pin=board.D25, cs_pin=board.D7, dc_pin=board.D24, spi=None):
        """
        Initialize the SSD1305 display
        
        Args:
            width (int): Display width in pixels
            height (int): Display height in pixels
            reset_pin: Reset pin (default: board.D25)
            cs_pin: Chip select pin (default: board.D7)
            dc_pin: Data/command pin (default: board.D24)
            spi: SPI interface (default: board.SPI())
        """
        self.width = width
        self.height = height
        
        # Define the reset pin
        self.oled_reset = digitalio.DigitalInOut(reset_pin)
        
        # Define the CS pin
        self.oled_cs = digitalio.DigitalInOut(cs_pin)
        
        # Define the DC pin
        self.oled_dc = digitalio.DigitalInOut(dc_pin)
        
        # Use SPI
        if spi is None:
            self.spi = board.SPI()
        else:
            self.spi = spi
            
        # Create the display
        self.display = adafruit_ssd1305.SSD1305_SPI(
            self.width, self.height, self.spi, self.oled_dc, self.oled_reset, self.oled_cs
        )
        
        # Clear display
        self.clear()
        
    def clear(self):
        """Clear the display"""
        self.display.fill(0)
        self.display.show()
        
    def create_image(self):
        """Create a blank image for drawing"""
        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        return Image.new("1", (self.display.width, self.display.height))
        
    def show_text(self, text, x=None, y=None, font=None, fill=255):
        """
        Show text on the display
        
        Args:
            text (str): Text to display
            x (int): X position (default: centered)
            y (int): Y position (default: centered)
            font: PIL font (default: default font)
            fill (int): Fill color (default: 255)
        """
        # Create blank image for drawing
        image = self.create_image()
        
        # Get drawing object to draw on image
        draw = ImageDraw.Draw(image)
        
        # Load default font if none provided
        if font is None:
            font = ImageFont.load_default()
            
        # Get text size
        (font_width, font_height) = font.getsize(text)
        
        # Center text if x or y not provided
        if x is None:
            x = self.display.width // 2 - font_width // 2
        if y is None:
            y = self.display.height // 2 - font_height // 2
            
        # Draw text
        draw.text((x, y), text, font=font, fill=fill)
        
        # Display image
        self.display.image(image)
        self.display.show()
        
    def draw_rectangle(self, x0, y0, x1, y1, outline=255, fill=0):
        """
        Draw a rectangle on the display
        
        Args:
            x0 (int): Top left X coordinate
            y0 (int): Top left Y coordinate
            x1 (int): Bottom right X coordinate
            y1 (int): Bottom right Y coordinate
            outline (int): Outline color (default: 255)
            fill (int): Fill color (default: 0)
        """
        # Create blank image for drawing
        image = self.create_image()
        
        # Get drawing object to draw on image
        draw = ImageDraw.Draw(image)
        
        # Draw rectangle
        draw.rectangle((x0, y0, x1, y1), outline=outline, fill=fill)
        
        # Display image
        self.display.image(image)
        self.display.show()