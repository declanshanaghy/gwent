# Diagnostic Tools

This directory contains utility scripts for diagnosing hardware issues in the Gwent project.

## Scripts

### gpio_check.py

A utility script to check for GPIO pin conflicts that could affect hardware components.

#### Features:
- Checks if specified GPIO pins are already exported/in use
- Lists processes that might be using GPIO pins
- Provides guidance on how to resolve conflicts

#### Usage:
```bash
python gpio_check.py [--pins PIN_LIST]
```

Where:
- `--pins`: Comma-separated list of BCM pin numbers to check (default: 17,22,27)

#### Example:
```bash
python gpio_check.py --pins 17,22,27,18
```

This will check if pins 17, 22, 27, and 18 are already in use, which could cause conflicts with the rotary encoder or other hardware components.