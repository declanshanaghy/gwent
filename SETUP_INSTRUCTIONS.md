# Gwent Raspberry Pi Development Environment Setup

This document provides instructions for setting up a Raspberry Pi development environment for the Gwent project.

**Note:** The original asyncio-based implementation has been moved to `software/gwent-asyncio`. The new implementation in `software/gwent` is designed to be compatible with the hardware libraries.

## Prerequisites

- Raspberry Pi 3 Model B (or newer) with at least 2GB RAM
- Raspberry Pi OS (64-bit) installed
- Internet connection
- Connected hardware components (RFID reader, OLED display, rotary encoder, etc.)

## Hardware Components

The Gwent project uses the following hardware components:

1. **RFID Reader (RFID-RC522)**
   - Used for reading RFID-enabled Gwent cards
   - Connected via SPI interface

2. **OLED Display (SSD1306)**
   - Used for menu display and user interface
   - Connected via SPI interface

3. **LED Matrix Displays (IS31FL3731)**
   - Used for score display
   - Connected via I2C interface through a multiplexer

4. **I2C Multiplexer (TCA9548A)**
   - Used to manage multiple I2C devices
   - Connected via I2C interface

5. **Rotary Encoder (PEC11 Series)**
   - Used for user input and menu navigation
   - Connected via GPIO pins

## GPIO Pin Connections

Based on the implementation in the `software/gwent/gwent/hal` directory, here are the actual GPIO pin connections used in the code:

| Component | GPIO Pin | Pin Number | Function |
|-----------|---------|------------|----------|
| RFID-RC522 SDA | GPIO8 | Pin 24 | SPI CE0 |
| RFID-RC522 SCK | GPIO11 | Pin 23 | SPI SCLK |
| RFID-RC522 MOSI | GPIO10 | Pin 19 | SPI MOSI |
| RFID-RC522 MISO | GPIO9 | Pin 21 | SPI MISO |
| RFID-RC522 RST | GPIO25 | Pin 22 | Reset |
| Rotary Encoder A | GPIO17 | Pin 11 | Encoder A input |
| Rotary Encoder B | GPIO22 | Pin 15 | Encoder B input |
| Rotary Encoder SW | GPIO27 | Pin 13 | Encoder push button |
| I2C SDA | GPIO2 | Pin 3 | I2C data |
| I2C SCL | GPIO3 | Pin 5 | I2C clock |
| OLED DC | GPIO24 | Pin 18 | OLED data/command |
| OLED CLK | GPIO11 | Pin 23 | SPI clock |
| OLED MOSI | GPIO10 | Pin 19 | SPI MOSI |
| OLED CS | GPIO7 | Pin 26 | SPI chip select (CE1) |
| OLED RESET | GPIO25 | Pin 22 | OLED reset |

### Raspberry Pi GPIO Pinout Diagram

```mermaid
graph TB
    classDef physical fill:#f9f9f9,stroke:#333,stroke-width:1px
    classDef gpio fill:#d9ead3,stroke:#333,stroke-width:1px
    classDef power fill:#f4cccc,stroke:#333,stroke-width:1px
    classDef ground fill:#d9d2e9,stroke:#333,stroke-width:1px
    classDef spi fill:#fff2cc,stroke:#333,stroke-width:1px
    classDef i2c fill:#cfe2f3,stroke:#333,stroke-width:1px
    classDef uart fill:#ead1dc,stroke:#333,stroke-width:1px
    classDef used fill:#76a5af,stroke:#333,stroke-width:2px,color:#fff
    
    subgraph "Raspberry Pi GPIO Pinout"
        p1[1: 3.3V]:::power --- p2[2: 5V]:::power
        p3[3: GPIO2/SDA]:::i2c --- p4[4: 5V]:::power
        p5[5: GPIO3/SCL]:::i2c --- p6[6: GND]:::ground
        p7[7: GPIO4]:::gpio --- p8[8: GPIO14/TXD]:::uart
        p9[9: GND]:::ground --- p10[10: GPIO15/RXD]:::uart
        p11[11: GPIO17]:::used --- p12[12: GPIO18]:::gpio
        p13[13: GPIO27]:::used --- p14[14: GND]:::ground
        p15[15: GPIO22]:::used --- p16[16: GPIO23]:::gpio
        p17[17: 3.3V]:::power --- p18[18: GPIO24]:::used
        p19[19: GPIO10/MOSI]:::used --- p20[20: GND]:::ground
        p21[21: GPIO9/MISO]:::used --- p22[22: GPIO25]:::used
        p23[23: GPIO11/SCLK]:::used --- p24[24: GPIO8/CE0]:::used
        p25[25: GND]:::ground --- p26[26: GPIO7/CE1]:::used
        p27[27: ID_SD]:::i2c --- p28[28: ID_SC]:::i2c
        p29[29: GPIO5]:::gpio --- p30[30: GND]:::ground
        p31[31: GPIO6]:::gpio --- p32[32: GPIO12]:::gpio
        p33[33: GPIO13]:::gpio --- p34[34: GND]:::ground
        p35[35: GPIO19]:::gpio --- p36[36: GPIO16]:::gpio
        p37[37: GPIO26]:::gpio --- p38[38: GPIO20]:::gpio
        p39[39: GND]:::ground --- p40[40: GPIO21]:::gpio
    end
    
    %% Component connections
    rotary_a[Rotary Encoder A]:::used --- p11
    rotary_b[Rotary Encoder B]:::used --- p15
    rotary_sw[Rotary Encoder SW]:::used --- p13
    oled_dc[OLED DC]:::used --- p18
    oled_reset[OLED RESET]:::used --- p22
    oled_cs[OLED CS]:::used --- p26
    rfid_sda[RFID SDA]:::used --- p24
    rfid_miso[RFID MISO]:::used --- p21
    rfid_mosi[RFID MOSI]:::used --- p19
    rfid_sck[RFID SCK]:::used --- p23
    rfid_rst[RFID RST]:::used --- p22
    i2c_sda[I2C SDA]:::i2c --- p3
    i2c_scl[I2C SCL]:::i2c --- p5
```

