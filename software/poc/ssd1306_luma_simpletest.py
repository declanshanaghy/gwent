#!/usr/bin/env python3

from time import sleep

from luma.core.interface.serial import spi
from luma.oled.device import ssd1306

from pathlib import Path
from luma.core.virtual import terminal
from PIL import ImageFont


def make_font(name, size):
    font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
    return ImageFont.truetype(font_path, size)


interface = spi(device=1, port=0)
device = ssd1306(interface)

font = make_font("pixelmix.ttf", 8)
term = terminal(device, font)

term.puts("  Thing One\n")
term.puts("> Thingotwo\n")
term.puts("  Third Thing\n")
term.puts("  Here's the fourth\n")
term.puts("  Another fifth\n")
term.puts("  Sisxth is the best\n")

while True:
    pass