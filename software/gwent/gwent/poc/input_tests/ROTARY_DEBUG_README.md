# Rotary Encoder Debugging Tools

This directory contains several diagnostic tools to help debug issues with rotary encoders. These tools are designed to help identify and fix problems with rotary encoder detection, particularly when the switch works but rotation isn't being detected.

## Diagnostic Tools Overview

1. **rotary_diagnostic.py** - Enhanced diagnostic script that provides detailed pin state monitoring and visualization
2. **rotary_pin_test.py** - Tests different pin configurations to identify the correct one
3. **rotary_debounce_test.py** - Tests different debouncing settings to find optimal configuration

## Possible Issues

Based on code analysis, several potential issues could cause rotation detection to fail:

1. **Pin Configuration Inconsistencies**
   - Different files use different pin assignments
   - Main implementation (rotary.py): A=17, B=22, SW=27
   - RPi.GPIO test script: A=22, B=17, SW=27 (A and B pins are swapped)
   - gpiozero test script: A=17, B=27, SW=22 (B and SW pins are different)

2. **Signal Detection Issues**
   - The RPi.GPIO implementation uses event detection which might be missing state transitions
   - The state transition logic might not match your encoder's behavior

3. **Hardware/Wiring Problems**
   - Loose connections or incorrect wiring
   - Faulty rotary encoder (mechanical issues)
   - Damaged GPIO pins

4. **Pull-up Resistor Configuration**
   - Both implementations use pull-up resistors, but your hardware might require different configuration

5. **Debouncing Issues**
   - The RPi.GPIO implementation doesn't have explicit debouncing for rotation detection

## Using the Diagnostic Tools

### Enhanced Diagnostic Script

This script provides detailed monitoring of pin states and helps identify issues with state transitions.

```bash
# Run with default settings
python3 -m gwent.poc.input_tests.rotary_diagnostic

# Run with custom pin assignments
python3 -m gwent.poc.input_tests.rotary_diagnostic --a-pin 17 --b-pin 22 --sw-pin 27

# Run with swapped A/B pins
python3 -m gwent.poc.input_tests.rotary_diagnostic --swap-pins

# Run with longer monitoring time
python3 -m gwent.poc.input_tests.rotary_diagnostic --monitor-time 2.0
```

### Pin Configuration Test

This script tests different pin configurations to help identify the correct one.

```bash
# Run with default settings (starts with configuration #0)
python3 -m gwent.poc.input_tests.rotary_pin_test

# Start with a specific configuration
python3 -m gwent.poc.input_tests.rotary_pin_test --start-config 1
```

### Debouncing Test

This script tests different debouncing settings to find the optimal configuration.

```bash
# Run with default settings (no debouncing for rotation)
python3 -m gwent.poc.input_tests.rotary_debounce_test

# Run with 5ms debouncing for rotation
python3 -m gwent.poc.input_tests.rotary_debounce_test --bounce-time 5

# Run with software debouncing (minimum interval between events)
python3 -m gwent.poc.input_tests.rotary_debounce_test --min-interval 0.05
```

## Troubleshooting Steps

1. **Verify Wiring**
   - Ensure the rotary encoder is properly connected to the correct GPIO pins
   - Check for loose connections or damaged wires

2. **Test Different Pin Configurations**
   - Use the `rotary_pin_test.py` script to test different pin configurations
   - Try swapping A and B pins to see if that resolves the issue

3. **Check for Noisy Signals**
   - Use the `rotary_diagnostic.py` script to monitor pin states
   - Look for invalid state transitions or noise in the signals

4. **Experiment with Debouncing**
   - Use the `rotary_debounce_test.py` script to test different debouncing settings
   - Try both hardware debouncing (bouncetime parameter) and software debouncing (min_interval)

5. **Check Hardware**
   - Test the rotary encoder with a multimeter to verify it's functioning correctly
   - Try a different rotary encoder if available

## Common Solutions

1. **Pin Configuration**
   - Ensure the correct pins are being used in the code
   - Try swapping A and B pins if rotation direction is reversed

2. **Debouncing**
   - Add appropriate debouncing to prevent false readings
   - For mechanical encoders, a bouncetime of 1-5ms is often effective

3. **Pull-up/Pull-down Resistors**
   - Ensure the correct pull-up/pull-down configuration is used
   - Most rotary encoders work best with pull-up resistors

4. **Hardware Fixes**
   - Add external pull-up resistors (10kΩ) if internal ones are insufficient
   - Add hardware debouncing capacitors (0.1μF) across the encoder pins to ground

5. **Software Fixes**
   - Modify the state transition logic if it doesn't match your encoder's behavior
   - Implement software debouncing if hardware debouncing isn't sufficient