**Note:** The following GPIO pins are shared between components:
- GPIO25 is shared between RFID-RC522 RST and OLED RESET
- SPI bus (GPIO10/MOSI, GPIO11/SCLK) is shared between RFID reader and OLED display

For a detailed visual reference of the Raspberry Pi GPIO pinout, you can also refer to this image:
[Raspberry Pi GPIO Pinout](https://i0.wp.com/randomnerdtutorials.com/wp-content/uploads/2023/03/Raspberry-Pi-Pinout-Random-Nerd-Tutorials.png?quality=100&strip=all&ssl=1)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/declanshanaghy/gwent.git
cd gwent
```

### 2. Run the Setup Script

The setup script will install all necessary dependencies, configure the system, and set up the Python environment.

```bash
sudo ./setup_raspberry_pi.sh
```

The script performs the following actions:
- Updates the system packages
- Installs system dependencies
- Installs WiringPi
- Enables SPI and I2C interfaces
- Adds the user to required groups
- Creates a Python virtual environment
- Installs Python packages
- Configures services (MQTT, Redis)
- Creates a hardware test script
- Creates a convenience script to activate the virtual environment

### 3. Reboot the Raspberry Pi

After the setup script completes, reboot the Raspberry Pi to apply all changes:

```bash
sudo reboot
```

### 4. Activate the Virtual Environment

After rebooting, activate the virtual environment:

```bash
source ./activate_gwent.sh
```

### 5. Test the Hardware

Run the hardware test script to verify that all components are working correctly:

```bash
python ./test_hardware.py
```

The test script will check:
- GPIO functionality
- SPI interface
- I2C interface
- RFID reader
- OLED display
- Rotary encoder
- MQTT broker
- Redis server

### 6. Run the Gwent Game

Once everything is set up and tested, you can run the Gwent game:

```bash
gwent
```

You can also use the card tools to read and write RFID cards:

```bash
# Read a card
read_card

# Write a card
write_card
```

### 7. Development

The new Gwent implementation is structured as follows:

```
software/gwent/
├── gwent/
│   ├── __init__.py
│   ├── game/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── card_tools.py
│   ├── hal/
│   │   ├── __init__.py
│   │   ├── display.py
│   │   ├── rfid.py
│   │   └── rotary.py
│   └── utils/
│       └── __init__.py
└── setup.py
```

- `game/`: Contains the game logic
- `hal/`: Hardware Abstraction Layer for interfacing with hardware components
- `utils/`: Utility functions and helpers

## Troubleshooting

### SPI and I2C Issues

If you encounter issues with SPI or I2C, make sure they are enabled:

```bash
sudo raspi-config
```

Navigate to "Interface Options" and enable SPI and I2C.

### Permission Issues

If you encounter permission issues, make sure your user is added to the required groups:

```bash
sudo usermod -a -G gpio,spi,i2c,dialout,audio,video $USER
```

Then log out and log back in for the changes to take effect.

### Hardware Connection Issues

If the hardware test script reports issues with specific components:
1. Check the physical connections
2. Verify the GPIO pin assignments
3. Check for conflicting GPIO pin usage

### Service Issues

If MQTT or Redis services are not running:

```bash
sudo systemctl status mosquitto
sudo systemctl status redis-server
```

If they are not running, start them:

```bash
sudo systemctl start mosquitto
sudo systemctl start redis-server
```

## Additional Resources

- [Raspberry Pi GPIO Documentation](https://www.raspberrypi.org/documentation/usage/gpio/)
- [SPI Documentation](https://www.raspberrypi.org/documentation/hardware/raspberrypi/spi/README.md)
- [I2C Documentation](https://www.raspberrypi.org/documentation/hardware/raspberrypi/i2c/README.md)
- [MFRC522 Python Library](https://github.com/pimylifeup/MFRC522-python)
- [Luma.OLED Documentation](https://luma-oled.readthedocs.io/)
- [Gaugette Library](https://github.com/guyc/py-gaugette)