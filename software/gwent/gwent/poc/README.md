# Proof of Concept (POC) Scripts

Test and diagnostic scripts for individual hardware components.

## Directory Structure

- **diagnostic_tools/**: Hardware diagnostic utilities
  - `gpio_check.py`: Check for GPIO pin conflicts
  - `gpio_service_manager.py`: Manage GPIO service status
  - `mfd_diagnostic.py`: Multi-Function Display diagnostic
  - `audio_diagnostic.py`: Audio system diagnostic

- **display_tests/**: OLED and LED matrix display tests
  - `display_test.py`: Tests multiple displays via TCA9548A I2C multiplexer
  - `oled_test.py`: SSD1306 OLED display tests

- **input_tests/**: Rotary encoder tests
  - `rotary_pigpio.py`: PiGPIO rotary encoder test (the implementation used in production)

- **rfid_tests/**: RFID card reader tests
  - `rfid.py`: MFRC522 card scanning test

- **util/**: Card management utilities
  - `card_manager.py`: Read/write RFID card data

## Hardware

| Component | Interface | HAL Module |
|-----------|-----------|------------|
| SSD1306 OLED | SPI (CE1) | `gwent.hal.oled_ssd1306` |
| MFRC522 RFID | SPI (CE0) | `gwent.hal.rfid` |
| IS31FL3731 LED Matrix x3 | I2C via TCA9548A (Ch 0,1,2) | `gwent.hal.matrix` |
| Rotary Encoder | GPIO (pigpio) | `gwent.hal.rotary` / `gwent.hal.rotary_pigpio` |

### GPIO Pins

| Pin | Function |
|-----|----------|
| GPIO17 | Rotary Encoder A |
| GPIO22 | Rotary Encoder B |
| GPIO27 | Rotary Encoder Switch |
| GPIO24 | OLED DC |
| GPIO25 | OLED Reset |
| GPIO7 (CE1) | OLED Chip Select |
| GPIO8 (CE0) | MFRC522 Chip Select |
