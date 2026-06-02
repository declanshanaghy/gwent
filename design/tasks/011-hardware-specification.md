# Task 011: Hardware Component Specification

## Description
Document the hardware configuration of the Gwent Companion as actually implemented in the codebase. This spec is the canonical source of truth for the PCB design (Pi HAT carrier) and any future hardware iteration. All values below are verified against the live code in `software/gwent/gwent/hal/` — file and line citations are inline.

## Priority
🔴 High

## Status
🟢 Implemented and verified

## Dependencies
- Task 001: Setup Raspberry Pi Development Environment

## Form Factor Decision
The hardware ships as a **Raspberry Pi HAT carrier PCB** (65 × 56.5 mm, mounting holes per the official Pi HAT mechanical spec, ID EEPROM optional but recommended for HAT auto-detection). The Pi 4 sits below the HAT; the HAT exposes 0.1″ headers and JST-SH Qwiic connectors so the existing Adafruit/SparkFun breakout modules plug in. A v2 may integrate the I²C devices directly.

## Hardware Components

### Compute
| Field | Value |
|-------|-------|
| Model | Raspberry Pi 4 Model B |
| Power | 5 V / 3 A USB-C, supplied to the Pi (HAT draws power from GPIO 5V rail) |
| GPIO mode in code | `GPIO.BCM` (pin numbering throughout this doc is BCM) |

### RFID Reader (MFRC522)
| Field | Value | Source |
|-------|-------|--------|
| Module | MFRC522 breakout, 13.56 MHz HF | — |
| Bus | SPI0, chip-select **CE0** (`/dev/spidev0.0`) | `hal/rfid.py` |
| Library | `mfrc522` (`SimpleMFRC522`, `pin_mode=GPIO.BCM`) | `hal/rfid.py:7,128` |
| Reset pin | **GPIO25** (Pin 22) — **shared with OLED reset** | see "Shared GPIO25 reset" note below |
| IRQ | not used |
| Notes | Antenna re-asserted before each read; SPI access serialized via `gwent.hal.spi_lock` (RLock) shared with OLED |

### OLED Display (SSD1306)
| Field | Value | Source |
|-------|-------|--------|
| Module | Monochrome 2.42″ 128×64 OLED, SSD1306 controller | — |
| Bus | SPI0, chip-select **CE1** (`device=1, port=0`) | `hal/oled_ssd1306.py:22,62` |
| Library | `luma.oled` (`ssd1306` driver) | `hal/oled_ssd1306.py:10` |
| DC pin | **GPIO24** (Pin 18) | `hal/oled_ssd1306.py` |
| Reset pin | **GPIO25** (Pin 22) — **shared with RFID reset**, pulsed manually in code; `gpio_RST=None` passed to luma so it does not clean up the pin | `hal/oled_ssd1306.py:48-62` |
| CS pin | GPIO7 (Pin 26) — SPI0 CE1 |
| CLK / MOSI | GPIO11 (Pin 23, SCLK) / GPIO10 (Pin 19, MOSI) |
| Strapping | BS1=0, BS2=0 (4-wire SPI mode) |
| Notes | SPI access serialized via `gwent.hal.spi_lock` shared with RFID; max contrast (255) at init |

### I²C Multiplexer (TCA9548A)
| Field | Value | Source |
|-------|-------|--------|
| Module | SparkFun Qwiic Mux Breakout — 8-Channel (TCA9548A) | — |
| Bus | I²C1 (SDA=GPIO2 Pin 3, SCL=GPIO3 Pin 5) | `hal/matrix.py:10-23,56` |
| Address | **0x70** (constant `DEFAULT_MUX_ADDRESS`) | `hal/matrix.py:16` |
| Library | `qwiic_tca9548a.QwiicTCA9548A` | `hal/matrix.py:10,56` |
| Reset pin | not connected (no hardware reset implemented) |
| Channels in use | 0, 1, 2 (channels 3–7 unused) |

### LED Matrix Displays (IS31FL3731)
Three identical 9 × 16 charlieplexed LED matrices fan out from the TCA9548A mux. All three share the same I²C address (0x74); the mux selects between them.

