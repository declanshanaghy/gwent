# Display Tests

This directory contains scripts for testing and debugging OLED displays used in the Gwent project.

## Scripts

### oled_test.py

A diagnostic tool for testing OLED displays with both SSD1306 and SSD1305 drivers.

#### Features:
- Tests both SSD1306 (with luma.oled) and SSD1305 (with Adafruit) drivers
- Tries different configurations (device, port, pins) to find working setups
- Provides code snippets for implementing the working configuration

#### Usage:
```bash
python oled_test.py
```

### TCA9548A-MatrixI2C-test.py

Tests multiple displays using a TCA9548A I2C multiplexer.

#### Features:
- Cycles through connected displays on specified channels
- Draws borders and text on each display
- Handles errors gracefully with helpful messages

#### Usage:
```bash
python TCA9548A-MatrixI2C-test.py
```

### ssd1305_luma_demo.py

Demo script for SSD1305 displays using the luma.oled library.

#### Usage:
```bash
python ssd1305_luma_demo.py
```

### ssd1305_pillow_demo.py

Demo script for SSD1305 displays using the Pillow library.

#### Usage:
```bash
python ssd1305_pillow_demo.py
```

## Troubleshooting

If you encounter issues with the displays:

1. Check that I2C or SPI is enabled on your Raspberry Pi
   - For I2C: `sudo raspi-config > Interface Options > I2C > Enable`
   - For SPI: `sudo raspi-config > Interface Options > SPI > Enable`

2. Verify the connections to your display
   - For SPI: Check MOSI, MISO, SCLK, CS, DC, and RST pins
   - For I2C: Check SDA and SCL pins

3. Run `oled_test.py` to systematically test different configurations