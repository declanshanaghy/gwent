import asyncio
import gwent.hal.mfdi

from luma.core.interface.serial import spi, noop
from luma.oled.device import ssd1306

from pathlib import Path
from luma.core.virtual import terminal
from PIL import ImageFont


"""
    Monochrome 2.4" 128x64 OLED Graphic Display Module
    Based on SSD1305 driver chip
    https://www.adafruit.com/product/2719
    https://learn.adafruit.com/1-5-and-2-4-monochrome-128x64-oled-display-module/python-wiring
    
    Alternative tutorial using luma.oled
    https://satoshinm.github.io/blog/171110monochrome_2.7_and_2.42_128x64_oled_displays_on_a_raspberry_pi_zero.html
"""


class SSD1306Presenter(gwent.hal.mfdi.Presenter):
    def __init__(self, loop: asyncio.AbstractEventLoop,
                 log_verbose: bool = False, device=0, port=0):
        super().__init__(loop, log_verbose=log_verbose)

        self._log.info("Initializing SSD1306Presenter")
        self._log.info(f"Attempting to initialize SPI interface with device={device}, port={port}")
        self.interface = spi(device=device, port=port, gpio=noop())
        self._log.info("SPI interface initialized successfully")
        
        self._log.info("Initializing SSD1306 device")
        self.device = ssd1306(self.interface)
        self._log.info("SSD1306 device initialized successfully")
        
        self._log.info("Loading font pixelmix.ttf")
        self.font = self.make_font("pixelmix.ttf", 8)
        self._log.info("Font loaded successfully")
        
        self._log.info("Creating terminal")
        self.term = terminal(self.device, self.font, animate=False)
        self._log.info("Terminal created successfully")
        
        self._log.info("SSD1306Presenter initialization complete")

    @staticmethod
    def make_font(name, size):
        font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
        return ImageFont.truetype(font_path, size)

    async def clear(self):
        self._log.info("clear() called")
        if self.term is None:
            self._log.warning("clear() called but term is None, returning")
            return
        self._log.info("Calling term.clear()")
        result = await self._loop.run_in_executor(None, self.term.clear)
        self._log.info("term.clear() completed")
        return result

    async def println(self, txt):
        self._log.info(f"println() called with text: '{txt}'")
        if self.term is None:
            self._log.warning("println() called but term is None, returning")
            return
        self._log.info(f"Calling term.println() with text: '{txt}'")
        result = await self._loop.run_in_executor(None, self.term.println, txt)
        self._log.info("term.println() completed")
        return result

    async def redraw(self):
        self._log.info("redraw() called")
        if self.term is None:
            self._log.warning("redraw() called but term is None, returning")
            return
            
        if self._display_error:
            self._log.info("Displaying error")
            await self.clear()
            await self.println(self._error)
        else:
            self._log.info("Clearing display")
            await self.clear()

            if self._prompt:
                self._log.info(f"Displaying prompt: {self._prompt}")
                await self.println(self._prompt)

            self._log.info(f"Displaying {len(self._choices)} choices")
            for cid, choice in self._choices.items():
                sel = self.selector_symbol(choice)
                await self.println(f'{sel} ({choice.id}):\t{choice.text}')

            if self._ok is not None:
                self._log.info("Displaying OK button")
                sel = self.selector_symbol(self._ok)
                await self.println(f'{sel} ({self._ok.id}):\t{self._ok.text}')
            if self._cancel is not None:
                self._log.info("Displaying Cancel button")
                sel = self.selector_symbol(self._cancel)
                await self.println(f'{sel} ({self._cancel.id}):\t{self._cancel.text}')
                
        # Make sure to actually update the display
        if self.term is not None:
            self._log.info("Calling term.flush() to update the display")
            await self._loop.run_in_executor(None, self.term.flush)
            self._log.info("term.flush() completed")
