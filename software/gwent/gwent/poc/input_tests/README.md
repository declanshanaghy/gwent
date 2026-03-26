# Input Tests

Test scripts for input devices used in the Gwent project.

## Rotary Encoder

The game uses a rotary encoder with push button via the **pigpio** library.

- **Pins**: A=GPIO17, B=GPIO22, SW=GPIO27
- **Implementation**: `gwent.hal.rotary_pigpio` (PiGPIORotaryEncoder, PiGPIOSwitch)

### rotary_pigpio.py

Test script for the pigpio-based rotary encoder. Logs rotation events and button presses.

```bash
python rotary_pigpio.py
```

Requires the pigpio daemon to be running (`sudo pigpiod`).
