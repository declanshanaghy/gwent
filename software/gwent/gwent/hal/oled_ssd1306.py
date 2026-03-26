import time
from gwent.utils.logging import get_logger
from pathlib import Path

import gwent.hal
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
    def __init__(self, device=1, port=0):
        super().__init__()
        self._log_verbose = False

        self._log.info("Initializing SSD1306Presenter")
        self.device = None
        self.term = None
        self.font = None
        
        # Store initialization parameters for debugging
        self._device_param = device
        self._port_param = port
        
        try:
            self._log.info(f"Initializing SPI interface with device={device}, port={port}")
            self._init_luma(device, port)
        except Exception as e:
            self._log.error(f"Failed to initialize display: {e}", exc_info=True)
            self._log.error("Display will not be available")

    def _init_luma(self, device, port):
        """Initialize using luma.oled driver with SSD1306"""

        try:
            self._log.info(f"Attempting to initialize SPI interface with device={device}, port={port}")
            self._log.debug("Creating SPI interface with noop GPIO")
            # GPIO25 is shared between the OLED reset and MFRC522 RFID
            # reset. We manually pulse it here, then pass gpio_RST=None
            # so luma doesn't call gpio.cleanup() on it (which would
            # release the pin and let it float LOW, holding the RFID
            # chip in permanent reset).
            import RPi.GPIO as GPIO
            GPIO.setwarnings(False)
            if GPIO.getmode() is None:
                GPIO.setmode(GPIO.BCM)
            GPIO.setup(25, GPIO.OUT)
            GPIO.output(25, GPIO.LOW)
            time.sleep(0.01)
            GPIO.output(25, GPIO.HIGH)
            time.sleep(0.05)
            self.interface = spi(device=device, port=port, gpio_RST=None)
            self._log.info(f"SPI interface initialized successfully with device={device}, port={port}")
            
            # Store the successful combination
            self._device_param = device
            self._port_param = device
        except Exception as e:
            self._log.warning(f"Failed to initialize SPI interface with device={device}, port={port}: {e}")
            last_exception = e
        
        if not hasattr(self, 'interface') or self.interface is None:
            self._log.error("All SPI interface initialization attempts failed")
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError("Failed to initialize SPI interface")
        
        # Initialize the display with multiple retry attempts
        retry_count = 3
        for attempt in range(retry_count):
            try:
                self._log.info(f"Initializing SSD1306 device (attempt {attempt+1}/{retry_count})")
                # Initialize with maximum contrast to ensure visibility
                self.device = ssd1306(self.interface, contrast=255)
                self._log.info(f"SSD1306 device initialized successfully: {self.device}")
                self._log.debug(f"Device dimensions: {self.device.width}x{self.device.height}")
                self._log.debug(f"Device mode: {self.device.mode}")
                break
            except Exception as e:
                self._log.warning(f"Attempt {attempt+1}/{retry_count} failed: {e}")
                if attempt == retry_count - 1:  # Last attempt
                    self._log.error("All SSD1306 initialization attempts failed")
                    raise
                time.sleep(0.5)  # Wait before retrying
        
        # Perform a comprehensive reset sequence
        try:
            self._log.info("Performing comprehensive display reset sequence")
            
            # Soft reset command
            self.device.command(0xE4)
            
            # Power cycle the display
            self.device.command(0xAE)  # Display off
            time.sleep(0.1)
            self.device.command(0xAF)  # Display on
            
            # Set contrast to maximum
            self.device.contrast(255)
            
            self._log.info("Display reset sequence completed")
        except Exception as e:
            self._log.warning(f"Display reset sequence failed: {e}", exc_info=True)
            self._log.info("Continuing despite reset failure")
        
        # Load font with fallback mechanism
        try:
            self._log.info("Loading font pixelmix.ttf")
            self.font = self.make_font("pixelmix.ttf", 8)
            if self.font == ImageFont.load_default():
                self._log.warning("Using default font instead of pixelmix.ttf")
                
                # Try to copy font from scripts directory if it exists
                try:
                    scripts_font_path = Path(__file__).resolve().parent.parent.parent.parent.parent.joinpath('scripts', 'fonts', 'pixelmix.ttf')
                    font_dir = Path(__file__).resolve().parent.joinpath('fonts')
                    target_path = font_dir.joinpath('pixelmix.ttf')
                    
                    self._log.info(f"Checking for font at {scripts_font_path}")
                    if scripts_font_path.exists() and not target_path.exists():
                        self._log.info(f"Found font at {scripts_font_path}, copying to {target_path}")
                        # Create fonts directory if it doesn't exist
                        font_dir.mkdir(exist_ok=True)
                        # Copy the font file
                        import shutil
                        shutil.copy(scripts_font_path, target_path)
                        self._log.info("Font copied successfully, trying to load again")
                        
                        # Try loading the font again
                        self.font = self.make_font("pixelmix.ttf", 8)
                        if self.font != ImageFont.load_default():
                            self._log.info("Successfully loaded pixelmix.ttf after copying")
                except Exception as e:
                    self._log.warning(f"Failed to copy font: {e}")
            else:
                self._log.info("Font pixelmix.ttf loaded successfully")
        except Exception as e:
            self._log.error(f"Error loading font: {e}", exc_info=True)
            self._log.warning("Using default font as fallback")
            self.font = ImageFont.load_default()
        
        try:
            self._log.info("Creating terminal with font")
            self.term = terminal(self.device, self.font, animate=False)
            self._log.info("Terminal created successfully")
        except Exception as e:
            self._log.error(f"Failed to create terminal: {e}", exc_info=True)
            raise
        
        self._log.info("SSD1306 initialization complete")

    @staticmethod
    def make_font(name, size):
        logger = get_logger('SSD1306Presenter')
        try:
            font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
            logger.debug(f"Looking for font at: {font_path}")
            
            if not Path(font_path).exists():
                logger.error(f"Font file not found: {font_path}")
                return ImageFont.load_default()
                
            logger.debug(f"Loading TrueType font: {name} with size {size}")
            font = ImageFont.truetype(font_path, size)
            logger.debug(f"Font loaded successfully: {font}")
            return font
        except Exception as e:
            logger.error(f"Error loading font {name}: {e}", exc_info=True)
            logger.warning(f"Using default font instead")
            return ImageFont.load_default()

    def clear(self):
        if self.device is None:
            return
        with gwent.hal.spi_lock:
            return self.term.clear()

    def println(self, txt):
        if self.device is None:
            return
        with gwent.hal.spi_lock:
            try:
                return self.term.println(txt)
            except Exception as e:
                self._log.error(f"Error in println(): {e}")
                simple_txt = str(txt).encode('ascii', 'replace').decode('ascii')
                return self.term.println(simple_txt)

    def redraw(self):
        with gwent.hal.spi_lock:
            self._redraw_locked()

    def _redraw_locked(self):
        if self.device is None:
            return

        try:
            self.term.clear()

            if self._display_error:
                self.term.println(self._error)
            else:
                if self._prompt:
                    self.term.println(self._prompt)

                for cid, choice in self._choices.items():
                    sel = self.selector_symbol(choice)
                    self.term.println(f'{sel} {choice.text}')

                if self._ok is not None:
                    sel = self.selector_symbol(self._ok)
                    self.term.println(f'{sel} {self._ok.text}')

                if self._cancel is not None:
                    sel = self.selector_symbol(self._cancel)
                    self.term.println(f'{sel} {self._cancel.text}')

            self.term.flush()

        except Exception as e:
            self._log.error(f"Error in redraw(): {e}", exc_info=True)
