#!/usr/bin/env python3

"""
Test script for the Gwent game with rotary encoder integration.
This script runs a simplified version of the game and simulates rotary encoder events.
"""

import time
import sys
import os
import threading

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the mock implementations
from gwent.hal.display_mock import MockOLEDDisplay
from gwent.hal.audio_mock import MockAudioPlayer
from gwent.hal.rotary_mock import MockRotaryEncoder

class SimpleGwentGame:
    """
    Simplified version of the Gwent game for testing.
    """
    
    def __init__(self):
        """
        Initialize the game.
        """
        self.running = False
        self.menu_position = 0
        self.menu_items = ["Start Game", "Options", "Credits", "Exit"]
        
        # Initialize hardware components
        self.init_hardware()
    
    def init_hardware(self):
        """
        Initialize hardware components.
        """
        try:
            # Initialize OLED display
            self.display = MockOLEDDisplay()
            print("OLED display initialized successfully")
            
            # Initialize audio player
            self.audio = MockAudioPlayer()
            print("Audio player initialized successfully")
            
            # Initialize rotary encoder with callbacks
            self.rotary = MockRotaryEncoder(
                rotation_callback=self.on_rotation,
                button_callback=self.on_button
            )
            self.rotary.start_monitoring()
            print("Rotary encoder initialized successfully")
        except Exception as e:
            print(f"Error initializing hardware: {e}")
            sys.exit(1)
    
    def on_rotation(self, direction):
        """
        Callback for rotary encoder rotation events.
        
        Args:
            direction (int): 1 for clockwise, -1 for counter-clockwise
        """
        direction_text = "clockwise" if direction > 0 else "counter-clockwise"
        print(f"Rotary event: Dial turned {direction_text}")
        
        # Update menu position based on rotation
        self.menu_position = (self.menu_position + direction) % len(self.menu_items)
        self.update_display()
    
    def on_button(self, state):
        """
        Callback for rotary encoder button events.
        
        Args:
            state (int): 1 for pressed, 0 for released
        """
        state_text = "pressed" if state == 1 else "released"
        print(f"Rotary event: Button {state_text}")
        
        # Only process button press (not release)
        if state == 1:
            selected_item = self.menu_items[self.menu_position]
            print(f"Selected menu item: {selected_item}")
            
            # Handle menu selection
            if selected_item == "Exit":
                print("Exit selected, shutting down...")
                self.shutdown()
    
    def update_display(self):
        """
        Update the display with the current menu.
        """
        self.display.clear()
        
        # Display menu title
        self.display.display_text("GWENT MENU", y=0, font_size=12)
        
        # Display menu items
        for i, item in enumerate(self.menu_items):
            # Highlight the selected item
            prefix = ">" if i == self.menu_position else " "
            self.display.display_text(f"{prefix} {item}", y=16 + i*12, font_size=10)
    
    def run(self):
        """
        Run the game.
        """
        self.running = True
        
        # Initial display update
        self.update_display()
        
        # Main loop
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        """
        Shut down the game.
        """
        self.running = False
        
        # Clean up hardware
        self.display.cleanup()
        self.audio.cleanup()
        self.rotary.cleanup()
        
        print("Game shut down")
        sys.exit(0)

def simulate_rotary_events(game):
    """
    Simulate rotary encoder events after a delay.
    
    Args:
        game: The game instance
    """
    # Wait for the game to initialize
    time.sleep(2)
    
    # Simulate navigating through the menu
    print("\n--- Simulating rotary events ---")
    
    # Simulate clockwise rotations (moving down the menu)
    for _ in range(2):
        print("\nSimulating clockwise rotation...")
        game.rotary.simulate_rotation(1)
        time.sleep(1)
    
    # Simulate counter-clockwise rotation (moving up the menu)
    print("\nSimulating counter-clockwise rotation...")
    game.rotary.simulate_rotation(-1)
    time.sleep(1)
    
    # Simulate button press to select the current menu item
    print("\nSimulating button press...")
    game.rotary.simulate_button_press(1)
    time.sleep(0.5)
    
    # Simulate button release
    print("\nSimulating button release...")
    game.rotary.simulate_button_press(0)
    time.sleep(1)
    
    # Navigate to Exit and select it
    print("\nNavigating to Exit...")
    while game.menu_items[game.menu_position] != "Exit":
        game.rotary.simulate_rotation(1)
        time.sleep(0.5)
    
    print("\nSelecting Exit...")
    game.rotary.simulate_button_press(1)
    time.sleep(0.5)
    game.rotary.simulate_button_press(0)

def main():
    """
    Main function.
    """
    print("Starting Gwent game with rotary encoder test...")
    
    # Create the game instance
    game = SimpleGwentGame()
    
    # Start a thread to simulate rotary events
    simulator_thread = threading.Thread(target=simulate_rotary_events, args=(game,))
    simulator_thread.daemon = True
    simulator_thread.start()
    
    # Run the game
    game.run()

if __name__ == "__main__":
    main()