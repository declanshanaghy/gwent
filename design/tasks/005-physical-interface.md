# Task 005: Create Physical Interface Controls

## Description
Implement the hardware interface including display, buttons, and rotary encoder for direct interaction with the companion device.

## Priority
🟠 Medium

## Status
🟢 Completed

## Dependencies
- Task 001: Setup Raspberry Pi Development Environment

## Details
Connect display to Raspberry Pi, implement display interface code, integrate rotary encoder and buttons, develop menu navigation system, create score visualization screens, and implement player prompts and error messages.

### Hardware Components
> Canonical pin assignments and library imports are documented in [011-hardware-specification.md](011-hardware-specification.md). The summary below mirrors that doc; if anything diverges, 011 wins.

#### OLED Display
- Type: Monochrome 2.42" 128x64 OLED Graphic Display Module (SSD1306)
- Protocol: SPI (4-wire, BS1=BS2=0)
- Library: `luma.oled` (`luma.oled.device.ssd1306`)
- Purpose: Main output display for menus, prompts, and card details
- Signal Pins:
  - DC: GPIO24 (Pin 18)
  - CLK: GPIO11 (Pin 23, SPI0 SCLK)
  - MOSI: GPIO10 (Pin 19, SPI0 MOSI)
  - CS: GPIO7 (Pin 26, SPI0 **CE1**)
  - RESET: GPIO25 (Pin 22) — **shared with MFRC522 RFID reset**, pulsed manually in `hal/oled_ssd1306.py`
- Power: 3.3V, GND

#### Score / Gem Displays
- Type: Adafruit IS31FL3731 9x16 charlieplex matrix breakout
- Protocol: I2C (via TCA9548A multiplexer; all matrices share address 0x74)
- Library: `adafruit_is31fl3731` (CircuitPython, via `adafruit-blinka`)
- Quantity: 3 displays
  - Mux Channel 0 — Round/gem display (lives), shows P1/P2 remaining gems as diamond shapes
  - Mux Channel 1 — Player 1 score, large centered digit with star indicator when active
  - Mux Channel 2 — Player 2 score, large centered digit with star indicator when active

#### I2C Multiplexer
- Type: SparkFun Qwiic Mux Breakout — 8-Channel (TCA9548A)
- Protocol: I2C1 (SDA=GPIO2 Pin 3, SCL=GPIO3 Pin 5)
- I2C Address: 0x70
- Library: `qwiic_tca9548a`
- Channels in use: 0, 1, 2 (3–7 unused)

#### Input Controls
- Rotary Encoder (with integrated push button):
  - Type: PEC11 series rotary encoder
  - Purpose: Menu navigation, selection, and play/pass decisions
  - Library: `pigpio` (via `gwent.hal.rotary_pigpio.PiGPIORotaryEncoder`); requires `pigpiod` daemon
  - Pins (BCM, all with internal pull-up):
    - A: GPIO17 (Pin 11)
    - B: GPIO22 (Pin 15)
    - SW: GPIO27 (Pin 13)
    - Common: GND
  - Features: 24 pulses/rotation, 4 steps per detent, 50 ms switch debounce

There are no separate push buttons. Game control and menu selection are entirely handled by the rotary encoder's integrated switch. Earlier drafts referenced two extra buttons on GPIO17/27, but those references were aspirational and the pins are now used by the rotary encoder itself.

### Implementation Requirements
1. Connect OLED display to Raspberry Pi via SPI
2. Implement display interface code using luma.oled
3. Connect LED matrix displays via I2C multiplexer
4. Implement score display code using adafruit-circuitpython-is31fl3731
5. Connect rotary encoder to GPIO pins
6. Implement input handling code using `pigpio` (and ensure the `pigpiod` daemon is enabled at boot)
7. Develop menu navigation system
8. Create score visualization screens
9. Implement player prompts and error messages
10. Develop a consistent UI design across all displays

### User Interface Requirements
- Clear, readable text on OLED display
- Intuitive menu navigation using rotary encoder
- Responsive input controls with feedback
- Consistent visual design across all displays
- Error messages that are clear and actionable
- Score displays that are easily readable from a distance

## Test Strategy
Test physical controls for durability and responsiveness, validate display readability, verify menu navigation flows, and conduct usability testing with sample users.

### Test Cases
1. Verify OLED display functionality and readability
2. Test LED matrix displays for brightness and clarity
3. Validate rotary encoder navigation and selection
4. Test button responsiveness and durability
5. Verify menu navigation flows
6. Test score visualization accuracy
7. Validate error message display
8. Conduct usability testing with sample users
9. Test input handling under various conditions
10. Verify display updates during gameplay