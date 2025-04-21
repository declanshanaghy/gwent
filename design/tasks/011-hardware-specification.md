# Task 011: Hardware Component Specification

## Description
Document detailed specifications for all hardware components including communication protocols, GPIO pins, I2C addresses, and required Python libraries.

## Priority
🔴 High

## Status
🟢 Completed

## Dependencies
- Task 001: Setup Raspberry Pi Development Environment

## Details
Created comprehensive hardware specifications including: RFID-RC522 reader with GPIO pin assignments, rotary encoder and push button input systems with pin mappings, I2C multiplexer (TCA9548A) configuration at address 0x70, LED matrix displays (IS31FL3731) at address 0x74 for score displays, SSD1306 OLED display with SPI configuration, power requirements, and a complete GPIO pin assignment table. Documented all required Python libraries including mfrc522-python, gaugette, qwiic_tca9548a, adafruit-circuitpython-is31fl3731, and luma.oled.

### Hardware Components
#### Raspberry Pi
- Model: Raspberry Pi 3 Model B (2GB RAM minimum)
- Processor: Broadcom BCM2711, Quad core Cortex-A72 (ARM v8) 64-bit SoC @ 1.5GHz
- Memory: 2GB LPDDR4-3200 SDRAM
- Storage: 32GB microSD card (Class 10 minimum)
- Power: 5V/3A USB power supply
- Connectivity:
  - 2.4 GHz and 5.0 GHz IEEE 802.11ac wireless
  - Bluetooth 5.0
  - Gigabit Ethernet
  - 2 × USB 3.0 ports
  - 2 × USB 2.0 ports

#### RFID Reader
- Model: RFID-RC522
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

#### LED Matrix Displays
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

#### OLED Display
- Type: Monochrome 2.42" 128x64 OLED Graphic Display Module Kit (SSD1306)
- Protocol: SPI
- Hardware Jumper Configuration
  - BS1=0
  - BS2=0
- Recommended Python Library: luma.oled
- Power Pins:
  - Pin #1: Ground
  - Pin #2: 3V Power In
  - Pin #3: Not used
- Signal Pins (SPI Configuration):
  - Pin #4 (DC): GPIO24 - Data/Command pin
  - Pin #7 (Data0/CLK): GPIO11 (SPI0 SCLK)
  - Pin #8 (Data1/MOSI): GPIO10 (SPI0 MOSI)
  - Pin #15 (CS): GPIO7 (SPI0 CE1)
  - Pin #16 (RESET): GPIO25

#### Input Controls
- Rotary Encoder:
  - Type: PEC11 Series Rotary Encoder
  - Recommended Python Library: py-gaugette
  - Pins:
    - Common (C): Ground
    - A: GPIO7 with pull-up resistor
    - B: GPIO9 with pull-up resistor
    - SW: GPIO2 for push button
  - Features: 24 pulses per rotation, 4 steps per detent
- Push Buttons:
  - Quantity: 2
  - Pins:
    - Button 1: GPIO17 with pull-up resistor
    - Button 2: GPIO27 with pull-up resistor

### GPIO Pin Assignment Table
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
| I2C SDA | GPIO2 | Pin 3 | I2C data |
| I2C SCL | GPIO3 | Pin 5 | I2C clock |
| OLED DC | GPIO24 | Pin 18 | OLED data/command |
| OLED CLK | GPIO11 | Pin 23 | SPI clock |
| OLED MOSI | GPIO10 | Pin 19 | SPI MOSI |
| OLED CS | GPIO8 | Pin 24 | SPI chip select |
| OLED RESET | GPIO25 | Pin 22 | OLED reset |

### GPIO Pin Conflict Management
The hardware design has several GPIO pin conflicts that must be managed in software:

1. **GPIO9 Conflict**: Shared between RFID-RC522 MISO and Rotary Encoder B
   - Solution: Careful timing of operations to avoid simultaneous access

2. **GPIO2 Conflict**: Shared between Rotary Encoder SW and I2C SDA
   - Solution: Software must manage I2C transactions to avoid interference with button presses

3. **GPIO3 Conflict**: Shared between Power Button and I2C SCL
   - Solution: Power management must be aware of I2C bus activity

4. **SPI Bus Sharing**: Between RFID reader and OLED display
   - Solution: Implement proper chip select management and bus arbitration

### Required Python Libraries
- mfrc522-python: For RFID reader
- gaugette: For rotary encoder
- qwiic_tca9548a: For I2C multiplexer
- adafruit-circuitpython-is31fl3731: For LED matrix displays
- luma.oled: For SSD1306 OLED display
- RPi.GPIO: Basic GPIO control
- gpiozero: High-level GPIO interface
- Adafruit-Blinka: CircuitPython support for Raspberry Pi
- busio: For I2C and SPI communication
- board: For pin definitions
- adafruit_framebuf: For display frame buffer operations

## Test Strategy
Verify hardware specifications against physical component datasheets, confirm GPIO pin assignments for non-conflicting usage, test I2C address configurations with i2cdetect utility, validate SPI device configurations, and test each component with their specified Python libraries to ensure compatibility and functionality.

### Test Cases
1. Verify hardware specifications against physical component datasheets
2. Confirm GPIO pin assignments for non-conflicting usage
3. Test I2C address configurations with i2cdetect utility
4. Validate SPI device configurations
5. Test each component with their specified Python libraries
6. Verify power requirements and consumption
7. Test GPIO pin conflict management solutions
8. Validate hardware integration in prototype assembly