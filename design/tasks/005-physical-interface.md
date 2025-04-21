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
#### OLED Display
- Type: Monochrome 2.42" 128x64 OLED Graphic Display Module Kit (SSD1306)
- Protocol: SPI
- Recommended Python Library: luma.oled
- Purpose: Main output display for user interaction
- Power Pins:
  - Pin #1: Ground
  - Pin #2: 3V Power In
  - Pin #3: Not used
- Signal Pins (SPI Configuration):
  - Pin #4 (DC): GPIO24 - Data/Command pin
  - Pin #7 (Data0/CLK): GPIO11 (SPI0 SCLK)
  - Pin #8 (Data1/MOSI): GPIO10 (SPI0 MOSI)
  - Pin #15 (CS): GPIO8 (SPI0 CE0)
  - Pin #16 (RESET): GPIO25

#### Score Displays
- Type: LED Charlieplexed Matrix - 9x16 LEDs (IS31FL3731)
- Protocol: I2C
- I2C Address: 0x74 (for all displays, accessed via multiplexer)
- Recommended Python Library: adafruit-circuitpython-is31fl3731
- Game Score Display:
  - Quantity: 1 (Red)
  - Purpose: Display games won for each player
  - Multiplexer Channel: 0
- Player 1 Displays:
  - Quantity: 4 (Blue)
  - Purpose: Siege, Ranged, Close combat, and Total round scores
  - Multiplexer Channels: 1-4
- Player 2 Displays:
  - Quantity: 4 (Yellow)
  - Purpose: Siege, Ranged, Close combat, and Total round scores
  - Multiplexer Channels: 5-7

#### I2C Multiplexer
- Type: SparkFun Qwiic Mux Breakout - 8 Channel (TCA9548A)
- Protocol: I2C
- I2C Address: 0x70
- Recommended Python Library: qwiic_tca9548a
- Pins:
  - SDA: GPIO2 (I2C1 SDA)
  - SCL: GPIO3 (I2C1 SCL)
  - VCC: 3.3V
  - GND: Ground

#### Input Controls
- Rotary Encoder:
  - Type: PEC11 Series Rotary Encoder
  - Purpose: Menu navigation and selection
  - Interface: GPIO
  - Pins:
    - Common (C): Ground
    - A: GPIO7 with pull-up resistor
    - B: GPIO9 with pull-up resistor
    - SW: GPIO2 for push button
  - Features: 24 pulses per rotation, 4 steps per detent
- Push Buttons:
  - Quantity: 2
  - Purpose: Game control and menu selection
  - Interface: GPIO
  - Pins:
    - Button 1: GPIO17 with pull-up resistor
    - Button 2: GPIO27 with pull-up resistor

### Implementation Requirements
1. Connect OLED display to Raspberry Pi via SPI
2. Implement display interface code using luma.oled
3. Connect LED matrix displays via I2C multiplexer
4. Implement score display code using adafruit-circuitpython-is31fl3731
5. Connect rotary encoder and buttons to GPIO pins
6. Implement input handling code using py-gaugette
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