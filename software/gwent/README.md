# Gwent

Electronic Gwent board game.

## Overview

Gwent is a Python package that provides hardware and software components for an electronic Gwent board game. It includes modules for:

- Display interfaces (SSD1305, SSD1306)
- Input interfaces (Rotary encoders using gpiozero)
- Communication interfaces
- Audio playback and management
- RFID card detection
- Game state management
- Menu system and user interface
- Utility functions (Matrix displays, CircuitPython/Blinka testing)

## Installation

```bash
# Install from the local directory
pip install -e .

# Or install directly from GitHub
pip install git+https://github.com/declanshanaghy/gwent.git
```

## Requirements

- Python 3.7 or higher
- CircuitPython/Blinka for hardware interfaces
- Raspberry Pi with GPIO pins

## Usage

### Display Interfaces

#### SSD1305 OLED Display

```python
from gwent.hal.ssd1305 import SSD1305Display

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
from gwent.hal.ssd1306 import SSD1306Display

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

#### Rotary Encoder (gpiozero)

```python
from gwent.hal.rotary import RotaryEncoder

# Initialize the rotary encoder
encoder = RotaryEncoder(a_pin=17, b_pin=18, sw_pin=27)

# Set callbacks
def on_rotation(direction):
    print(f"Rotated: {direction}")

def on_button(state):
    print(f"Button: {state}")

encoder.rotation_callback = on_rotation
encoder.button_callback = on_button

# Start monitoring
encoder.start_monitoring()
```


### Audio System

#### Audio Player

```python
from gwent.hal.audio import AudioPlayer

# Initialize the audio player
audio = AudioPlayer()

# Play background music
audio.play_music("path/to/music.mp3", volume=0.8, loop=True)

# Play a sound effect
audio.play_sound("path/to/sound.wav", volume=1.0)

# Stop music
audio.stop_music()

# Check if music is playing
if audio.is_music_playing():
    print("Music is currently playing")

# Monitor performance (useful for diagnosing stuttering)
performance_data = audio.monitor_performance(duration=5)
print(f"Average CPU usage: {performance_data['avg_cpu']}%")

# Clean up resources
audio.cleanup()
```

#### Audio State Manager

```python
from gwent.logical.audio_manager import audio_state, is_audio_enabled

# Check if audio is enabled
if is_audio_enabled():
    print("Audio is enabled")

# Enable audio
audio_state.enable_audio()

# Play music through the state manager
audio_state.play_music("path/to/music.mp3", volume=0.7, loop=True)

# Disable audio (will stop any playing audio)
audio_state.disable_audio()

# Clean up resources
audio_state.cleanup()
```

### Menu System

#### Creating a Menu

```python
from gwent.logical.menu import MenuSystem, MenuItem
from gwent.hal.display import OLEDDisplay
from gwent.hal.rotary import RotaryEncoder

# Initialize display and rotary encoder
display = OLEDDisplay()
rotary = RotaryEncoder()

# Create a menu system
menu = MenuSystem(display, rotary)
menu.title = "MAIN MENU"

# Add menu items
menu.add_item("Start Game", action=start_game_function)
menu.add_item("Settings", action=open_settings_menu)
menu.add_item("Exit", action=exit_function)

# Start the menu system
menu.start()
```

#### Creating Hierarchical Menus

```python
# Create a parent menu
main_menu = MenuSystem(display, rotary)
main_menu.title = "MAIN MENU"

# Create a submenu
settings_menu = MenuSystem(display, rotary, parent=main_menu)
settings_menu.title = "SETTINGS"

# Add items to the submenu
settings_menu.add_item("Audio", action=audio_settings_function)
settings_menu.add_item("Display", action=display_settings_function)
settings_menu.add_back_item()  # Adds a "Go Back" item

# Add an item to the main menu that opens the submenu
def open_settings():
    main_menu.stop()
    settings_menu.start()

main_menu.add_item("Settings", action=open_settings)
```

#### Loading Menus from JSON

```python
from gwent.logical.menu import load_menu_from_json

# Load menus from a JSON file
menu_systems = load_menu_from_json("path/to/menu.json", display, rotary)

# Get the root menu
root_menu = menu_systems.get('root')

# Start the root menu
root_menu.start()
```

### Utility Functions

#### Matrix Display

```python
from gwent.hal.matrix import MatrixDisplay

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
from gwent.hal.blinka import BlinkaTest

# Test all interfaces
BlinkaTest.test_all()

# Or test individual interfaces
BlinkaTest.test_digital_io()
BlinkaTest.test_i2c()
BlinkaTest.test_spi()
```

## Examples

The `examples` directory contains demo scripts that show how to use the Gwent package:

### Demo

The `demo.py` script demonstrates the usage of the Gwent package with actual hardware:

```bash
# Run all demos
python examples/demo.py

# Run specific demos
python examples/demo.py --display  # Run display demo
python examples/demo.py --rotary   # Run rotary encoder demo
python examples/demo.py --test     # Run CircuitPython/Blinka tests
```

### Mock Demo

The `demo_mock.py` script demonstrates the usage of the Gwent package without requiring actual hardware:

```bash
# Run all mock demos
python examples/demo_mock.py

# Run specific mock demos
python examples/demo_mock.py --display  # Run mock display demo
python examples/demo_mock.py --rotary   # Run mock rotary encoder demo
python examples/demo_mock.py --test     # Run mock CircuitPython/Blinka tests
```

## License

MIT