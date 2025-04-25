# Rotary Encoder Implementations

This document provides a comprehensive guide to the different rotary encoder implementations available in the Gwent project.

## Overview

The Gwent project supports multiple implementations for rotary encoders, each with its own advantages and disadvantages. The implementations are:

1. **RPi.GPIO (DirectGPIO)** - The original implementation using the RPi.GPIO library
2. **GPIOZero** - An implementation using the gpiozero library
3. **PiGPIO** - The recommended implementation using the pigpio library

## Implementation Comparison

| Feature | RPi.GPIO | GPIOZero | PiGPIO |
|---------|----------|----------|--------|
| Reliability | Good | Better | Best |
| Debouncing | Basic | Good | Excellent |
| Conflict Handling | Poor | Good | Excellent |
| Resource Usage | Low | Medium | Medium |
| Dependencies | RPi.GPIO | gpiozero | pigpio daemon |

## Recommended Implementation

The **PiGPIO** implementation is now the default and recommended implementation for the following reasons:

1. It can work alongside other GPIO services
2. It has excellent debouncing capabilities
3. It is more reliable for detecting rotation events
4. It handles conflicts with other GPIO users better

## How to Use

### Default Implementation

By default, the Gwent application now uses the PiGPIO implementation. No configuration is needed.

### Changing the Implementation

If you need to use a different implementation, you can modify the `gwent/hal/rotary.py` file:

```python
# Change this line in RotaryChooser.__init__
self.rotary = RotaryEncoder(implementation=RotaryImplementation.PIGPIO, log_verbose=log_verbose)

# And this line in RotaryEncoder.__init__
def __init__(self, implementation=RotaryImplementation.PIGPIO, log_verbose=False):
```

Replace `RotaryImplementation.PIGPIO` with one of:
- `RotaryImplementation.DIRECT_GPIO` - For the RPi.GPIO implementation
- `RotaryImplementation.GPIOZERO` - For the GPIOZero implementation

## Testing Different Implementations

You can test the different implementations using the provided test scripts:

```bash
# Test the RPi.GPIO implementation
make rotary-rpigpio-test

# Test the GPIOZero implementation
make rotary-gpiozero-test

# Test the PiGPIO implementation
make rotary-pigpio

# Test all implementations with a comparison tool
make rotary-test
```

## Troubleshooting

If you encounter issues with the rotary encoder, try the following:

1. **Check GPIO Permissions**:
   ```bash
   make gpio-check
   ```

2. **Stop Conflicting GPIO Services**:
   ```bash
   make gpio-service-stop
   ```

3. **Test Different Pin Configurations**:
   ```bash
   make rotary-pin-test
   ```

4. **Test Different Debouncing Settings**:
   ```bash
   make rotary-debounce-test
   ```

5. **Run Comprehensive Diagnostics**:
   ```bash
   make rotary-diagnostics
   ```

For more detailed troubleshooting information, see the [Rotary Encoder Troubleshooting Guide](rotary_encoder_troubleshooting.md).

## Implementation Details

### RPi.GPIO (DirectGPIO)

The RPi.GPIO implementation uses edge detection to detect changes in the rotary encoder pins. It is simple and has low resource usage, but can be prone to conflicts with other GPIO users.

**Classes**:
- `DirectGPIORotaryEncoder` - Implements the `AbstractRotaryEncoder` interface
- `DirectGPIOSwitch` - Implements the `AbstractSwitch` interface

### GPIOZero

The GPIOZero implementation uses the gpiozero library, which provides a higher-level interface to GPIO pins. It has better debouncing and conflict handling than RPi.GPIO.

**Classes**:
- `GwentGPIOZeroRotaryEncoder` - Implements the `AbstractRotaryEncoder` interface
- `GPIOZeroSwitch` - Implements the `AbstractSwitch` interface

### PiGPIO

The PiGPIO implementation uses the pigpio library, which communicates with the pigpio daemon. This provides excellent debouncing and can work alongside other GPIO services.

**Classes**:
- `PiGPIORotaryEncoder` - Implements the `AbstractRotaryEncoder` interface
- `PiGPIOSwitch` - Implements the `AbstractSwitch` interface

## Requirements

### PiGPIO Implementation

To use the PiGPIO implementation, you need to have the pigpio daemon running:

```bash
# Install pigpio
sudo apt-get update
sudo apt-get install -y pigpio python3-pigpio

# Start the pigpio daemon
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

These dependencies are automatically installed when you run `make install-system`.