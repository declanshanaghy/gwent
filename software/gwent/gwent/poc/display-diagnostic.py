#!/usr/bin/env python3

"""
Display diagnostic script to help troubleshoot OLED display issues.
This script will attempt to initialize the display with different drivers
and configurations, and display a test pattern.
"""

import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("display_diagnostic")

def test_ssd1306_display():
    """Test the display using SSD1306 driver with explicit contrast settings"""
    logger.info("Testing display with SSD1306 driver")
    
    try:
        from luma.core.interface.serial import spi
        from luma.oled.device import ssd1306
        from luma.core.render import canvas
        from PIL import ImageFont, ImageDraw
        
        # Initialize SPI interface
        logger.info("Initializing SPI interface with device=1, port=0")
        serial_interface = spi(device=1, port=0)
        
        # Initialize device with explicit contrast
        logger.info("Initializing SSD1306 device with contrast=255 (maximum)")
        device = ssd1306(serial_interface, contrast=255)
        
        # Clear the display
        logger.info("Clearing display")
        device.clear()
        
        # Draw test pattern
        logger.info("Drawing test pattern")
        with canvas(device) as draw:
            # Draw border
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            
            # Draw text
            draw.text((10, 10), "DISPLAY TEST", fill="white")
            draw.text((10, 25), "SSD1306 Driver", fill="white")
            draw.text((10, 40), "If you can see this", fill="white")
            draw.text((10, 50), "display is working!", fill="white")
        
        logger.info("Test pattern displayed - waiting 5 seconds")
        time.sleep(5)
        
        # Try different contrast levels
        for contrast in [255, 128, 64, 32]:
            logger.info(f"Setting contrast to {contrast}")
            device.contrast(contrast)
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="white", fill="black")
                draw.text((10, 10), f"Contrast: {contrast}", fill="white")
                draw.text((10, 30), "Can you see this?", fill="white")
            time.sleep(2)
        
        # Reset to high contrast
        device.contrast(255)
        return True
        
    except Exception as e:
        logger.error(f"Error testing SSD1306 display: {e}")
        return False

def test_ssd1305_display():
    """Test the display using SSD1305 driver"""
    logger.info("Testing display with SSD1305 driver")
    
    try:
        import board
        import digitalio
        import adafruit_ssd1305
        from PIL import Image, ImageDraw, ImageFont
        
        # Define the Reset Pin
        oled_reset = digitalio.DigitalInOut(board.D25)
        
        # Use for SPI
        spi_bus = board.SPI()
        oled_cs = digitalio.DigitalInOut(board.D7)    # CE1
        oled_dc = digitalio.DigitalInOut(board.D24)
        
        # Initialize display
        logger.info("Initializing SSD1305 with Adafruit library")
        oled = adafruit_ssd1305.SSD1305_SPI(128, 64, spi_bus, oled_dc, oled_reset, oled_cs)
        
        # Clear display
        oled.fill(0)
        oled.show()
        
        # Create blank image for drawing
        image = Image.new("1", (oled.width, oled.height))
        draw = ImageDraw.Draw(image)
        
        # Draw a test pattern
        draw.rectangle((0, 0, oled.width, oled.height), outline=255, fill=0)
        draw.text((10, 10), "DISPLAY TEST", fill=255)
        draw.text((10, 25), "SSD1305 Driver", fill=255)
        draw.text((10, 40), "If you can see this", fill=255)
        draw.text((10, 50), "display is working!", fill=255)
        
        # Display image
        oled.image(image)
        oled.show()
        
        logger.info("Test pattern displayed - waiting 5 seconds")
        time.sleep(5)
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing SSD1305 display: {e}")
        return False

def check_hardware_connections():
    """Check hardware connections using GPIO"""
    logger.info("Checking hardware connections")
    
    try:
        import RPi.GPIO as GPIO
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Check SPI pins
        spi_pins = [10, 9, 11, 8]  # MOSI, MISO, SCLK, CE0
        pin_names = ["MOSI", "MISO", "SCLK", "CE0"]
        
        for pin, name in zip(spi_pins, pin_names):
            GPIO.setup(pin, GPIO.IN)
            state = GPIO.input(pin)
            logger.info(f"SPI {name} (GPIO {pin}) state: {state}")
        
        # Check reset and DC pins
        reset_pin = 25  # D25
        dc_pin = 24     # D24
        
        GPIO.setup(reset_pin, GPIO.IN)
        reset_state = GPIO.input(reset_pin)
        logger.info(f"Reset pin (GPIO {reset_pin}) state: {reset_state}")
        
        GPIO.setup(dc_pin, GPIO.IN)
        dc_state = GPIO.input(dc_pin)
        logger.info(f"DC pin (GPIO {dc_pin}) state: {dc_state}")
        
        # Cleanup
        GPIO.cleanup()
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking hardware connections: {e}")
        return False

def run():
    """Main function to run the display diagnostics"""
    logger.info("Starting display diagnostics")
    
    # Check hardware connections
    logger.info("\n=== Checking Hardware Connections ===")
    try:
        check_hardware_connections()
    except Exception as e:
        logger.error(f"Hardware connection check failed: {e}")
    
    # Test with SSD1306 driver
    logger.info("\n=== Testing with SSD1306 Driver ===")
    ssd1306_success = test_ssd1306_display()
    
    # Test with SSD1305 driver
    logger.info("\n=== Testing with SSD1305 Driver ===")
    ssd1305_success = test_ssd1305_display()
    
    # Print summary
    logger.info("\n=== Test Results Summary ===")
    logger.info(f"SSD1306 driver test: {'SUCCESS' if ssd1306_success else 'FAILED'}")
    logger.info(f"SSD1305 driver test: {'SUCCESS' if ssd1305_success else 'FAILED'}")
    
    if not (ssd1306_success or ssd1305_success):
        logger.info("\nRecommendations:")
        logger.info("1. Check physical connections (SPI wiring)")
        logger.info("2. Verify power supply to the display")
        logger.info("3. Try adjusting contrast settings")
        logger.info("4. Verify the display model (SSD1305 vs SSD1306)")
    else:
        logger.info("\nDisplay is working with at least one driver!")

if __name__ == "__main__":
    run()