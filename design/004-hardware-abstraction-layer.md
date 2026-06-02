# PRD-004: Hardware Abstraction Layer

## Overview

The hardware abstraction layer provided unified interfaces for all physical components: RFID readers, OLED display, rotary encoder, audio output, and LED matrix displays. Each driver followed a BaseComponent lifecycle pattern with init() and shutdown() methods to ensure clean resource management.

## Requirements

### Functional Requirements

- FR-1: RFID readers (MFRC522) read and wrote 16-byte sectors on Mifare Classic cards for card identification.
- FR-2: The SSD1306 OLED display (128x64, SPI on bus 0 / CE1) showed game prompts, card names, and stage information.
- FR-3: A rotary encoder with push button provided player input (play/pass decisions, menu navigation) via pigpio GPIO callbacks.
- FR-4: Audio playback used pygame mixer with dedicated channels: channel 0 for SFX, channel 1 for TTS.
- FR-5: LED matrix displays (Adafruit IS31FL3731 9x16 charlieplex, three units) showed gem counts and player scores, multiplexed through a TCA9548A I2C mux on channels 0, 1, and 2.
- FR-6: All hardware components implemented BaseComponent with init() and shutdown() lifecycle methods.
- FR-7: Graceful shutdown via SIGTERM ensured GPIO pins, I2C buses, and audio resources were released cleanly.
- FR-8: Hardware drivers published/subscribed to MQTT topics, decoupling them from game logic.

### Non-Functional Requirements

- NFR-1: Hardware failures were caught and logged without crashing the game server.
- NFR-2: RFID reads completed within 500ms to maintain responsive card scanning.
- NFR-3: The system never used SIGKILL (kill -9) to avoid leaving hardware in undefined states.

## Dependencies

- Raspberry Pi GPIO, I2C, SPI interfaces
- pigpio daemon for GPIO callbacks
- MFRC522-python library (git submodule)
- pygame for audio
- adafruit-circuitpython libraries for displays

## Related Documents

- [Architecture](GwentArchitecture.md)
- [PRD-001: MQTT PubSub Messaging](001-mqtt-pubsub-messaging.md)
- [Thread Model](ThreadModel.md)
