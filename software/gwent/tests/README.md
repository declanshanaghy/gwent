# Gwent Tests

This directory contains tests for the Gwent project.

## Hardware Requirements

Some tests require actual hardware to run properly:

- **Rotary Encoder Tests**: Require a physical rotary encoder connected to GPIO pins 17 and 27 on a Raspberry Pi.

## Running Tests

To run all tests:

```bash
cd software/gwent
python -m pytest
```

To run a specific test file:

```bash
cd software/gwent
python -m pytest tests/hal/test_gpio_rotary.py
```

To run a specific test:

```bash
cd software/gwent
python -m pytest tests/hal/test_gpio_rotary.py::TestDirectGPIORotaryEncoder::test_initialization
```

## Installing Test Dependencies

The test dependencies are specified in the `extras_require` section of `setup.py`. To install them:

```bash
cd software/gwent
pip install -e ".[dev]"
```

## Test Structure

- `tests/hal/`: Tests for hardware abstraction layer components
  - `test_gpio_rotary.py`: Tests for the rotary encoder implementation

## Hardware Test Notes

### Rotary Encoder Tests

The rotary encoder tests require manual interaction. When running these tests, you'll be prompted to rotate the encoder in specific directions. The tests will wait for your input before proceeding.

Make sure your rotary encoder is properly connected:
- A pin to GPIO 17
- B pin to GPIO 27
- Common/ground pin to GND

If you need to use different GPIO pins, modify the `A_PIN` and `B_PIN` constants at the top of the `test_gpio_rotary.py` file.