# Rotary Encoder Troubleshooting Guide

This document provides a comprehensive guide for troubleshooting issues with rotary encoders in the Gwent project, particularly when the switch works but rotation isn't being detected.

## Identified Issue

Based on our diagnostic tests, we've identified that the most likely cause of the rotary encoder rotation detection issue is a **conflict with the GPIO service** running on the Raspberry Pi. This service is using the same GPIO pins that our rotary encoder code is trying to access, causing the "Failed to add edge detection" error.

## Diagnostic Tools

We've created several diagnostic tools to help identify and fix the issue:

1. **GPIO Permissions Check** - Checks for GPIO permission issues and identifies processes using GPIO pins
2. **GPIO Service Manager** - Helps manage GPIO-related services that might conflict with rotary encoder tests
3. **Rotary Encoder Diagnostic** - Provides detailed pin state monitoring and visualization
4. **Rotary Pin Test** - Tests different pin configurations to identify the correct one
5. **Rotary Debounce Test** - Tests different debouncing settings to find optimal configuration
6. **Robust Rotary Implementations** - Alternative implementations that can work alongside other GPIO services

## Step-by-Step Troubleshooting

### 1. Check GPIO Permissions and Usage

First, check if there are any permission issues or conflicting processes:

```bash
make gpio-check
```

This will show:
- If your user has proper GPIO permissions
- If any GPIO pins are already in use
- If any GPIO-related services are running

### 2. Stop Conflicting GPIO Service

If the check shows a GPIO service is running, stop it temporarily:

```bash
make gpio-service-stop
```

### 3. Test with Different Implementations

Try different rotary encoder implementations to see which one works best:

#### a. Standard RPi.GPIO Implementation

```bash
make rotary-rpigpio-test
```

#### b. GPIOZero Implementation

```bash
make rotary-gpiozero-test
```

#### c. PIGPIO Implementation (Recommended)

This implementation can work alongside other GPIO services:

```bash
# Make sure pigpiod is running
sudo systemctl start pigpiod

# Run the test
make rotary-pigpio
```

### 4. Test with Different Pin Configurations

If you're still having issues, try different pin configurations:

```bash
make rotary-pin-test
```

### 5. Test with Different Debouncing Settings

Mechanical rotary encoders can be noisy and may require debouncing:

```bash
make rotary-debounce-test
```

## Permanent Solutions

Based on our findings, here are the recommended permanent solutions:

### Option 1: Use PIGPIO Implementation

The PIGPIO library can work alongside other GPIO services, making it the most robust solution:

1. Install the pigpio library if not already installed:
   ```bash
   sudo apt-get update
   sudo apt-get install -y pigpio python3-pigpio
   ```

2. Make sure the pigpio daemon is running:
   ```bash
   sudo systemctl enable pigpiod
   sudo systemctl start pigpiod
   ```

3. Update the rotary encoder implementation in `gwent/hal/rotary.py` to use the PIGPIO library.

### Option 2: Disable Conflicting GPIO Service

If you prefer to use the existing implementation:

1. Identify the conflicting service:
   ```bash
   make gpio-check
   ```

2. Permanently disable the service:
   ```bash
   sudo systemctl disable gpio
   sudo systemctl stop gpio
   ```

### Option 3: Use Different GPIO Pins

If neither of the above options works, try using different GPIO pins for the rotary encoder:

1. Modify the pin assignments in `gwent/hal/rotary.py`:
   ```python
   A_PIN = 5  # Use a different pin
   B_PIN = 6  # Use a different pin
   SW_PIN = 13  # Use a different pin
   ```

2. Update the wiring accordingly.

## Hardware Considerations

If software solutions don't resolve the issue, consider these hardware factors:

1. **Wiring** - Ensure the rotary encoder is properly wired:
   - A pin to GPIO pin
   - B pin to GPIO pin
   - Switch pin to GPIO pin
   - GND to ground

2. **Pull-up Resistors** - Most rotary encoders require pull-up resistors:
   - Our code enables internal pull-up resistors
   - If using external pull-up resistors, use 10kΩ resistors

3. **Debouncing** - Mechanical rotary encoders can be noisy:
   - Software debouncing is implemented in our code
   - For severe noise, add 0.1μF capacitors between each signal pin and ground

4. **Faulty Hardware** - If all else fails, the rotary encoder might be faulty:
   - Test with a multimeter in continuity mode
   - Replace with a known working encoder

## Conclusion

The most likely cause of the rotary encoder rotation detection issue is a conflict with the GPIO service running on the Raspberry Pi. By following the steps in this guide, you should be able to resolve the issue and get the rotary encoder working properly.

If you continue to experience issues, please contact the development team for further assistance.