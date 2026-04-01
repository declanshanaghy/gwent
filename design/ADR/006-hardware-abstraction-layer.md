# ADR 006: Hardware Abstraction Layer

## Status

Accepted

## Context

The Gwent Companion uses multiple hardware peripherals — RFID reader (MFRC522 via SPI), IS31FL3731 LED matrices (I2C via TCA9548A multiplexer), OLED display, rotary encoder (GPIO), and audio output (pygame). Development and testing must work on non-Pi machines where none of this hardware exists.

## Decision

- All hardware components extend `BaseComponent` (which extends `PubSubComponent`), providing `init()` and `shutdown()` lifecycle methods.
- Concrete implementations in `gwent.hal`:
  - `rfid.py` — `_BaseReader` with real MFRC522 and mock variants
  - `matrix.py` — `_RealMatrix` using TCA9548A I2C mux to address 3 LED matrices on channels 0, 1, 2
  - `mfd.py` — `_MFD` for OLED multi-function display
  - `mfdi.py` — `Presenter` (display output) and `Chooser` (rotary input)
  - `rotary.py` — `RotaryEncoder` for physical dial input
  - `sfx.py` — `_SFX` for pygame audio playback
- Mock/stub implementations are selected at startup based on hardware detection, allowing the full game server to run on a dev laptop.
- `shutdown()` is called on SIGTERM to release GPIO pins, close SPI/I2C, and stop audio — never use SIGKILL.

## Consequences

### Positive
- Full game logic runs on dev machines with mock hardware.
- Hardware cleanup is guaranteed via structured shutdown.
- Each peripheral is independently testable.
- TCA9548A mux allows 3 identical-address LED matrices on one I2C bus.

### Negative
- Mock implementations may not catch hardware-specific timing bugs.
- Two code paths (real vs mock) to maintain per peripheral.

### Risks
- I2C bus contention if mux channel switching isn't serialized; mitigated by single-threaded hardware access.

## Related
- [ADR 002: Physical Interface](002-physical-interface-implementation.md)
- [Product Requirements - Hardware](../000-product-requirements.md)
- `software/gwent/gwent/hal/`
