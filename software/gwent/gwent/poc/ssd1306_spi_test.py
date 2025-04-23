#!/usr/bin/env python3

import time
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

# Create the SPI interface
# Try both port 0 and port 1 to see which one works
try:
    print("Trying SPI with device=0, port=1...")
    serial = spi(device=0, port=1)
    device = ssd1306(serial)
    
    # Draw something on the display
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="black")
        draw.text((10, 10), "SPI Port 1", fill="white")
        draw.text((10, 30), "Test", fill="white")
    
    print("SPI with device=0, port=1 worked!")
    time.sleep(5)
    
    # Clear the display
    with canvas(device) as draw:
        pass
        
except Exception as e:
    print(f"Error with SPI port 1: {e}")
    
    try:
        print("Trying SPI with device=0, port=0...")
        serial = spi(device=0, port=0)
        device = ssd1306(serial)
        
        # Draw something on the display
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 10), "SPI Port 0", fill="white")
            draw.text((10, 30), "Test", fill="white")
        
        print("SPI with device=0, port=0 worked!")
        time.sleep(5)
        
        # Clear the display
        with canvas(device) as draw:
            pass
            
    except Exception as e:
        print(f"Error with SPI port 0: {e}")