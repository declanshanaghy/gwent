# Proof of Concept (POC) Scripts

This directory contains proof-of-concept scripts used during the development of the Gwent project. These scripts were created to test and debug individual hardware components and functionality.

## Directory Structure

- **diagnostic_tools/**: Utility scripts for diagnosing hardware issues
  - `gpio_check.py`: Checks for GPIO pin conflicts that could affect hardware components

- **display_tests/**: Scripts for testing OLED displays
  - `display_test.py`: Tests multiple displays using a TCA9548A I2C multiplexer
  - `oled_test.py`: Tests OLED displays with both SSD1306 and SSD1305 drivers
  - `ssd1305_luma_demo.py`: Demo for SSD1305 displays using luma.oled library
  - `ssd1305_pillow_demo.py`: Demo for SSD1305 displays using Pillow library
  - `test_displays.py`: Additional display test script

- **input_tests/**: Scripts for testing input devices
  - `rotary_debug.py`: Diagnostic script for debugging rotary encoder issues
  - `rotary_gpiozero.py`: Rotary encoder implementation using gpiozero library
  - `rotary_rpigpio.py`: Rotary encoder implementation using RPi.GPIO library

- **rfid_tests/**: Scripts for testing RFID functionality
  - `rfid.py`: Test script for RFID card scanning

- **luma.examples/**: Collection of examples for luma display libraries

## Usage

These scripts are primarily for development and debugging purposes. They can be used to:

1. Test hardware components in isolation
2. Debug issues with specific hardware components
3. Understand how different components work
4. Serve as reference for implementing functionality in the main codebase

## Relationship to Main Codebase

Many of these POC scripts have corresponding implementations in the HAL (Hardware Abstraction Layer) directory:

- Display-related POC scripts → `gwent/hal/display.py`, `gwent/hal/oled_ssd1306.py`
- Rotary encoder POC scripts → `gwent/hal/rotary.py`, `gwent/hal/rotary_gpiozero.py`, `gwent/hal/rotary_rpigpio.py`
- RFID POC scripts → `gwent/hal/rfid.py`

The game functionality that uses these hardware components is implemented in the `gwent/game/` directory.