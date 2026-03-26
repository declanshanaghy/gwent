#!/usr/bin/env python3

"""
OLED display test script to diagnose issues with the OLED display.
This script will attempt to initialize and test the display using both
SSD1306 and SSD1305 drivers to determine which one works with the hardware.
Run this script directly on the Raspberry Pi.
"""

import time
import sys
import os
from gwent.utils.logging import get_logger, configure_logging, INFO

# Configure logging with console output
configure_logging(level=INFO, log_file="/tmp/logs/oled_test.log")

# Get logger for this component
logger = get_logger("display_test")

def get_user_confirmation(prompt="Can you see the test pattern on the display? (y/n): "):
    """Get confirmation from the user"""
    while True:
        response = input(prompt).strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")

def test_ssd1306_luma():
    """Test the display using the luma.oled SSD1306 driver"""
    logger.info("Testing SSD1306 with luma.oled library")
    working_configs = []
    
    try:
        from luma.core.interface.serial import spi
        from luma.oled.device import ssd1306
        from luma.core.render import canvas
        from PIL import ImageFont

        # Try different device/port combinations
        configs = [
            {"device": 0, "port": 0},
            {"device": 1, "port": 0},
            {"device": 0, "port": 1},
            {"device": 1, "port": 1}
        ]

        for config in configs:
            device_num = config["device"]
            port_num = config["port"]
            
            try:
                logger.info(f"Trying SSD1306 with device={device_num}, port={port_num}")
                serial_interface = spi(device=device_num, port=port_num)
                device = ssd1306(serial_interface)
                
                # Clear the display
                device.clear()
                logger.info("Display cleared successfully")
                
                # Draw something on the display
                with canvas(device) as draw:
                    draw.rectangle(device.bounding_box, outline="white", fill="black")
                    draw.text((10, 10), "SSD1306 Test", fill="white")
                    draw.text((10, 20), f"Dev={device_num}", fill="white")
                    draw.text((10, 30), f"Port={port_num}", fill="white")
                
                logger.info("Test pattern displayed successfully")
                logger.info(f"Please check if you can see the test pattern with device={device_num}, port={port_num}")
                
                # Wait for user confirmation
                if get_user_confirmation():
                    logger.info(f"✓ User confirmed SSD1306 display is working with device={device_num}, port={port_num}")
                    working_configs.append({"driver": "SSD1306", "device": device_num, "port": port_num})
                else:
                    logger.info(f"✗ User reported SSD1306 display is NOT working with device={device_num}, port={port_num}")
                
                # Clean up
                device.clear()
                device.hide()
                
            except Exception as e:
                logger.error(f"Error with SSD1306 (device={device_num}, port={port_num}): {e}")
        
        if working_configs:
            logger.info(f"Found {len(working_configs)} working SSD1306 configurations")
            return working_configs
        else:
            logger.error("All SSD1306 configurations failed")
            return []
            
    except ImportError as e:
        logger.error(f"Could not import luma.oled libraries: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error testing SSD1306: {e}")
        return []

def test_ssd1305_adafruit():
    """Test the display using the Adafruit SSD1305 driver"""
    logger.info("Testing SSD1305 with Adafruit library")
    working_configs = []
    
    try:
        import board
        import digitalio
        import adafruit_ssd1305
        from PIL import Image, ImageDraw, ImageFont
        
        # Define the Reset Pin - try different pins
        reset_pins = [board.D25, board.D24, board.D23]
        cs_pins = [board.D7, board.D8, board.D21]
        dc_pins = [board.D24, board.D23, board.D22]
        
        spi_bus = board.SPI()
        
        for reset_pin in reset_pins:
            reset_name = str(reset_pin).split('.')[-1]
            for cs_pin in cs_pins:
                cs_name = str(cs_pin).split('.')[-1]
                for dc_pin in dc_pins:
                    dc_name = str(dc_pin).split('.')[-1]
                    
                    if cs_pin == dc_pin:
                        continue  # Skip invalid combinations
                        
                    try:
                        logger.info(f"Trying SSD1305 with reset={reset_name}, cs={cs_name}, dc={dc_name}")
                        oled_reset = digitalio.DigitalInOut(reset_pin)
                        oled_cs = digitalio.DigitalInOut(cs_pin)
                        oled_dc = digitalio.DigitalInOut(dc_pin)
                        
                        # Initialize display
                        oled = adafruit_ssd1305.SSD1305_SPI(128, 64, spi_bus, oled_dc, oled_reset, oled_cs)
                        
                        # Clear display
                        oled.fill(0)
                        oled.show()
                        logger.info("Display cleared successfully")
                        
                        # Create blank image for drawing
                        image = Image.new("1", (oled.width, oled.height))
                        draw = ImageDraw.Draw(image)
                        
                        # Draw a test pattern
                        draw.rectangle((0, 0, oled.width, oled.height), outline=255, fill=0)
                        draw.text((10, 10), "SSD1305 Test", fill=255)
                        draw.text((10, 20), f"Reset={reset_name}", fill=255)
                        draw.text((10, 30), f"CS={cs_name}", fill=255)
                        draw.text((10, 40), f"DC={dc_name}", fill=255)
                        
                        # Display image
                        oled.image(image)
                        oled.show()
                        
                        logger.info("Test pattern displayed successfully")
                        logger.info(f"Please check if you can see the test pattern with this configuration")
                        
                        # Wait for user confirmation
                        if get_user_confirmation():
                            logger.info(f"✓ User confirmed SSD1305 display is working with reset={reset_name}, cs={cs_name}, dc={dc_name}")
                            working_configs.append({
                                "driver": "SSD1305",
                                "reset_pin": reset_name,
                                "cs_pin": cs_name,
                                "dc_pin": dc_name
                            })
                        else:
                            logger.info(f"✗ User reported SSD1305 display is NOT working with this configuration")
                        
                        # Clean up
                        oled.fill(0)
                        oled.show()
                        
                    except Exception as e:
                        logger.error(f"Error with SSD1305 configuration: {e}")
        
        if working_configs:
            logger.info(f"Found {len(working_configs)} working SSD1305 configurations")
            return working_configs
        else:
            logger.error("All SSD1305 configurations failed")
            return []
    except ImportError as e:
        logger.error(f"Could not import Adafruit libraries: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error testing SSD1305: {e}")
        return []

