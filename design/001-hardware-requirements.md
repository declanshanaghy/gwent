# Hardware Requirements Specification

## 1. Raspberry Pi Specifications

### 1.1 Minimum Requirements
- Model: Raspberry Pi 3 Model B (2GB RAM minimum)
- Processor: Broadcom BCM2711, Quad core Cortex-A72 (ARM v8) 64-bit SoC @ 1.5GHz
- Memory: 2GB LPDDR4-3200 SDRAM
- Storage: 32GB microSD card (Class 10 minimum)
- Power: 5V/3A USB power supply

### 1.2 Connectivity
- 2.4 GHz and 5.0 GHz IEEE 802.11ac wireless
- Bluetooth 5.0
- Gigabit Ethernet
- 2 × USB 3.0 ports
- 2 × USB 2.0 ports

## 2. RFID System

### 2.1 Reader Specifications
- Model: RFID-RC522
- Reference: https://pypi.org/project/mfrc522-python/
- Frequency: 13.56 MHz (HF)
- Read Range: Up to 10cm
- Read Speed: < 100ms per card
- Interface: GPIO
- Power: 5V DC
- Recommended Python Library: mfrc522-python
- Pins:
  | RF522 Module | Raspberry Pi |
  | ------------ | ------------ |
  | SDA          | Pin 24 / GPIO8 (CE0) |
  | SCK          | Pin 23 / GPIO11 (SCKL) |
  | MOSI         | Pin 19 / GPIO10 (MOSI) |
  | MISO         | Pin 21 / GPIO9 (MISO) |
  | IRQ          | – |
  | GND          | GND |
  | RST          | Pin 22 / GPIO25 |
  | 3.3V         | 3.3V |

### 2.2 Card Specifications
- Type: ISO/IEC 14443 Type A
- Memory: 1KB minimum
- Operating Frequency: 13.56 MHz
- Read/Write Cycles: 100,000 minimum
- Physical Size: Standard playing card dimensions

## 3. Input System

### 3.1 Rotary Encoder
- Type: PEC11 Series Rotary Encoder
- Reference: https://www.adafruit.com/products/377
- Implementation Reference: https://github.com/guyc/py-gaugette
- Purpose: Menu navigation and selection
- Interface: GPIO
- Recommended Python Library: gaugette
- Pins:
  - Common (C): Ground
  - A: GPIO7 (Wiring Pin 1) with pull-up resistor
  - B: GPIO9 (Wiring Pin 0) with pull-up resistor
  - SW: GPIO2 (Wiring Pin 2) for push button
- Features:
  - Detent feedback
  - Push button functionality
  - 24 pulses per rotation
  - 4 steps per detent

### 3.2 Push Buttons
- Type: Tactile Push Button
- Quantity: 2
- Purpose: Game control and menu selection
- Interface: GPIO
- Recommended Python Library: RPi.GPIO or gpiozero
- Pins:
  - Button 1: GPIO17 with pull-up resistor
  - Button 2: GPIO27 with pull-up resistor
- Features:
  - Tactile feedback
  - Debounce protection
  - Minimum 100,000 press lifecycle

### 3.3 Additional Controls
- Power button: Connected to GPIO3
- Reset button: Connected to GPIO2
- Menu navigation buttons: Connected to GPIO22 and GPIO23

## 4. Output System

### 4.1 Score Display Coordinator
- Type: SparkFun Qwiic Mux Breakout - 8 Channel (TCA9548A)
- Protocol: I2C
- I2C Address: 0x70
- Reference: https://www.sparkfun.com/sparkfun-qwiic-mux-breakout-8-channel-tca9548a.html
- Implementation Reference: https://learn.sparkfun.com/tutorials/qwiic-mux-hookup-guide
- Recommended Python Library: qwiic_tca9548a
- Purpose: Enables communication with multiple I2C devices that have the same address
- Pins:
  - SDA: GPIO2 (I2C1 SDA)
  - SCL: GPIO3 (I2C1 SCL)
  - VCC: 3.3V
  - GND: Ground

### 4.2 Score Displays
- Type: LED Charlieplexed Matrix - 9x16 LEDs (IS31FL3731)
- Protocol: I2C
- I2C Address: 0x74 (for all displays, accessed via multiplexer)
- Reference: https://www.adafruit.com/product/2947
- Integration Reference: https://learn.adafruit.com/i31fl3731-16x9-charliplexed-pwm-led-driver/downloads
- Recommended Python Library: adafruit-circuitpython-is31fl3731
- Game Score Display:
  - Quantity: 1 (Red)
  - Purpose: Display games won for each player (e.g. "2-1")
  - Digits: 3 (including separator)
  - Multiplexer Channel: 0
- Player 1 Displays:
  - Quantity: 4 (Blue)
  - Purpose:
    - Siege row score
    - Ranged row score
    - Close combat row score
    - Total round score
  - Digits: 3 per display
  - Multiplexer Channels: 1-4
