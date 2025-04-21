# Gwent Companion Menu System Documentation

This document provides comprehensive documentation for the menu system used in the Gwent Companion project. The menu system provides a user interface for navigating through options and settings using the physical rotary encoder and OLED display.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Menu Creation](#menu-creation)
5. [Navigation and Selection](#navigation-and-selection)
6. [Hierarchical Menus](#hierarchical-menus)
7. [JSON Configuration](#json-configuration)
8. [Integration with Hardware](#integration-with-hardware)
9. [Standard Actions](#standard-actions)
10. [Best Practices](#best-practices)
11. [Examples](#examples)

## Overview

The Gwent Companion menu system provides a flexible and intuitive interface for users to navigate through options and settings using the physical rotary encoder. It displays menu items on the OLED display and allows users to select items by pressing the rotary encoder button.

Key features include:
- Hierarchical menu structure with parent-child relationships
- Event-driven navigation using rotary encoder input
- Thread-safe operation for concurrent access
- JSON-based configuration for easy menu definition
- Integration with the display and rotary encoder hardware
- Support for datetime display and custom formatting

## Architecture

The menu system follows an event-driven architecture with the following components:

1. **Menu Items**: Individual options that can be selected
2. **Menu System**: Container for menu items with navigation logic
3. **Display Integration**: Rendering of menus on the OLED display
4. **Input Integration**: Processing of rotary encoder events
5. **Action Registry**: Mapping of action names to functions

The system uses threading for background operations such as datetime updates and event processing, ensuring responsive user interaction without blocking the main application.

## Core Components

### MenuItem Class

The `MenuItem` class represents an individual menu option with the following properties:
- `text`: The text to display for this menu item
- `action`: Function to call when this item is selected
- `enabled`: Whether this menu item is enabled

```python
class MenuItem:
    def __init__(self, text, action=None, enabled=True):
        self.text = text
        self.action = action
        self.enabled = enabled
    
    def select(self):
        if self.enabled and self.action is not None:
            self.action()
            return True
        return False
```

### MenuSystem Class

The `MenuSystem` class manages a collection of menu items and handles navigation, selection, and display:

```python
class MenuSystem:
    def __init__(self, display, rotary=None, parent=None):
        self.display = display
        self.rotary = rotary
        self.items = []
        self.selected_index = 0
        self.title = "MENU"
        self.running = False
        self.thread = None
        self.parent = parent
        self.is_root = parent is None
        self.action_context = {}
```

Key methods include:
- `add_item(text, action, enabled)`: Add a menu item
- `add_back_item()`: Add a "Go Back" item for submenu navigation
- `on_rotation(direction)`: Handle rotary encoder rotation
- `on_button(state)`: Handle rotary encoder button press
- `update_display()`: Update the display with the current menu
- `start()`: Start the menu system in a background thread
- `stop()`: Stop the menu system

## Menu Creation

### Basic Menu Creation

```python
from gwent.logical.menu import MenuSystem, MenuItem
from gwent.hal.display import OLEDDisplay
from gwent.hal.rotary import RotaryEncoder

# Initialize hardware
display = OLEDDisplay()
rotary = RotaryEncoder()

# Create menu system
menu = MenuSystem(display, rotary)
menu.title = "MAIN MENU"

# Add menu items
menu.add_item("Start Game", action=start_game)
menu.add_item("Settings", action=open_settings)
menu.add_item("Exit", action=exit_app)

# Start the menu
menu.start()
```

### Adding Items with Lambda Functions

```python
# Add an item with a lambda function
menu.add_item("Volume Up", action=lambda: set_volume(volume + 10))

# Add an item with a lambda that captures the menu system
menu.add_item("Refresh", action=lambda: menu.update_display())
```

## Navigation and Selection

The menu system processes rotary encoder events to navigate through menu items:

1. **Rotation**: When the rotary encoder is turned, the `on_rotation` method is called with the direction (1 for clockwise, -1 for counter-clockwise)
2. **Button Press**: When the rotary encoder button is pressed, the `on_button` method is called with the state (1 for pressed, 0 for released)

The menu system updates the selected index based on rotation events and executes the action of the selected item when the button is pressed.

```python
def on_rotation(self, direction):
    if not self.items:
        return
    
    # Update selected index based on rotation
    self.selected_index = (self.selected_index + direction) % len(self.items)
    self.update_display()

def on_button(self, state):
    # Only process button press (not release)
    if state == 1 and self.items and not self.processing_event:
        # Get the selected item
        selected_item = self.items[self.selected_index]
        
        # Execute the action
        selected_item.select()
```

## Hierarchical Menus

The menu system supports hierarchical (nested) menus through parent-child relationships:

```python
# Create a parent menu
main_menu = MenuSystem(display, rotary)
main_menu.title = "MAIN MENU"

# Create a submenu
settings_menu = MenuSystem(display, rotary, parent=main_menu)
settings_menu.title = "SETTINGS"

# Add items to the submenu
settings_menu.add_item("Audio", action=audio_settings)
settings_menu.add_item("Display", action=display_settings)
settings_menu.add_back_item()  # Adds a "Go Back" item

# Add an item to the main menu that opens the submenu
def open_settings():
    main_menu.stop()
    settings_menu.start()

main_menu.add_item("Settings", action=open_settings)
```

## JSON Configuration

The menu system can be configured using JSON files, making it easy to define complex menu structures without code changes:

```json
{
  "title": "MAIN MENU",
  "items": [
    {
      "text": "Audio Settings",
      "action": "open_audio_menu",
      "submenu": {
        "title": "AUDIO SETTINGS",
        "items": [
          {
            "text": "Enable Audio",
            "action": "enable_audio"
          },
          {
            "text": "Disable Audio",
            "action": "disable_audio"
          }
        ]
      }
    },
    {
      "text": "Games",
      "action": "open_games_menu",
      "submenu": {
        "title": "GAMES",
        "items": []
      }
    }
  ]
}
```

To load menus from JSON:

```python
from gwent.logical.menu import load_menu_from_json

# Load menus from a JSON file
menu_systems = load_menu_from_json("path/to/menu.json", display, rotary)

# Get the root menu
root_menu = menu_systems.get('root')

# Start the root menu
root_menu.start()
```

## Integration with Hardware

### Display Integration

The menu system integrates with the display through the `update_display` method, which renders the menu title and items on the OLED display:

```python
def update_display(self):
    self.display.clear()
    
    # Display menu title
    self.display.display_text(self.title, y=0, font_size=12)
    
    # Display menu items
    for i, item in enumerate(self.items):
        # Highlight the selected item with a ">" character
        prefix = ">" if i == self.selected_index else " "
        self.display.display_text(f"{prefix} {item.text}", y=16 + i*12, font_size=10)
```

### Rotary Encoder Integration

The menu system integrates with the rotary encoder through callbacks and event processing:

```python
# Set up callbacks
rotary.rotation_callback = menu.on_rotation
rotary.button_callback = menu.on_button

# Or use the event queue for more reliable event handling
def _process_events_thread(self):
    while self.running:
        event = self.rotary.get_next_event(block=True, timeout=0.01)
        
        if event is None:
            continue
            
        if event.event_type.name == 'ROTATION':
            self.on_rotation(event.value)
        elif event.event_type.name == 'BUTTON':
            self.on_button(event.value)
```

## Standard Actions

The menu system includes a registry of standard actions that can be used in menus:

```python
# Register standard actions
action_registry['enable_audio'] = enable_audio
action_registry['disable_audio'] = disable_audio
action_registry['go_back'] = go_back
action_registry['open_submenu'] = open_submenu
```

These actions can be referenced by name in JSON menu definitions:

```json
{
  "text": "Enable Audio",
  "action": "enable_audio"
}
```

## Best Practices

1. **Keep Menus Simple**: Limit the number of items in each menu to fit on the display
2. **Use Hierarchical Structure**: Organize related options into submenus
3. **Provide Navigation Cues**: Use consistent prefixes for selected items
4. **Add Back Navigation**: Always include a way to return to the parent menu
5. **Use Descriptive Titles**: Make menu titles clear and descriptive
6. **Handle Errors Gracefully**: Ensure actions handle errors without crashing the menu
7. **Update Display After Actions**: Refresh the display after actions that change state
8. **Use JSON for Configuration**: Define menus in JSON for easier maintenance
9. **Test with Hardware**: Verify menu navigation with the actual rotary encoder
10. **Optimize for Performance**: Minimize display updates and use content caching

## Examples

### Audio Settings Menu

```python
def create_audio_menu(display, rotary, parent=None):
    menu = MenuSystem(display, rotary, parent)
    menu.title = "AUDIO SETTINGS"
    
    def enable_audio():
        audio_state.enable_audio()
        menu.update_display()
    
    def disable_audio():
        audio_state.disable_audio()
        menu.update_display()
    
    menu.add_item("Enable Audio", action=enable_audio)
    menu.add_item("Disable Audio", action=disable_audio)
    menu.add_back_item()
    
    return menu
```

### Game Menu with Dynamic Content

```python
def create_game_menu(display, rotary, parent=None):
    menu = MenuSystem(display, rotary, parent)
    menu.title = "GAMES"
    
    # Get available games
    games = get_available_games()
    
    # Add a menu item for each game
    for game in games:
        def create_action(game=game):
            def action():
                start_game(game)
            return action
        
        menu.add_item(game.name, action=create_action())
    
    menu.add_back_item()
    
    return menu
```

### Menu with Datetime Display

```python
menu = MenuSystem(display, rotary)
menu.title = "MAIN MENU"

# Configure datetime display
menu.set_datetime_display(
    show=True,
    format_str="%Y-%m-%d %H:%M:%S",
    font_name="pixelmix.ttf",
    font_size=8,
    x=0,
    y=0,
    fill="white"
)

menu.start()