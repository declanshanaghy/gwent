# Gwent HAT — canonical netlist

Source of truth for net-by-net pin assignments. Derived from [`design/tasks/011-hardware-specification.md`](../../../design/tasks/011-hardware-specification.md). All pin numbers below are BCM.

## Power rails

| Net | Source | Consumers |
|---|---|---|
| `+5V` | Pi GPIO header pins 2, 4 | (none on this HAT — Pi self-supplies) |
| `+3V3` | Pi GPIO header pins 1, 17 | RC522 VCC, OLED VCC, TCA9548A VCC, all 3 IS31FL3731 VCC, encoder pull-ups |
| `GND` | Pi GPIO header pins 6, 9, 14, 20, 25, 30, 34, 39 | all module GND, encoder COM, 0.1 µF decoupling caps |

## SPI0 — RFID + OLED (shared bus, separate CS)

| Net | Pi BCM | Pi header | RC522 | OLED |
|---|---|---|---|---|
| `SPI0_SCLK` | GPIO11 | 23 | SCK | CLK |
| `SPI0_MOSI` | GPIO10 | 19 | MOSI | MOSI |
| `SPI0_MISO` | GPIO9 | 21 | MISO | (n/c) |
| `SPI0_CE0_RFID` | GPIO8 | 24 | SDA (CS) | — |
| `SPI0_CE1_OLED` | GPIO7 | 26 | — | CS |
| `OLED_DC` | GPIO24 | 18 | — | DC |
| `RFID_OLED_RST` | GPIO25 | 22 | RST | RES |

The shared **GPIO25** reset is intentional. Software in `software/gwent/gwent/hal/oled_ssd1306.py` pulses it manually on init and tells `luma.oled` not to manage the pin (`gpio_RST=None`) so it doesn't get released to LOW on shutdown — which would hold the RC522 in permanent reset.

## I²C1 — TCA9548A multiplexer

| Net | Pi BCM | Pi header | TCA9548A |
|---|---|---|---|
| `I2C1_SDA` | GPIO2 | 3 | SDA |
| `I2C1_SCL` | GPIO3 | 5 | SCL |

Mux address: 0x70 (factory default, A0=A1=A2=GND).

## I²C downstream — 3× IS31FL3731

The TCA9548A passes I²C through to whichever channel is selected. Each downstream segment is a separate I²C net.

| Mux channel | Net | Role | IS31FL3731 address |
|---|---|---|---|
| 0 | `I2C_CH0_SDA`, `I2C_CH0_SCL` | Round/gem display | 0x74 |
| 1 | `I2C_CH1_SDA`, `I2C_CH1_SCL` | Player 1 score | 0x74 |
| 2 | `I2C_CH2_SDA`, `I2C_CH2_SCL` | Player 2 score | 0x74 |

Channels 3–7 unused. Implementation: 4-pin Qwiic JST-SH connector per matrix (3.3V / GND / SDA / SCL), pinout matches Adafruit/SparkFun Qwiic standard.

## GPIO — PEC11 rotary encoder + button

| Net | Pi BCM | Pi header | Encoder | Notes |
|---|---|---|---|---|
| `ENC_A` | GPIO17 | 11 | A | internal pull-up enabled by pigpio |
| `ENC_B` | GPIO22 | 15 | B | internal pull-up enabled by pigpio |
| `ENC_SW` | GPIO27 | 13 | SW | internal pull-up enabled by pigpio |
| `GND` | (any GND) | — | C, GND | encoder common + switch ground |

Pi internal pull-ups are sufficient (~50 kΩ); no external resistors required. Optional 100 nF cap from each line to GND for hardware debounce — recommended belt-and-suspenders.

## Decoupling

- 100 nF X7R 0805 across +3V3/GND adjacent to: TCA9548A VCC pin, each IS31FL3731 connector, RC522 connector, OLED connector
- 10 µF tantalum or ceramic across +3V3/GND, one near the GPIO header

## Pi GPIO header pins NOT used on this HAT

| BCM | Pin | Function | Why unused |
|---|---|---|---|
| GPIO4 | 7 | GPCLK0 / 1-Wire | reserved |
| GPIO5 | 29 | — | reserved |
| GPIO6 | 31 | — | reserved |
| GPIO12 | 32 | PWM0 | reserved |
| GPIO13 | 33 | PWM1 | reserved |
| GPIO14, 15 | 8, 10 | UART0 TX/RX | reserved for serial console |
| GPIO16 | 36 | — | reserved |
| GPIO18 | 12 | I2S BCLK / PWM0 | reserved (audio expansion) |
| GPIO19 | 35 | I2S LRCLK | reserved (audio expansion) |
| GPIO20 | 38 | I2S DIN | reserved (audio expansion) |
| GPIO21 | 40 | I2S DOUT | reserved (audio expansion) |
| GPIO23 | 16 | — | reserved |
| GPIO26 | 37 | — | reserved |
| ID_SC, ID_SD | 27, 28 | HAT EEPROM I²C | optional EEPROM on this HAT (see below) |

## Optional: HAT ID EEPROM

The Pi HAT spec defines a 24Cxx I²C EEPROM at address 0x50 on a dedicated I²C bus (ID_SD/ID_SC, GPIO0/GPIO1, header pins 27/28) for HAT auto-detection. It's optional; without it, the Pi just doesn't auto-load the HAT's device-tree overlay. Decision for v1: **skip the EEPROM**, add it in v1.1 if HAT auto-detect ends up mattering.

If added later: 24C32 (or larger) in SOIC-8, with ID_SD on pin 5 (SDA), ID_SC on pin 6 (SCL), pull-ups to +3V3 (3.3 kΩ each), write-protect to GND.
