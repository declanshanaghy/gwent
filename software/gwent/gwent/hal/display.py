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

# Import the logging module
from ..utils.logging import get_logger, INFO, DEBUG, WARNING, ERROR, VERBOSE

# Add the luma.examples virtual environment to the path
sys.path.append('/home/dshanaghy/luma.examples/venv/lib/python3.11/site-packages')

from luma.core.interface.serial import spi
from luma.oled.device import ssd1306
from luma.core.render import canvas

# Get a logger for this module
logger = get_logger("gwent.hal.display")

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
        # Add content caching to prevent unnecessary refreshes
        self._last_content = None
        self._force_refresh = False
        
        # Add a lock for thread safety
        self._display_lock = threading.Lock()
        try:
            # Initialize SPI interface
            # Using GPIO11 for SCK and GPIO10 for MOSI as per hardware specs
            self.serial = spi(device=1, port=0, gpio_DC=dc_pin, gpio_RST=reset_pin, gpio_CS=cs_pin)
            
            # Log debug information
            logger.debug(f"SPI Configuration: device=1, port=0, gpio_DC={dc_pin}, gpio_RST={reset_pin}, gpio_CS={cs_pin}")
        except Exception as e:
            logger.error(f"Error initializing SPI interface: {e}")
            raise
        
        # Initialize SSD1306 display
        self.device = ssd1306(self.serial, width=width, height=height, rotate=0)
        self.width = self.device.width
        self.height = self.device.height
        logger.info(f"Initialized display: SSD1306 with dimensions {self.width}x{self.height}")
        
        # Use the absolute path to the fonts directory
        self.fonts_dir = pathlib.Path("/home/dshanaghy/fonts")
        
        # If the fonts directory doesn't exist, try to find it
        if not self.fonts_dir.exists():
            self.fonts_dir = self._find_fonts_directory()
            logger.info(f"Using fonts directory: {self.fonts_dir}")
    
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
                logger.info(f"Found fonts directory at: {path}")
                return path
        
        # If no fonts directory is found, use the current directory
        logger.warning(f"No fonts directory found, using: {pathlib.Path(__file__).parent}")
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
                logger.warning(f"Font file not found: {font_path}")
                return ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Using default font instead of {name}: {e}")
            return ImageFont.load_default()
    
    def clear(self):
        """
        Clear the display.
        """
        # Force a refresh on the next display operation
        self._force_refresh = True
        self._last_content = None
        
        # Use a lock to ensure thread safety
        with self._display_lock:
            with canvas(self.device) as draw:
                # Draw a black rectangle to clear the display
                draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            logger.debug("Display cleared")
    
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
        # Create a content key for caching
        content_key = f"text:{text}:{x}:{y}:{font_name}:{font_size}:{fill}"
        
        # Check if content has changed
        if not self._force_refresh and self._last_content == content_key:
            logger.debug(f"Skipping display update - content unchanged")
            return
            
        # Update the content cache
        self._last_content = content_key
        self._force_refresh = False
        
        # Use a lock to ensure thread safety
        with self._display_lock:
            with canvas(self.device) as draw:
                try:
                    font = self.get_font(font_name, font_size)
                    draw.text((x, y), text, font=font, fill=fill)
                    logger.debug(f"Displayed text: '{text}' using font: {font_name}")
                except Exception as e:
                    logger.warning(f"Error displaying text with font {font_name}: {e}")
                    # Try with default font
                    draw.text((x, y), text, fill=fill)
                    logger.debug(f"Displayed text: '{text}' using default font")
                
    def display_multiple_texts(self, texts, font_name="pixelmix.ttf", font_size=8, fill="white"):
        """
        Display multiple text items on the OLED in a single update.
        
        Args:
            texts (list): List of (text, x, y, font_size) tuples
            font_name (str): Default font filename
            font_size (int): Default font size
            fill (str): Text color ("white" for white, "black" for black)
        """
        # Create a content key for caching
        content_key = f"multi:{str(texts)}:{font_name}:{font_size}:{fill}"
        
        # Check if content has changed
        if not self._force_refresh and self._last_content == content_key:
            logger.debug(f"Skipping display update - content unchanged")
            return
            
        # Update the content cache
        self._last_content = content_key
        self._force_refresh = False
        
        # Use a lock to ensure thread safety
        with self._display_lock:
            with canvas(self.device) as draw:
                for text_item in texts:
                    if len(text_item) == 2:
                        text, y = text_item
                        x, item_font_size = 0, font_size
                    elif len(text_item) == 3:
                        text, x, y = text_item
                        item_font_size = font_size
                    elif len(text_item) >= 4:
                        text, x, y, item_font_size = text_item[:4]
                    else:
                        logger.warning(f"Invalid text item format: {text_item}")
                        continue
                    
                    try:
                        font = self.get_font(font_name, item_font_size)
                        draw.text((x, y), text, font=font, fill=fill)
                        logger.debug(f"Displayed text: '{text}' using font: {font_name}")
                    except Exception as e:
                        logger.warning(f"Error displaying text with font {font_name}: {e}")
                        # Try with default font
                        draw.text((x, y), text, fill=fill)
                        logger.debug(f"Displayed text: '{text}' using default font")
    
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
        # Create a content key for caching
        content_key = f"menu:{str(items)}:{selected_index}:{title}:{font_name}:{font_size}"
        
        # Check if content has changed
        if not self._force_refresh and self._last_content == content_key:
            logger.debug(f"Skipping display update - menu unchanged")
            return
            
        # Update the content cache
        self._last_content = content_key
        self._force_refresh = False
        
        # Use a lock to ensure thread safety
        with self._display_lock:
            with canvas(self.device) as draw:
                try:
                    font = self.get_font(font_name, font_size)
                    logger.debug(f"Using font: {font_name} for menu display")
                except Exception as e:
                    logger.warning(f"Error loading font {font_name} for menu: {e}")
                    # Use default font
                    font = None
                    logger.debug("Using default font for menu display")
                
                # Draw title if provided
                y_offset = 0
                if title:
                    # Handle multi-line titles (e.g., datetime + title)
                    if "\n" in title:
                        title_lines = title.split("\n")
                        for i, line in enumerate(title_lines):
                            line_y = i * (font_size + 2)
                            draw.text((0, line_y), line, font=font, fill="white")
                        draw.line([(0, len(title_lines) * (font_size + 2)), (self.width, len(title_lines) * (font_size + 2))], fill="white")
                        y_offset = len(title_lines) * (font_size + 2) + 2
                    else:
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
            logger.debug(f"Displayed image: {image_path}")
        except Exception as e:
            logger.error(f"Error displaying image: {e}")
    
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
        
        # Use a lock to ensure thread safety
        with self._display_lock:
            with canvas(self.device) as draw:
                try:
                    font = self.get_font(font_name, font_size)
                    draw.text((x, y), datetime_str, font=font, fill=fill)
                    logger.debug(f"Displayed datetime: '{datetime_str}' using font: {font_name}")
                except Exception as e:
                    logger.warning(f"Error displaying datetime with font {font_name}: {e}")
                    # Try with default font
                    draw.text((x, y), datetime_str, fill=fill)
                    logger.debug(f"Displayed datetime: '{datetime_str}' using default font")
        
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
        
        # Log font directory information
        logger.debug(f"Using fonts directory: {self.fonts_dir}")
        logger.debug(f"Checking if directory exists: {self.fonts_dir.exists()}")
        if self.fonts_dir.exists():
            logger.verbose(f"Directory contents: {list(self.fonts_dir.glob('*'))}")
        
        def update_datetime():
            # Check font availability once at the beginning to avoid log spam
            try:
                font_path = self.fonts_dir / font_name
                logger.debug(f"Looking for font at: {font_path}")
                if not font_path.exists():
                    logger.warning(f"Font file not found: {font_path}, will use default font for datetime display")
                else:
                    logger.debug(f"Found font file: {font_path}")
            except Exception as e:
                logger.warning(f"Will use default font for datetime display: {e}")
                
            while self._datetime_running:
                self.display_datetime(x, y, font_name, font_size, fill, format_str)
                # Sleep until the next second
                now = datetime.datetime.now()
                sleep_time = 1.0 - (now.microsecond / 1000000.0)
                time.sleep(sleep_time)
        
        self._datetime_thread = threading.Thread(target=update_datetime, daemon=True)
        self._datetime_thread.start()
        logger.info("Started datetime display thread")
        return self._datetime_thread
    
    def stop_datetime_display(self):
        """
        Stop the datetime display thread.
        """
        if hasattr(self, '_datetime_running') and self._datetime_running:
            self._datetime_running = False
            if hasattr(self, '_datetime_thread'):
                self._datetime_thread.join(timeout=1.0)
            logger.info("Stopped datetime display thread")
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_datetime_display()
        self.clear()
        logger.info("Display cleaned up")
