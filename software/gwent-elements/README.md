# Gwent Elements

Hardware interface elements for the Gwent project.

## Overview

Gwent Elements is a Python package that provides hardware interface components for the Gwent project. It includes modules for:

- Display interfaces (SSD1305, SSD1306)
- Input interfaces (Rotary encoders)
- Communication interfaces (MQTT, Redis)
- Utility functions (Matrix displays, CircuitPython/Blinka testing)

## Installation

```bash
# Install the gaugette dependency from GitHub
pip install git+https://github.com/guyc/py-gaugette.git

# Install from the local directory
pip install -e .

# Or install directly from GitHub
pip install git+https://github.com/declanshanaghy/gwent.git#subdirectory=software/gwent-elements
```

Alternatively, you can use the provided installation script:

```bash
# Run the installation script
./install-dev.sh
```

## Requirements

- Python 3.7 or higher
- CircuitPython/Blinka for hardware interfaces
- MQTT broker for MQTT communication
- Redis server for Redis communication

## Usage

### Display Interfaces

#### SSD1305 OLED Display

```python
from gwent_elements.display.ssd1305 import SSD1305Display

# Initialize the display
display = SSD1305Display()

# Show text on the display
display.show_text("Hello, Gwent!")

# Draw a rectangle
display.draw_rectangle(10, 10, 50, 30)

# Clear the display
display.clear()
```

#### SSD1306 OLED Display

```python
from gwent_elements.display.ssd1306 import SSD1306Display

# Initialize the display
display = SSD1306Display()

# Print text to the display
display.println("Hello, Gwent!")

# Display a menu
display.menu(["Option 1", "Option 2", "Option 3"], selected_index=1)

# Clear the display
display.clear()
```

### Input Interfaces

#### Rotary Encoder

```python
from gwent_elements.input.rotary import RotaryEncoder

# Initialize the rotary encoder
encoder = RotaryEncoder(a_pin=1, b_pin=0, sw_pin=2)

# Set callbacks
def on_rotation(delta):
    print(f"Rotated: {delta}")

def on_switch(state):
    print(f"Switch: {state}")

encoder.set_rotation_callback(on_rotation)
encoder.set_switch_callback(on_switch)

# Run the update loop
encoder.run_loop()
```

#### Asynchronous Rotary Encoder

```python
import asyncio
from gwent_elements.input.rotary import AsyncRotaryEncoder

async def main():
    # Create an asynchronous rotary encoder
    encoder = await AsyncRotaryEncoder.create(a_pin=1, b_pin=0, sw_pin=2)
    
    # Set callbacks
    def on_rotation(delta):
        print(f"Rotated: {delta}")
    
    def on_switch(state):
        print(f"Switch: {state}")
    
    encoder.set_rotation_callback(on_rotation)
    encoder.set_switch_callback(on_switch)
    
    # Run the update loop
    await encoder.run_async_loop()

asyncio.run(main())
```

### Communication Interfaces

#### MQTT Client

```python
import asyncio
from gwent_elements.communication.mqtt import MQTTClient

async def main():
    # Initialize the MQTT client
    mqtt = MQTTClient(host="localhost", port=1883)
    
    # Connect to the MQTT broker
    await mqtt.connect()
    
    # Subscribe to a topic
    async def on_message(message):
        print(f"Received: {message.payload.decode()}")
    
    await mqtt.subscribe("gwent/topic", on_message)
    
    # Publish a message
    await mqtt.publish("gwent/topic", "Hello, MQTT!")
    
    # Wait for messages
    await asyncio.sleep(60)
    
    # Disconnect
    await mqtt.disconnect()

asyncio.run(main())
```

#### Redis Client

```python
import asyncio
from gwent_elements.communication.redis import RedisClient

async def main():
    # Initialize the Redis client
    redis = RedisClient(url="redis://localhost")
    
    # Connect to Redis
    await redis.connect()
    
    # Set a value
    await redis.set("gwent:key", "Hello, Redis!")
    
    # Get a value
    value = await redis.get("gwent:key")
    print(f"Value: {value.decode()}")
    
    # Subscribe to a channel
    async def on_message(channel, message):
        print(f"Received from {channel}: {message.decode()}")
    
    await redis.subscribe("gwent:channel", callback=on_message)
    
    # Publish a message
    await redis.publish("gwent:channel", "Hello, Redis PubSub!")
    
    # Wait for messages
    await asyncio.sleep(60)
    
    # Disconnect
    await redis.disconnect()

asyncio.run(main())
```

### Utility Functions

#### Matrix Display

```python
from gwent_elements.utils.matrix import MatrixDisplay

# Initialize the matrix display
display = MatrixDisplay()

# Draw a border
display.draw_border(brightness=255)

# Draw text
display.draw_text("Hello", brightness=50, scroll=True)

# Clear the display
display.clear()
```

#### CircuitPython/Blinka Testing

```python
from gwent_elements.utils.blinka import BlinkaTest

# Test all interfaces
BlinkaTest.test_all()

# Or test individual interfaces
BlinkaTest.test_digital_io()
BlinkaTest.test_i2c()
BlinkaTest.test_spi()
```

## Mock Demo

For development and testing without actual hardware, you can use the mock demo:

```bash
# Run the mock demo
cd examples
python demo_mock.py
```

This will simulate the hardware interfaces and demonstrate the API usage without requiring physical hardware.

## License

MIT