#!/usr/bin/env python3

"""
Main Module for Gwent
This module provides the entry point for the Gwent game.
"""

from __future__ import annotations

import sys
import time
import signal
import platform
import threading
import os
from typing import Optional, Any, Dict, List, Union, Callable, Type, TypeVar, cast

# Import the logging module
from ..utils.logging import get_logger, INFO, DEBUG, WARNING, ERROR, VERBOSE, configure_logging

# Get a logger for this module
logger = get_logger("gwent.game.main")

# Create a global variable to store the active game instance
active_game_instance = None

# Import the menu system
from ..logical.menu import MenuSystem, MenuItem, load_menu_from_json
# Import the audio manager
from ..logical.audio_manager import AudioStateManager, audio_state, is_audio_enabled

# Ensure running on a Raspberry Pi
def ensure_raspberry_pi() -> None:
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            if 'Raspberry Pi' not in model:
                logger.error("This application must run on Raspberry Pi hardware")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to verify Raspberry Pi hardware: {e}")
        logger.error("This application must run on Raspberry Pi hardware")
        sys.exit(1)
    
    logger.info("Verified Raspberry Pi hardware")

# Verify we're running on Raspberry Pi hardware
ensure_raspberry_pi()

# Import the hardware implementations
from ..hal.display import OLEDDisplay
from ..hal.audio import AudioPlayer
from ..hal.rotary import RotaryEncoder

