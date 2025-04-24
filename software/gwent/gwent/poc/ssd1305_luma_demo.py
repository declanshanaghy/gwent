#!/usr/bin/env python3

"""
This demo will fill the screen with white, draw a black box on top
and then print Hello World! in the center of the display

This version uses the luma.oled library instead of Adafruit CircuitPython
"""

from time import sleep
from luma.core.interface.serial import spi
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

# Define the dimensions
WIDTH = 128
HEIGHT = 64
BORDER = 8

# Use for SPI
serial = spi(device=1, port=0)
device = ssd1306(serial)

# Clear display
device.clear()

# Create blank image for drawing
# Make sure to create image with mode '1' for 1-bit color
image = Image.new("1", (device.width, device.height))

# Get drawing object to draw on image
draw = ImageDraw.Draw(image)

# Draw a white background
draw.rectangle((0, 0, device.width, device.height), outline=255, fill=255)

# Draw a smaller inner rectangle
draw.rectangle(
    (BORDER, BORDER, device.width - BORDER - 1, device.height - BORDER - 1),
    outline=0,
    fill=0,
)

# Load default font
font = ImageFont.load_default()

# Draw Some Text
text = "Hello World 3"
# Use getbbox() instead of deprecated getsize()
bbox = font.getbbox(text)
font_width = bbox[2] - bbox[0]
font_height = bbox[3] - bbox[1]
draw.text(
    (device.width // 2 - font_width // 2, device.height // 2 - font_height // 2),
    text,
    font=font,
    fill=255,
)

# Display image
device.display(image)

# Keep the display on
while True:
    sleep(1)