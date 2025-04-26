"""
Proof of Concept (POC) scripts for the Gwent project.

This package contains various test scripts and demos for hardware components
used in the Gwent project, organized into the following directories:

- diagnostic_tools/: Utility scripts for diagnosing hardware issues
- display_tests/: Scripts for testing OLED displays (SSD1305, SSD1306) and LED matrix displays
- input_tests/: Scripts for testing rotary encoders (using RPi.GPIO and gpiozero)
- rfid_tests/: Scripts for testing RFID readers
- luma.examples/: Collection of examples for luma display libraries

See the README.md file in each directory for more information.
"""

# Import subpackages to make them available
from . import diagnostic_tools
from . import display_tests
from . import input_tests
from . import rfid_tests
from . import util