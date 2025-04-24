#!/usr/bin/env python3

"""
Direct OLED display test script that bypasses the game's MFD system.
This script will attempt to initialize the display directly and display a test pattern.
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

logger = logging.getLogger("oled_direct_test")

def test_ssd1306_direct():
    """Test the SSD1306 display directly using luma.oled"""
    logger.info("Testing SSD1306 display directly")
    
    try:
        from luma.core.interface.serial import spi, noop
        from luma.oled.device import ssd1306
        from luma.core.render import canvas
        from PIL import ImageFont, ImageDraw
        
        # Initialize SPI interface
        logger.info("Initializing SPI interface with device=1, port=0")
        serial_interface = spi(device=1, port=0, gpio=noop())
        
        # Initialize device with explicit contrast
        logger.info("Initializing SSD1306 device with contrast=255 (maximum)")
        device = ssd1306(serial_interface, contrast=255)
        
        # Try to reset the display
        try:
            logger.info("Attempting hardware reset of display")
            device.command(0xE4)  # Soft reset command for SSD1306
            logger.info("Hardware reset completed")
        except Exception as e:
            logger.warning(f"Hardware reset failed: {e}")
        
        # Clear the display
        logger.info("Clearing display")
        device.clear()
        
        # Draw test pattern
        logger.info("Drawing test pattern")
        with canvas(device) as draw:
            # Draw border
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            
            # Draw text
            draw.text((10, 10), "DIRECT TEST", fill="white")
            draw.text((10, 25), "SSD1306 Driver", fill="white")
            draw.text((10, 40), "If you can see this", fill="white")
            draw.text((10, 50), "display is working!", fill="white")
        
        logger.info("Test pattern displayed")
        
        # Additional display refresh to ensure content is visible
        try:
            logger.info("Performing additional display refresh")
            # Force a display refresh by toggling display on/off
            device.hide()
            device.show()
            # Set display to maximum contrast again
            device.contrast(255)
            logger.info("Additional display refresh completed")
        except Exception as e:
            logger.error(f"Error during additional display refresh: {e}")
        
        logger.info("Waiting 5 seconds")
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
        
        # Try different display modes
        logger.info("Testing display modes")
        
        # Normal mode
        logger.info("Setting normal display mode")
        device.command(0xA6)  # Normal display mode
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 10), "Normal Mode", fill="white")
            draw.text((10, 30), "White on Black", fill="white")
        time.sleep(2)
        
        # Inverted mode
        logger.info("Setting inverted display mode")
        device.command(0xA7)  # Inverted display mode
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 10), "Inverted Mode", fill="white")
            draw.text((10, 30), "Black on White", fill="white")
        time.sleep(2)
        
        # Reset to normal mode
        device.command(0xA6)  # Normal display mode
        
        # Final test pattern
        with canvas(device) as draw:
            # Draw alternating pattern to test all pixels
            for y in range(0, device.height, 2):
                for x in range(0, device.width, 2):
                    draw.point((x, y), fill="white")
                    draw.point((x+1, y+1), fill="white")
        
        logger.info("Checkerboard pattern displayed")
        time.sleep(2)
        
        # Final message
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 10), "Test Complete", fill="white")
            draw.text((10, 30), "Display should be", fill="white")
            draw.text((10, 40), "working now!", fill="white")
        
        logger.info("Test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error testing SSD1306 display: {e}")
        return False

def run():
    """Main function to run the direct OLED test"""
    logger.info("Starting direct OLED display test")
    
    # Test with SSD1306 driver
    logger.info("\n=== Testing with SSD1306 Driver ===")
    success = test_ssd1306_direct()
    
    # Print summary
    logger.info("\n=== Test Results Summary ===")
    logger.info(f"SSD1306 direct test: {'SUCCESS' if success else 'FAILED'}")
    
    if not success:
        logger.info("\nRecommendations:")
        logger.info("1. Check physical connections (SPI wiring)")
        logger.info("2. Verify power supply to the display")
        logger.info("3. Try a different display if available")
    else:
        logger.info("\nDisplay test completed successfully!")

if __name__ == "__main__":
    run()