def run():
    """Main function to run the display tests"""
    logger.info("Starting display tests")
    all_working_configs = []
    
    # Ask user which drivers to test
    print("\nWhich display drivers would you like to test?")
    print("1. SSD1306 with luma.oled")
    print("2. SSD1305 with Adafruit")
    print("3. Both")
    
    while True:
        choice = input("Enter your choice (1-3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")
    
    # Test SSD1306 driver
    if choice in ['1', '3']:
        logger.info("\n=== Testing SSD1306 with luma.oled ===")
        ssd1306_configs = test_ssd1306_luma()
        all_working_configs.extend(ssd1306_configs)
    
    # Test SSD1305 driver
    if choice in ['2', '3']:
        logger.info("\n=== Testing SSD1305 with Adafruit ===")
        ssd1305_configs = test_ssd1305_adafruit()
        all_working_configs.extend(ssd1305_configs)
    
    # Print summary
    logger.info("\n=== Test Results Summary ===")
    
    if all_working_configs:
        logger.info(f"Found {len(all_working_configs)} working configurations:")
        for i, config in enumerate(all_working_configs, 1):
            if config["driver"] == "SSD1306":
                logger.info(f"{i}. SSD1306 (luma.oled): device={config['device']}, port={config['port']}")
            else:
                logger.info(f"{i}. SSD1305 (Adafruit): reset={config['reset_pin']}, cs={config['cs_pin']}, dc={config['dc_pin']}")
        
        # Ask which configuration to use
        if len(all_working_configs) > 1:
            print("\nWhich configuration would you like to use?")
            for i, config in enumerate(all_working_configs, 1):
                if config["driver"] == "SSD1306":
                    print(f"{i}. SSD1306 (luma.oled): device={config['device']}, port={config['port']}")
                else:
                    print(f"{i}. SSD1305 (Adafruit): reset={config['reset_pin']}, cs={config['cs_pin']}, dc={config['dc_pin']}")
            
            while True:
                choice = input(f"Enter your choice (1-{len(all_working_configs)}): ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(all_working_configs):
                        selected_config = all_working_configs[idx]
                        break
                    else:
                        print(f"Invalid choice. Please enter a number between 1 and {len(all_working_configs)}.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        else:
            selected_config = all_working_configs[0]
        
        # Print the selected configuration
        logger.info("\n=== Selected Configuration ===")
        if selected_config["driver"] == "SSD1306":
            logger.info(f"Driver: SSD1306 (luma.oled)")
            logger.info(f"Device: {selected_config['device']}")
            logger.info(f"Port: {selected_config['port']}")
            
            # Print code snippet for implementation
            print("\nUse this configuration in your code:")
            print("```python")
            print("from luma.core.interface.serial import spi")
            print("from luma.oled.device import ssd1306")
            print(f"serial_interface = spi(device={selected_config['device']}, port={selected_config['port']})")
            print("device = ssd1306(serial_interface)")
            print("```")
        else:
            logger.info(f"Driver: SSD1305 (Adafruit)")
            logger.info(f"Reset Pin: {selected_config['reset_pin']}")
            logger.info(f"CS Pin: {selected_config['cs_pin']}")
            logger.info(f"DC Pin: {selected_config['dc_pin']}")
            
            # Print code snippet for implementation
            print("\nUse this configuration in your code:")
            print("```python")
            print("import board")
            print("import digitalio")
            print("import adafruit_ssd1305")
            print(f"oled_reset = digitalio.DigitalInOut(board.{selected_config['reset_pin']})")
            print(f"oled_cs = digitalio.DigitalInOut(board.{selected_config['cs_pin']})")
            print(f"oled_dc = digitalio.DigitalInOut(board.{selected_config['dc_pin']})")
            print("spi = board.SPI()")
            print("oled = adafruit_ssd1305.SSD1305_SPI(128, 64, spi, oled_dc, oled_reset, oled_cs)")
            print("```")
    else:
        logger.info("No working configurations found.")
        logger.info("Recommendation: Check hardware connections and ensure libraries are installed")

if __name__ == "__main__":
    run()