| Channel | Role | Color (per BOM) | Source |
|---------|------|-----------------|--------|
| 0 | Round/gem display (lives) — shows P1/P2 remaining gems as diamond shapes side by side | Red | `hal/matrix.py:21,654-685`; `game/round_keeper.py:27` |
| 1 | Player 1 score — large centered digit, star indicator when active player | Blue | `hal/matrix.py:22`; `game/player.py:28`; `game/main.py:294-295` |
| 2 | Player 2 score — large centered digit, star indicator when active player | Yellow | `hal/matrix.py:23`; `game/player.py:28`; `game/main.py:294-295` |

| Field | Value | Source |
|-------|-------|--------|
| Module | Adafruit IS31FL3731 9×16 charlieplex matrix breakout | — |
| Address | **0x74** per matrix (constant `DEFAULT_MATRIX_ADDRESS`) | `hal/matrix.py:17` |
| Library | `adafruit_is31fl3731` (CircuitPython) via `busio.I2C(board.SCL, board.SDA)` | `hal/matrix.py:13` |
| Default brightness | 10/255 | `hal/matrix.py:18` |
| Quantity | 3 |

### Rotary Encoder + Integrated Push Button
| Field | Value | Source |
|-------|-------|--------|
| Module | PEC11 series rotary encoder (24 PPR, 4 detents/pulse), with integrated SPST push-button | ADR 002 |
| Library | `pigpio` (via `gwent.hal.rotary_pigpio.PiGPIORotaryEncoder`); requires `pigpiod` daemon | `hal/rotary.py:71-76` |
| A pin | **GPIO17** (Pin 11) | `hal/rotary.py:74` |
| B pin | **GPIO22** (Pin 15) | `hal/rotary.py:75` |
| SW pin | **GPIO27** (Pin 13) | `hal/rotary.py:76` |
| Common | Ground |
| Debounce | 50 ms for switch (`DEBOUNCE_TIME = 0.05`); encoder edges debounced by pigpio | `hal/rotary.py:77` |
| Pull-ups | Pi internal pull-ups on all three lines |

There are **no separate push buttons** beyond the encoder's integrated switch. Earlier docs referenced two additional buttons on GPIO17/27; those references were aspirational and never implemented. The PCB design does not need to provide for them.

### Audio Output
| Field | Value | Source |
|-------|-------|--------|
| Path | Raspberry Pi 4 onboard 3.5 mm headphone jack (default ALSA device) | `hal/audio.py:54` |
| Library | `pygame.mixer` (44.1 kHz, 16-bit signed, stereo, 4096-sample buffer) | `hal/audio.py:54` |
| Channels | 0 = SFX, 1 = TTS announcements | `hal/sfx.py` |
| External amplification | Not on this PCB. External powered speakers / amp connect to the Pi's 3.5 mm jack |

The HAT does not need to route any audio signals.

## GPIO Pin Assignment Table (canonical, BCM numbering)

| Component | BCM | Header Pin | Function | Notes |
|-----------|-----|-----------|----------|-------|
| RFID-RC522 | GPIO8 | 24 | SPI0 CE0 | RC522 SDA |
| RFID-RC522 | GPIO11 | 23 | SPI0 SCLK | shared with OLED |
| RFID-RC522 | GPIO10 | 19 | SPI0 MOSI | shared with OLED |
| RFID-RC522 | GPIO9 | 21 | SPI0 MISO | shared with OLED |
| RFID-RC522 | GPIO25 | 22 | RST | **shared with OLED reset** |
| OLED SSD1306 | GPIO7 | 26 | SPI0 CE1 |  |
| OLED SSD1306 | GPIO24 | 18 | DC |  |
| OLED SSD1306 | GPIO25 | 22 | RST | **shared with RFID reset** |
| TCA9548A mux | GPIO2 | 3 | I²C1 SDA |  |
| TCA9548A mux | GPIO3 | 5 | I²C1 SCL |  |
| Rotary encoder A | GPIO17 | 11 | encoder phase A | internal pull-up |
| Rotary encoder B | GPIO22 | 15 | encoder phase B | internal pull-up |
| Rotary encoder SW | GPIO27 | 13 | encoder push-button | internal pull-up |