- Player 2 Displays:
  - Quantity: 4 (Yellow)
  - Purpose:
    - Siege row score
    - Ranged row score
    - Close combat row score
    - Total round score
  - Digits: 3 per display
  - Multiplexer Channels: 5-7
- Power: 5V DC

### 4.3 Menu Display
- Type: Monochrome 2.42" 128x64 OLED Graphic Display Module Kit (SSD1306)
- Protocol: SPI
- Reference: https://www.adafruit.com/product/2719
- Implementation Example: https://learn.adafruit.com/1-5-and-2-4-monochrome-128x64-oled-display-module
- Recommended Python Library: luma.oled
- Purpose: Main output display for user interaction. Displays selection menu for control of the game.
- Power Pins:
  - Pin #1: Ground
  - Pin #2: 3V Power In - provide 3V with 50-75mA current capability
  - Pin #3: Not used, do not connect to anything
- Signal Pins (SPI Configuration):
  - Pin #4 (DC): GPIO24 - Data/Command pin
  - Pin #7 (Data0/CLK): GPIO11 (SPI0 SCLK)
  - Pin #8 (Data1/MOSI): GPIO10 (SPI0 MOSI)
  - Pin #15 (CS): GPIO8 (SPI0 CE0)
  - Pin #16 (RESET): GPIO25
- Remaining Pins:
  - Pins #5, #6, #9-14, #17-19: Not connected, do not use
  - Pin #20: Frame ground, can connect to ground or leave floating

## 5. Power System

### 5.1 Power Requirements
- Input: 5V DC
- Current: 3A minimum
- Battery backup: Optional
- Power management: Automatic sleep mode

### 5.2 Protection
- Overvoltage protection
- Overcurrent protection
- Reverse polarity protection

## 6. Physical Design

### 6.1 Enclosure
- Material: ABS plastic
- Dimensions: To be determined
- Mounting: Tabletop or wall mount options
- Ventilation: Adequate for heat dissipation

### 6.2 Game Mat
- Material: Cloth with RFID-friendly properties
- Size: Standard Gwent play area
- RFID antenna integration: None (reader in companion device)

## 7. Environmental Requirements

### 7.1 Operating Conditions
- Temperature: 0°C to 40°C
- Humidity: 20% to 80% non-condensing
- Altitude: 0 to 2000m

### 7.2 Storage Conditions
- Temperature: -20°C to 60°C
- Humidity: 10% to 90% non-condensing

## 8. Compliance Requirements

### 8.1 Certifications
- CE marking
- FCC certification
- RoHS compliance

### 8.2 Safety Standards
- EN 60950-1
- UL 60950-1
- IEC 60950-1

## 9. Maintenance Requirements

### 9.1 Serviceability
- Modular design for easy component replacement
- Accessible components
- Clear maintenance procedures

### 9.2 Cleaning
- Exterior cleaning procedures
- Component cleaning guidelines
- Maintenance schedule

## 10. Recommended Python Libraries

### 10.1 Core Libraries
- RPi.GPIO: Basic GPIO control
- gpiozero: High-level GPIO interface
- Adafruit-Blinka: CircuitPython support for Raspberry Pi

### 10.2 Component-Specific Libraries
- mfrc522-python: For RFID reader
- gaugette: For rotary encoder
- qwiic_tca9548a: For I2C multiplexer
- adafruit-circuitpython-is31fl3731: For LED matrix displays
- luma.oled: For SSD1306 OLED display
- busio: For I2C and SPI communication
- board: For pin definitions
- adafruit_framebuf: For display frame buffer operations

## 11. GPIO Pin Assignment Table

| Component | GPIO Pin | Pin Number | Function |
|-----------|---------|------------|----------|
| RFID-RC522 SDA | GPIO8 | Pin 24 | SPI CE0 |
| RFID-RC522 SCK | GPIO11 | Pin 23 | SPI SCLK |
| RFID-RC522 MOSI | GPIO10 | Pin 19 | SPI MOSI |
| RFID-RC522 MISO | GPIO9 | Pin 21 | SPI MISO |
| RFID-RC522 RST | GPIO25 | Pin 22 | Reset |
| Rotary Encoder A | GPIO7 | Pin 26 | Encoder A input |
| Rotary Encoder B | GPIO9 | Pin 21 | Encoder B input |
| Rotary Encoder SW | GPIO2 | Pin 3 | Encoder push button |
| Push Button 1 | GPIO17 | Pin 11 | Game control |
| Push Button 2 | GPIO27 | Pin 13 | Game control |
| Power Button | GPIO3 | Pin 5 | Power control |
| Reset Button | GPIO2 | Pin 3 | System reset |
| I2C SDA | GPIO2 | Pin 3 | I2C data |
| I2C SCL | GPIO3 | Pin 5 | I2C clock |
| OLED DC | GPIO24 | Pin 18 | OLED data/command |
| OLED CLK | GPIO11 | Pin 23 | SPI clock |
| OLED MOSI | GPIO10 | Pin 19 | SPI MOSI |
| OLED CS | GPIO8 | Pin 24 | SPI chip select |
| OLED RESET | GPIO25 | Pin 22 | OLED reset |