class GwentGame:
    """
    Main class for the Gwent game.
    """
    
    def __init__(self) -> None:
        """
        Initialize the Gwent game.
        """
        self.running = False
        self.menu_active = True  # Start with menu active by default
        
        # Initialize hardware components
        self.init_hardware()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def init_hardware(self) -> None:
        """
        Initialize hardware components.
        """
        try:
            # Initialize OLED display
            self.display = OLEDDisplay()
            logger.info("OLED display initialized successfully")
            
            # Initialize audio state manager
            audio_state.initialize()
            
            # Initialize rotary encoder with callbacks
            self.rotary = RotaryEncoder(
                rotation_callback=self.on_rotation,
                button_callback=self.on_button
            )
            self.rotary.start_monitoring()
            logger.info("Rotary encoder initialized successfully")
            
            # Load menu from JSON
            module_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(module_dir, "../logical/menu.json")
            
            if os.path.exists(json_path):
                # Load menus from JSON
                self.menu_systems = load_menu_from_json(json_path, self.display, None)
                self.root_menu = self.menu_systems.get('root')
                
                # Configure the root menu to hide datetime
                if self.root_menu:
                    self.root_menu.set_datetime_display(
                        show=False,
                        format_str="%Y-%m-%d %H:%M:%S",
                        font_size=10,
                        x=0,
                        y=0
                    )
                    
                    # Set the active menu to the root menu
                    self.menu_system = self.root_menu
                    logger.info("Menu system initialized successfully from JSON")
                else:
                    logger.error("Failed to load root menu from JSON")
                    sys.exit(1)
            else:
                logger.error(f"Menu JSON file not found: {json_path}")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error initializing hardware: {e}")
            sys.exit(1)
    
    def on_rotation(self, direction: int) -> None:
        """
        Callback for rotary encoder rotation events.
        
        Args:
            direction (int): 1 for clockwise, -1 for counter-clockwise
        """
        direction_text = "clockwise" if direction > 0 else "counter-clockwise"
        logger.debug(f"Rotary event: Dial turned {direction_text}")
        
        # If menu is active, pass the event to the active menu system
        if self.menu_active and hasattr(self, 'menu_system'):
            # Get the current active menu system
            current_menu = self.menu_system
            
            # Send rotation event to the current menu
            current_menu.on_rotation(direction)
            
            # Log the current menu for debugging
            logger.debug(f"Rotation event sent to menu: {current_menu.title}")
    
    def on_button(self, state: int) -> None:
        """
        Callback for rotary encoder button events.
        
        Args:
            state (int): 1 for pressed, 0 for released
        """
        state_text = "pressed" if state == 1 else "released"
        logger.debug(f"Rotary event: Button {state_text}")
        
        # Toggle menu on long press (only on button release)
        if state == 0:
            # If menu is active, pass the event to the active menu system
            if self.menu_active and hasattr(self, 'menu_system'):
                # Get the current active menu system
                current_menu = self.menu_system
                
                # Send button events to the current menu
                current_menu.on_button(1)  # Send press event
                time.sleep(0.1)
                current_menu.on_button(0)  # Send release event
                
                # Log the current menu for debugging
                logger.debug(f"Button event sent to menu: {current_menu.title}")
            else:
                # Toggle menu on button press
                self.toggle_menu()
    
    def toggle_menu(self) -> None:
        """
        Toggle the menu display on/off.
        """
        self.menu_active = not self.menu_active
        
        if self.menu_active:
            # Stop any existing datetime display thread before starting the menu
            if hasattr(self.display, 'stop_datetime_display'):
                self.display.stop_datetime_display()
                
            # Start the root menu system
            if hasattr(self, 'root_menu') and self.root_menu:
                self.root_menu.start()
                # Set the active menu to the root menu
                self.menu_system = self.root_menu
                logger.info("Menu system activated")
        else:
            # Stop the menu system and restore the main display
            self.menu_system.stop()
            self.update_main_display()
            logger.info("Menu system deactivated")
    
    def update_main_display(self) -> None:
        """
        Update the main display (non-menu mode).
        """
        # Clear the display
        self.display.clear()
        
        # Display HELLO WORLD at the top
        self.display.display_text("HELLO WORLD", y=10, font_size=12)
        
        # No menu hint needed since we start with the menu active
    
    def run(self) -> None:
        """
        Run the Gwent game.
        """
        self.running = True
        
        # Start with the menu active instead of showing the welcome message
        if self.menu_active and hasattr(self, 'root_menu') and self.root_menu:
            self.root_menu.start()
            logger.info("Menu system started automatically")
        
        # Check if audio is enabled
        audio_enabled = is_audio_enabled()
        
        # Play startup music if audio is enabled
        if audio_enabled:
            self.play_background_music()
        else:
            logger.info("Audio playback disabled")
        
        # Main loop
        try:
            while self.running:
                # Check if audio state has changed
                current_audio_enabled = is_audio_enabled()
                if current_audio_enabled != audio_enabled:
                    audio_enabled = current_audio_enabled
                    self.update_audio_state()
                
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self) -> None:
        """
        Shut down the Gwent game.
        """
        self.running = False
        
        # Stop all menu systems
        if hasattr(self, 'menu_systems'):
            for menu_name, menu in self.menu_systems.items():
                menu.stop()
        
        # Ensure datetime display is stopped
        if hasattr(self.display, 'stop_datetime_display'):
            self.display.stop_datetime_display()
        
        # Clean up hardware
        self.display.cleanup()
        audio_state.cleanup()
        self.rotary.cleanup()
        
        logger.info("Gwent game shut down")
        sys.exit(0)
    
    def play_background_music(self) -> None:
        """
        Play background music if audio is enabled.
        """
        # Try multiple approaches to find the music file
        music_file = "music1.mp3"
        
        # First try: direct path from the module directory
        music_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 "hal", "music", music_file)
        
        if not os.path.exists(music_path):
            logger.warning(f"Music file not found at {music_path}, trying alternative paths")
            
            # Second try: try to find it relative to the current directory
            music_path = os.path.join("gwent", "hal", "music", music_file)
            
            if not os.path.exists(music_path):
                logger.warning(f"Music file not found at {music_path}, trying another path")
                
                # Third try: try to find it in the package directory
                import gwent
                package_dir = os.path.dirname(os.path.dirname(gwent.__file__))
                music_path = os.path.join(package_dir, "gwent", "hal", "music", music_file)
                
                if not os.path.exists(music_path):
                    logger.error(f"Music file not found at any location: {music_file}")
                    return
        
        logger.info(f"Found music file at: {music_path}")
        audio_state.play_music(music_path, volume=0.7, loop=True)
        logger.info("Audio playback started")
    
    def update_audio_state(self) -> None:
        """
        Update audio playback based on the current audio enabled state.
        """
        # Get the current audio state from the AudioStateManager
        audio_enabled = is_audio_enabled()
        
        if audio_enabled:
            self.play_background_music()
        else:
            audio_state.stop_music()
            logger.info("Audio playback stopped")
    
    def signal_handler(self, sig: int, frame: Any) -> None:
        """
        Handle signals for graceful shutdown.
        """
        self.shutdown()

def main() -> None:
    """
    Main entry point for the Gwent game.
    """
    global active_game_instance
    
    # Configure logging at the application entry point
    configure_logging()
    logger.info("Starting Gwent Companion...")
    game = GwentGame()
    active_game_instance = game
    game.run()

if __name__ == "__main__":
    main()