import logging
from pathlib import Path

import gwent.hal.mfdi

from PIL import ImageFont
from luma.core.interface.serial import spi, noop
from luma.oled.device import ssd1306  # Using SSD1306 driver which works with our display
from luma.core.virtual import terminal


"""
    Monochrome 2.4" 128x64 OLED Graphic Display Module
    Using SSD1306 driver which is compatible with our display hardware
    Configuration: device=1, port=0 (confirmed working)
"""


class SSD1306Presenter(gwent.hal.mfdi.Presenter):
    def __init__(self, log_verbose: bool = False, device=1, port=0):
        super().__init__(log_verbose=log_verbose)

        self._log.info("Initializing SSD1306Presenter")
        self.device = None
        self.term = None
        self.font = None
        
        try:
            self._log.info(f"Initializing SPI interface with device={device}, port={port}")
            self._init_luma(device, port)
        except Exception as e:
            self._log.error(f"Failed to initialize display: {e}")
            self._log.error("Display will not be available")

    def _init_luma(self, device, port):
        """Initialize using luma.oled driver with SSD1306"""
        # Always use device=1, port=0 as this is confirmed to work
        self._log.info(f"Initializing SPI interface with device=1, port=0 (overriding device={device}, port={port})")
        self.interface = spi(device=1, port=0, gpio=noop())
        self._log.info("SPI interface initialized successfully")
        
        self._log.info("Initializing SSD1306 device with maximum contrast")
        # Initialize with maximum contrast to ensure visibility
        self.device = ssd1306(self.interface, contrast=255)
        self._log.info("SSD1306 device initialized successfully")
        
        # Try to reset the display
        try:
            self._log.info("Attempting hardware reset of display")
            self.device.command(0xE4)  # Soft reset command for SSD1306
            self._log.info("Hardware reset completed")
        except Exception as e:
            self._log.warning(f"Hardware reset failed: {e}")
        
        self._log.info("Loading font pixelmix.ttf")
        self.font = self.make_font("pixelmix.ttf", 8)
        self._log.info("Font loaded successfully")
        
        self._log.info("Creating terminal")
        self.term = terminal(self.device, self.font, animate=False)
        self._log.info("Terminal created successfully")
        
        self._log.info("SSD1306 initialization complete")

    @staticmethod
    def make_font(name, size):
        try:
            font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
            return ImageFont.truetype(font_path, size)
        except Exception as e:
            logging.getLogger('SSD1306Presenter').error(f"Error loading font {name}: {e}")
            return ImageFont.load_default()

    def clear(self):
        self._log.info("clear() called")
        if self.device is None:
            self._log.warning("clear() called but device is None, returning")
            return
            
        # luma.oled implementation
        self._log.info("Calling term.clear()")
        result = self.term.clear()
        self._log.info("term.clear() completed")
        return result

    def println(self, txt):
        self._log.info(f"println() called with text: '{txt}'")
        if self.device is None:
            self._log.warning("println() called but device is None, returning")
            return
            
        # luma.oled implementation
        self._log.info(f"Calling term.println() with text: '{txt}'")
        result = self.term.println(txt)
        self._log.info("term.println() completed")
        return result

    def redraw(self):
        self._log.info("redraw() called")
        if self.device is None:
            self._log.warning("redraw() called but device is None, returning")
            return
            
        # luma.oled implementation
        if self._display_error:
            self._log.info("Displaying error")
            self.clear()
            self.println(self._error)
        else:
            self._log.info("Clearing display")
            self.clear()

            if self._prompt:
                self._log.info(f"Displaying prompt: {self._prompt}")
                self.println(self._prompt)

            self._log.info(f"Displaying {len(self._choices)} choices")
            for cid, choice in self._choices.items():
                sel = self.selector_symbol(choice)
                self.println(f'{sel} ({choice.id}):\t{choice.text}')

            if self._ok is not None:
                self._log.info("Displaying OK button")
                sel = self.selector_symbol(self._ok)
                self.println(f'{sel} ({self._ok.id}):\t{self._ok.text}')
            if self._cancel is not None:
                self._log.info("Displaying Cancel button")
                sel = self.selector_symbol(self._cancel)
                self.println(f'{sel} ({self._cancel.id}):\t{self._cancel.text}')
                
        # Make sure to actually update the display
        self._log.info("Calling term.flush() to update the display")
        self.term.flush()
        self._log.info("term.flush() completed")
        
        # Additional display refresh to ensure content is visible
        try:
            self._log.info("Performing additional display refresh")
            # Force a display refresh by toggling display on/off
            self.device.hide()
            self.device.show()
            # Set display to maximum contrast again
            self.device.contrast(255)
            self._log.info("Additional display refresh completed")
        except Exception as e:
            self._log.error(f"Error during additional display refresh: {e}")