Power rails consumed: **5V** (Pin 2 or 4) for any 5 V devices on the HAT, **3.3V** (Pin 1 or 17) for the mux/matrices/RFID/OLED logic, and **GND** (Pins 6, 9, 14, 20, 25, 30, 34, 39).

## Shared GPIO25 Reset

GPIO25 is the reset line for **both** the MFRC522 and the SSD1306. The OLED driver (`luma.oled`) would normally take exclusive ownership of its reset pin and call `gpio.cleanup()` on shutdown, which would float the line LOW and hold the MFRC522 in permanent reset. The code works around this in `hal/oled_ssd1306.py:48-62`:

1. Manually configures GPIO25 as output via `RPi.GPIO`
2. Pulses it LOW (10 ms) → HIGH (50 ms) to reset both devices
3. Passes `gpio_RST=None` to luma's SPI interface so luma never touches the pin again

The PCB must wire GPIO25 to **both** the RC522 RST pin and the SSD1306 RES pin.

## Software Libraries (canonical, derived from code imports)

| Component | Python package | Notes |
|-----------|---------------|-------|
| RFID | `mfrc522` (provides `SimpleMFRC522`) | git submodule; `pin_mode=GPIO.BCM` |
| OLED | `luma.oled` (`luma.core` + `luma.oled.device.ssd1306`) | not Adafruit/CircuitPython |
| I²C mux | `qwiic_tca9548a` | SparkFun |
| LED matrices | `adafruit-circuitpython-is31fl3731` | with `adafruit-blinka` (`board`, `busio`) |
| Rotary encoder | `pigpio` (Python bindings) | `pigpiod` daemon must be running |
| Audio | `pygame` (`pygame.mixer`) | onboard 3.5 mm output |
| GPIO baseline | `RPi.GPIO` | used directly for the GPIO25 reset workaround |

## Pin Conflicts and Real Constraints

1. **GPIO25 reset sharing** — addressed in software (see above). **PCB must connect GPIO25 to both RC522 RST and SSD1306 RES.**
2. **SPI0 bus sharing (RFID + OLED)** — different chip-selects (CE0 / CE1); software arbitrates with `gwent.hal.spi_lock` (RLock). Standard pattern, no PCB constraint beyond routing both CS lines.
3. **I²C address collision (3× IS31FL3731 at 0x74)** — solved by the TCA9548A mux. PCB must route each matrix to its assigned mux channel (Qwiic-cable daisy or fan-out, depending on layout).

The earlier doc claimed conflicts on GPIO9/GPIO2/GPIO3 from a since-abandoned encoder pinout. **Those conflicts do not exist** in the current design; the rotary encoder is on GPIO17/22/27.

## Test Strategy
Verify each component end-to-end against the live software — these tests already exist in `software/gwent/gwent/poc/`:

1. RFID round-trip read/write — `poc/rfid_tests/`
2. OLED rendering — `poc/display_tests/`
3. Matrix lighting and animation — `poc/display_tests/` and `hal/matrix.py` self-test entry point
4. Rotary encoder rotation + button events — `poc/input_tests/`
5. Bus arbitration regression — exercise SPI lock by reading RFID while updating OLED
6. GPIO25 reset behavior — confirm RFID still reads after OLED init/shutdown cycle

### Test Cases
1. Confirm BCM pin assignments match this doc on real hardware (`gpioinfo` / `pinout`)
2. Confirm I²C devices respond at 0x70 (mux) and 0x74 on each enabled mux channel (`i2cdetect -y 1` after enabling each channel)
3. Confirm both SPI devices enumerate (`ls /dev/spidev0.*` should show `spidev0.0` and `spidev0.1`)
4. Confirm `pigpiod` is running on system boot (systemd unit)
5. Validate hardware integration in the assembled HAT prototype
6. Stress-test the GPIO25 reset workaround by repeatedly init/shutdown cycling the OLED while polling RFID
