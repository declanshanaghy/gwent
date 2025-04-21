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


class SSD1325Presenter(gwent.hal.mfdi.Presenter):
    def __init__(self, loop: asyncio.AbstractEventLoop,
                 log_verbose: bool = False):
        super().__init__(loop, log_verbose=log_verbose)

        # Use noop for GPIO to avoid conflicts
        try:
            # Try with SPI
            self.interface = spi(device=1, port=0, gpio=noop())
            self.font = self.make_font("pixelmix.ttf", 8)
            self.device = ssd1306(self.interface)
            self.term = terminal(self.device, self.font, animate=False)
        except Exception as e:
            self._log.error(f"Error initializing SPI: {e}")
            # Fall back to a dummy implementation
            self.interface = None
            self.font = None
            self.device = None
            self.term = None

    @staticmethod
    def make_font(name, size):
        font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
        return ImageFont.truetype(font_path, size)

    async def clear(self):
        if self.term is None:
            return
        return await self._loop.run_in_executor(None, self.term.clear)

    async def println(self, txt):
        if self.term is None:
            return
        return await self._loop.run_in_executor(None, self.term.println, txt)

    async def redraw(self):
        if self.term is None:
            return
        return await self._loop.run_in_executor(None, self.term.redraw)

    async def println(self, txt):
        return await self._loop.run_in_executor(None, self.term.println, txt)

    async def redraw(self):
        if self._display_error:
            await self.clear()
            await self.println(self._error)
        else:
            await self.clear()

            if self._prompt:
                await self.println(self._prompt)

            for cid, choice in self._choices.items():
                sel = self.selector_symbol(choice)
                await self.println(f'{sel} ({choice.id}):\t{choice.text}')

            if self._ok is not None:
                sel = self.selector_symbol(self._ok)
                await self.println(f'{sel} ({self._ok.id}):\t{self._ok.text}')
            if self._cancel is not None:
                sel = self.selector_symbol(self._cancel)
                await self.println(f'{sel} ({self._cancel.id}):\t{self._cancel.text}')
