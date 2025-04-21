"""
Pytest configuration file for the gwent project.
This file contains common fixtures and setup for the tests.
"""

from __future__ import annotations

import os
import sys
import platform
import pytest
import importlib.util
import datetime
import pathlib
from typing import Dict, Any, Optional, Generator

# Add the parent directory to the Python path
# This allows the tests to import from the gwent package
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import the logging module from gwent
from gwent.utils.logging import configure_logging

# Create test results directory if it doesn't exist
TEST_RESULTS_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "test-results"
))
os.makedirs(TEST_RESULTS_DIR, exist_ok=True)

# Generate timestamp for this test run
TEST_TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_raspberry_pi() -> None:
    """
    Ensure the current system is a Raspberry Pi.
    Exits with an error if not running on Raspberry Pi hardware.
    """
    import logging
    logger = logging.getLogger("hardware_test")
    
    # Check if the platform is Linux
    if not platform.system() == 'Linux':
        logger.error("This application must run on Raspberry Pi hardware")
        logger.error("Current platform is not Linux")
        sys.exit(1)
    
    # Check for Raspberry Pi model in /proc/cpuinfo
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        if not ('Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo or 'ARM' in cpuinfo):
            logger.error("This application must run on Raspberry Pi hardware")
            logger.error("CPU information does not match Raspberry Pi")
            sys.exit(1)
    except Exception as e:
        # If we can't read the file, check for Pi-specific hardware
        if not (os.path.exists('/dev/gpiomem') and os.path.exists('/dev/i2c-1')):
            logger.error(f"This application must run on Raspberry Pi hardware: {e}")
            logger.error("Could not find Raspberry Pi specific hardware")
            sys.exit(1)
    
    logger.info("Verified Raspberry Pi hardware")

# Configure pytest to always generate XML output
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with XML output and logging."""
    # Set up the XML output file
    xml_path = os.path.join(TEST_RESULTS_DIR, f"hardware_test_{TEST_TIMESTAMP}.xml")
    config.option.xmlpath = xml_path
    
    # Set up the log file with the same timestamp
    log_path = os.path.join(TEST_RESULTS_DIR, f"hardware_test_{TEST_TIMESTAMP}.log")
    configure_logging(log_file=log_path)
    
    # Log the start of the test session
    import logging
    logger = logging.getLogger("pytest")
    logger.info(f"Starting test session at {datetime.datetime.now().isoformat()}")
    logger.info(f"Test results will be saved to {xml_path}")
    logger.info(f"Logs will be saved to {log_path}")

@pytest.fixture(scope="session")
def raspberry_pi_hw() -> Generator[Dict[str, Any], None, None]:
    """
    Pytest fixture for Raspberry Pi hardware testing.
    
    This fixture:
    1. Ensures the test is running on a Raspberry Pi (exits if not)
    2. Initializes hardware components (GPIO, SPI, I2C, display, rotary encoder, etc.)
    3. Provides access to these components for tests
    4. Properly cleans up resources after tests
    
    Returns:
        dict: A dictionary containing initialized hardware components
    """
    # Log the start of hardware initialization
    import logging
    logger = logging.getLogger("hardware_test")
    logger.info("Initializing Raspberry Pi hardware components")
    
    # Ensure we're running on a Raspberry Pi (will exit if not)
    ensure_raspberry_pi()
    
    # Initialize hardware components
    hw_components = {}
    
    # Initialize GPIO
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        hw_components['gpio'] = GPIO
    except (ImportError, RuntimeError):
        pytest.skip("GPIO initialization failed")
        return None
    
    # Initialize SPI for display
    try:
        from luma.core.interface.serial import spi
        from luma.oled.device import ssd1306
        
        serial = spi(device=1, port=0, gpio_DC=24, gpio_RST=25, gpio_CS=7)
        display = ssd1306(serial, width=128, height=64, rotate=0)
        hw_components['display'] = display
    except (ImportError, RuntimeError, OSError) as e:
        print(f"Display initialization failed: {e}")
        # Continue even if display fails, other components might work
    
    # Initialize Rotary Encoder
    try:
        from gwent.hal.rotary import RotaryEncoder
        rotary = RotaryEncoder(a_pin=17, b_pin=18, sw_pin=27)
        rotary.start_monitoring()
        hw_components['rotary'] = rotary
    except (ImportError, RuntimeError, OSError) as e:
        print(f"Rotary encoder initialization failed: {e}")
        # Continue even if rotary fails, other components might work
    
    # Initialize RFID reader
    try:
        if importlib.util.find_spec("mfrc522"):
            from gwent.hal.rfid import RFIDReader
            rfid = RFIDReader()
            hw_components['rfid'] = rfid
    except (ImportError, RuntimeError, OSError) as e:
        print(f"RFID reader initialization failed: {e}")
        # Continue even if RFID fails, other components might work
    
    # Initialize Audio
    try:
        from gwent.hal.audio import AudioPlayer
        audio = AudioPlayer()
        hw_components['audio'] = audio
    except (ImportError, RuntimeError, OSError) as e:
        print(f"Audio initialization failed: {e}")
        # Continue even if audio fails, other components might work
    
    # Yield the hardware components for tests to use
    yield hw_components
    
    # Clean up resources
    try:
        if 'rotary' in hw_components:
            hw_components['rotary'].cleanup()
        
        if 'display' in hw_components:
            hw_components['display'].cleanup()
        
        if 'audio' in hw_components:
            hw_components['audio'].cleanup()
        
        if 'rfid' in hw_components:
            hw_components['rfid'].cleanup()
        
        if 'gpio' in hw_components:
            # Clean up GPIO pins without affecting other components
            # Only clean up pins that were explicitly set by our tests
            hw_components['gpio'].cleanup()
    except Exception as e:
        print(f"Error during hardware cleanup: {e}")