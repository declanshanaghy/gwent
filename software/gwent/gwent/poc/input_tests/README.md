# Input Tests

This directory contains scripts for testing and debugging input devices, specifically rotary encoders, used in the Gwent project.

## Scripts

### rotary_debug.py

A diagnostic script for debugging rotary encoder issues.

#### Features:
- Provides detailed logging of rotary encoder events
- Supports testing different implementations (direct GPIO or gpiozero)
- Allows configuring pin assignments
- Option to swap A and B pins to test direction issues

#### Usage:
```bash
python rotary_debug.py [options]
```

Options:
- `--implementation {direct,gpiozero}`: Which implementation to use (default: direct)
- `--a-pin PIN`: BCM pin number for A signal (default: 17)
- `--b-pin PIN`: BCM pin number for B signal (default: 22)
- `--sw-pin PIN`: BCM pin number for switch (default: 27)
- `--swap-pins`: Swap A and B pins to test direction issues

#### Example:
```bash
python rotary_debug.py --implementation gpiozero --a-pin 23 --b-pin 24
```

### rotary_gpiozero.py

Rotary encoder implementation using the gpiozero library.

This script contains the `GwentGPIOZeroRotaryEncoder` and `GPIOZeroSwitch` classes that are used in the main codebase.

### rotary_rpigpio.py

Rotary encoder implementation using the RPi.GPIO library.

This script contains the `DirectGPIORotaryEncoder` and `DirectGPIOSwitch` classes that are used in the main codebase.

## Troubleshooting

If you encounter issues with the rotary encoder:

1. Check for GPIO pin conflicts using the `gpio_check.py` script in the diagnostic_tools directory
2. Verify the wiring connections to your rotary encoder
3. Try both implementations (direct and gpiozero) to see if one works better
4. If the rotation direction is reversed, try using the `--swap-pins` option
5. Enable debug logging for more detailed information