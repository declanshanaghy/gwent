#!/usr/bin/env python3

"""
Menu System Module for Gwent
This module provides a logical abstraction for the menu system.
"""

from __future__ import annotations

import threading
import time
import datetime
import os
import json
import pathlib
from typing import List, Optional, Callable, Any, Union, Dict

# Import the logging module
from ..utils.logging import get_logger, INFO, DEBUG, WARNING, ERROR, VERBOSE

# Get a logger for this module
logger = get_logger("gwent.logical.menu")

# Import the integrated AudioStateManager
from .audio_manager import AudioStateManager, audio_state, is_audio_enabled

# Define action registry to map action names to functions
action_registry = {}

class MenuItem:
    """
    Class representing a menu item.
    """
    
    def __init__(self, text: str, action: Optional[Callable[[], None]] = None, enabled: bool = True) -> None:
        """
        Initialize a menu item.
        
        Args:
            text (str): The text to display for this menu item
            action (callable, optional): Function to call when this item is selected
            enabled (bool): Whether this menu item is enabled
        """
        self.text = text
        self.action = action
        self.enabled = enabled
    
    def select(self) -> bool:
        """
        Select this menu item, executing its action if one is defined.
        
        Returns:
            bool: True if the action was executed, False otherwise
        """
        if self.enabled and self.action is not None:
            self.action()
            return True
        return False

class MenuSystem:
    """
    Class to manage a menu system with navigation and selection.
    """
    
    def __init__(self, display: Any, rotary: Optional[Any] = None, parent: Optional['MenuSystem'] = None) -> None:
        """
        Initialize the menu system.
        
        Args:
            display: The display object to render the menu on
            rotary: The rotary encoder object for navigation and selection
            parent: Parent menu system (for hierarchical menus)
        """
        self.display = display
        self.rotary = rotary
        self.items: List[MenuItem] = []
        self.selected_index = 0
        self.title = "MENU"
        self.running = False
        self.thread = None
        self.parent = parent
        self.is_root = parent is None
        self.action_context = {}  # Context for actions
        
        # Datetime display properties
        self.show_datetime = False  # Disabled by default
        self.datetime_format = "%Y-%m-%d %H:%M:%S"
        self.datetime_font_name = "pixelmix.ttf"
        self.datetime_font_size = 8
        self.datetime_x = 0
        self.datetime_y = 0
        self.datetime_fill = "white"
        self.last_datetime_update = None
        
        # We'll use the event queue instead of callbacks for more reliable event handling
        # But keep the callbacks for backward compatibility
        if self.rotary:
            self.rotary.rotation_callback = self.on_rotation
            self.rotary.button_callback = self.on_button
            
        # Flag to track if we're currently processing an event
        self.processing_event = False
    
    def add_item(self, text: str, action: Optional[Callable[[], None]] = None, enabled: bool = True) -> MenuItem:
        """
        Add a menu item to the menu.
        
        Args:
            text (str): The text to display for this menu item
            action (callable, optional): Function to call when this item is selected
            enabled (bool): Whether this menu item is enabled
            
        Returns:
            MenuItem: The created menu item
        """
        item = MenuItem(text, action, enabled)
        self.items.append(item)
        return item
        
    def add_back_item(self) -> MenuItem:
        """
        Add a "Go Back" menu item that returns to the parent menu.
        Only adds the item if this is not a root menu.
        
        Returns:
            MenuItem: The created menu item or None if this is a root menu
        """
        if not self.is_root and self.parent is not None:
            # Define the go back action
            def go_back():
                # Stop this menu
                self.stop()
                # Start the parent menu
                self.parent.start()
                logger.info(f"Navigated back to parent menu: {self.parent.title}")
                
            # Add the back item
            return self.add_item("Go Back", go_back)
        return None
    
    def clear_items(self) -> None:
        """
        Clear all menu items.
        """
        self.items = []
        self.selected_index = 0
    
    def on_rotation(self, direction: int) -> None:
        """
        Handle rotary encoder rotation events.
        
        Args:
            direction (int): 1 for clockwise, -1 for counter-clockwise
        """
        if not self.items:
            return
        
        # Use the direction directly from the encoder
        # Clockwise (1) should move down (increase index)
        # Counter-clockwise (-1) should move up (decrease index)
        
        # Update selected index based on rotation
        self.selected_index = (self.selected_index + direction) % len(self.items)
        self.update_display()
    
    def on_button(self, state: int) -> None:
        """
        Handle rotary encoder button events.
        
        Args:
            state (int): 1 for pressed, 0 for released
        """
        # Only process button press (not release)
        if state == 1 and self.items and not self.processing_event:
            # Set flag to indicate we're processing an event
            self.processing_event = True
            
            try:
                # Get the selected item
                selected_item = self.items[self.selected_index]
                
                # Log the selection
                logger.info(f"Selected menu item: {selected_item.text}")
                
                # Force a display update before executing the action
                self._force_refresh = True
                self.update_display()
                
                # Execute the action immediately
                selected_item.select()
                
                # Force another display update after selection
                self._force_refresh = True
                self.update_display()
                
            except Exception as e:
                logger.error(f"Error handling button event: {e}", exc_info=True)
            finally:
                # Clear the processing flag
                self.processing_event = False
    
    def update_display(self) -> None:
        """
        Update the display with the current menu and datetime if enabled.
        """
        if not hasattr(self.display, 'clear'):
            logger.warning("Display object does not have clear method")
            return
        
        # Check if we need to force a refresh
        if hasattr(self, '_force_refresh') and self._force_refresh:
            # Force the display to refresh
            self.display._force_refresh = True
            self._force_refresh = False
        
        self.display.clear()
        
        # Get current datetime if needed
        now: Optional[datetime.datetime] = None
        if self.show_datetime:
            now = datetime.datetime.now()
            self.last_datetime_update = now
        
        # Calculate layout adjustments based on whether datetime is shown
        y_offset = 0
        if self.show_datetime:
            y_offset = self.datetime_font_size + 2  # Add space after datetime
        
        # Check if we can use the new display_multiple_texts method
        if hasattr(self.display, 'display_multiple_texts'):
            # Prepare all text items to display in a single update
            text_items = []
            
            # Add datetime if enabled
            if self.show_datetime and now:
                datetime_str = now.strftime(self.datetime_format)
                text_items.append((datetime_str, self.datetime_x, self.datetime_y, self.datetime_font_size))
            
            # Add menu title
            text_items.append((self.title, 0, y_offset, 12))
            
            # Add menu items
            menu_start_y = y_offset + 16  # Title height + spacing
            for i, item in enumerate(self.items):
                # Highlight the selected item with a ">" character
                prefix = ">" if i == self.selected_index else " "
                text_items.append((f"{prefix} {item.text}", 0, menu_start_y + i*12, 10))
            
            # Display all text items in a single update
            self.display.display_multiple_texts(
                text_items,
                font_name=self.datetime_font_name,
                fill=self.datetime_fill
            )
        # Fall back to the old methods if display_multiple_texts is not available
        elif hasattr(self.display, 'display_text'):
            # Display datetime if enabled
            if self.show_datetime and now:
                datetime_str = now.strftime(self.datetime_format)
                self.display.display_text(
                    datetime_str,
                    x=self.datetime_x,
                    y=self.datetime_y,
                    font_name=self.datetime_font_name,
                    font_size=self.datetime_font_size,
                    fill=self.datetime_fill
                )
            
            # Display menu title with offset if datetime is shown
            self.display.display_text(self.title, y=y_offset, font_size=12)
            
            # Display menu items with adjusted y positions
            menu_start_y = y_offset + 16  # Title height + spacing
            for i, item in enumerate(self.items):
                # Highlight the selected item with a ">" character
                prefix = ">" if i == self.selected_index else " "
                self.display.display_text(f"{prefix} {item.text}", y=menu_start_y + i*12, font_size=10)
        elif hasattr(self.display, 'display_menu'):
            # If the display has a built-in menu display function, use it
            # Convert our menu items to strings
            item_texts = [item.text for item in self.items]
            
            # Pass the title with a datetime prefix if datetime is enabled
            if self.show_datetime and now:
                datetime_str = now.strftime(self.datetime_format)
                combined_title = f"{datetime_str}\n{self.title}"
                self.display.display_menu(item_texts, self.selected_index, combined_title)
            else:
                self.display.display_menu(item_texts, self.selected_index, self.title)
        else:
            logger.warning("Display object does not have display_text, display_multiple_texts, or display_menu method")
    
    def set_datetime_display(self, show: bool = True, format_str: str = "%Y-%m-%d %H:%M:%S",
                            font_name: str = "pixelmix.ttf", font_size: int = 8,
                            x: int = 0, y: int = 0, fill: str = "white") -> None:
        """
        Configure the datetime display settings.
        
        Args:
            show (bool): Whether to show the datetime
            format_str (str): Datetime format string
            font_name (str): Font filename
            font_size (int): Font size
            x (int): X coordinate
            y (int): Y coordinate
            fill (str): Text color
        """
        self.show_datetime = show
        self.datetime_format = format_str
        self.datetime_font_name = font_name
        self.datetime_font_size = font_size
        self.datetime_x = x
        self.datetime_y = y
        self.datetime_fill = fill
        
        # Update display to reflect changes
        if self.running:
            self.update_display()
    
    def start(self) -> None:
        """
        Start the menu system in a background thread.
        """
        if self.thread is not None and self.thread.is_alive():
            return  # Already running
        
        self.running = True
        self.thread = threading.Thread(target=self._run_thread)
        self.thread.daemon = True
        self.thread.start()
        
        # Create a separate thread for event processing
        self.event_thread = threading.Thread(target=self._process_events_thread)
        self.event_thread.daemon = True
        self.event_thread.start()
        
        # Initial display update
        self.update_display()
    
    def stop(self) -> None:
        """
        Stop the menu system.
        """
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
        
        # Also stop the event thread
        if hasattr(self, 'event_thread') and self.event_thread is not None:
            self.event_thread.join(timeout=1.0)
            self.event_thread = None
    
    def _run_thread(self) -> None:
        """
        Background thread function for the menu system.
        Handles periodic updates for the datetime display.
        """
        while self.running:
            # Update display if datetime is enabled and it's time for an update
            if self.show_datetime:
                now = datetime.datetime.now()
                # Update once per second
                if (self.last_datetime_update is None or
                    (now - self.last_datetime_update).total_seconds() >= 1.0):
                    self.update_display()
            
            # Sleep until next check
            # Calculate sleep time to align with second boundaries for smoother updates
            now = datetime.datetime.now()
            sleep_time = 1.0 - (now.microsecond / 1000000.0)
            time.sleep(min(sleep_time, 0.05))  # Cap at 50ms for better responsiveness
    
    def _process_events_thread(self) -> None:
        """
        Background thread function for processing rotary encoder events.
        This ensures events are processed in order and exactly once.
        """
        if not hasattr(self.rotary, 'get_next_event'):
            logger.warning("Rotary encoder does not support event queue, falling back to callbacks")
            return
            
        while self.running:
            try:
                # Get the next event from the queue with a short timeout
                event = self.rotary.get_next_event(block=True, timeout=0.01)
                
                if event is None:
                    continue
                    
                # Process the event based on its type
                if event.event_type.name == 'ROTATION':
                    # Set flag to indicate we're processing an event
                    self.processing_event = True
                    self.on_rotation(event.value)
                    self.processing_event = False
                elif event.event_type.name == 'BUTTON':
                    # Set flag to indicate we're processing an event
                    self.processing_event = True
                    self.on_button(event.value)
                    self.processing_event = False
                    
                # Small delay to prevent CPU hogging
                time.sleep(0.001)
                
            except Exception as e:
                logger.error(f"Error processing encoder event: {e}", exc_info=True)
                # Continue processing events even if one fails
                continue

# Register standard actions
def register_standard_actions():
    """
    Register standard actions that can be used in menus.
    """
    # Path to the background music file
    module_dir = os.path.dirname(os.path.abspath(__file__))
    music_file = os.path.join(module_dir, "../hal/music/music1.mp3")
    
    def enable_audio(menu_system: MenuSystem) -> None:
        audio_state.enable_audio()
        # Start playing background music
        if os.path.exists(music_file):
            audio_state.play_music(music_file, volume=0.8, loop=True)
        # Update the menu display after changing the setting
        menu_system.update_display()
        logger.info("Audio enabled")
    
    def disable_audio(menu_system: MenuSystem) -> None:
        audio_state.disable_audio()
        # Audio will automatically stop due to our integrated AudioStateManager
        # Update the menu display after changing the setting
        menu_system.update_display()
        logger.info("Audio disabled")
    
    def go_back(menu_system: MenuSystem) -> None:
        if menu_system.parent is not None:
            logger.info(f"Going back from {menu_system.title} to {menu_system.parent.title}")
            
            # Get the parent before stopping the current menu
            parent = menu_system.parent
            
            # Force a display update before switching menus
            if hasattr(menu_system, '_force_refresh'):
                menu_system._force_refresh = True
                menu_system.update_display()
            
            # Stop this menu
            menu_system.stop()
            
            # Set the active menu in the game class immediately
            from ..game.main import active_game_instance
            if active_game_instance is not None:
                active_game_instance.menu_system = parent
                logger.info(f"Set active menu to parent menu: {parent.title}")
            
            # Start the parent menu with a forced refresh
            if hasattr(parent, '_force_refresh'):
                parent._force_refresh = True
            parent.start()
            
            logger.info(f"Navigated back to parent menu: {parent.title}")
    
    def open_submenu(menu_system: MenuSystem) -> None:
        # The submenu should be stored in the action_context
        submenu = menu_system.action_context.get('submenu')
        if submenu is not None:
            logger.info(f"Opening submenu: {submenu.title} from {menu_system.title}")
            
            # Make sure the current menu system is set as the parent of the submenu
            submenu.parent = menu_system
            
            # Force a display update before switching menus
            if hasattr(menu_system, '_force_refresh'):
                menu_system._force_refresh = True
                menu_system.update_display()
            
            # Set the active menu in the game class immediately
            from ..game.main import active_game_instance
            if active_game_instance is not None:
                active_game_instance.menu_system = submenu
                logger.info(f"Set active menu to submenu: {submenu.title}")
            
            # Stop the current menu
            menu_system.stop()
            
            # Start the submenu with a forced refresh
            if hasattr(submenu, '_force_refresh'):
                submenu._force_refresh = True
            submenu.start()
            
            logger.info(f"Opened submenu: {submenu.title}")
    
    # Register the actions
    action_registry['enable_audio'] = enable_audio
    action_registry['disable_audio'] = disable_audio
    action_registry['go_back'] = go_back
    action_registry['open_submenu'] = open_submenu
    
    # These are aliases for open_submenu, but we'll keep them for clarity in the JSON
    action_registry['open_audio_menu'] = open_submenu
    action_registry['open_games_menu'] = open_submenu

def load_menu_from_json(json_path: str, display: Any, rotary: Optional[Any] = None) -> Dict[str, MenuSystem]:
    """
    Load menu structure from a JSON file.
    
    Args:
        json_path: Path to the JSON file
        display: The display object to render the menu on
        rotary: The rotary encoder object for navigation and selection
        
    Returns:
        Dict[str, MenuSystem]: Dictionary of menu systems
    """
    # Initialize the audio state manager
    audio_state.initialize()
    
    # Register standard actions
    register_standard_actions()
    
    # Load the JSON file
    try:
        with open(json_path, 'r') as f:
            menu_data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading menu JSON: {e}", exc_info=True)
        return {}
    
    # Create menu systems
    menu_systems = {}
    
    # Function to recursively create menus
    def create_menu(data, parent=None):
        menu = MenuSystem(display, rotary, parent)
        menu.title = data.get('title', 'MENU')
        
        # Add items
        for item_data in data.get('items', []):
            text = item_data.get('text', '')
            action_name = item_data.get('action')
            
            # Check if this item has a submenu
            submenu_data = item_data.get('submenu')
            if submenu_data:
                # Create the submenu first
                submenu = create_menu(submenu_data, menu)
                menu_systems[submenu.title] = submenu
                
                # Create an action that opens the submenu
                action_func = action_registry.get('open_submenu')
                if action_func:
                    # Create a wrapper that provides the submenu
                    def create_action(submenu=submenu):
                        def action():
                            logger.info(f"Preparing to open submenu: {submenu.title}")
                            menu.action_context['submenu'] = submenu
                            # Call the action function directly
                            action_func(menu)
                        return action
                    
                    menu.add_item(text, create_action())
            else:
                # Regular action item
                action_func = action_registry.get(action_name)
                if action_func:
                    # Create a wrapper that provides the menu system
                    def create_action(menu=menu, func=action_func, action_name=action_name):
                        def action():
                            logger.info(f"Executing action: {action_name}")
                            # Call the action function directly
                            func(menu)
                        return action
                    
                    menu.add_item(text, create_action())
                else:
                    # Add item without action
                    menu.add_item(text)
        
        # Automatically add a "Go Back" item to submenus
        if parent is not None:
            # Create a go back action
            action_func = action_registry.get('go_back')
            if action_func:
                # Create a wrapper that provides the menu system
                def create_action(menu=menu, func=action_func):
                    def action():
                        logger.info("Executing go_back action")
                        # Call the action function directly
                        func(menu)
                    return action
                
                menu.add_item("Go Back", create_action())
        
        return menu
    
    # Create the root menu
    root_menu = create_menu(menu_data)
    menu_systems['root'] = root_menu
    
    # Start playing background music if audio is enabled
    if audio_state.audio_enabled:
        module_dir = os.path.dirname(os.path.abspath(__file__))
        music_file = os.path.join(module_dir, "../hal/music/music1.mp3")
        if os.path.exists(music_file):
            audio_state.play_music(music_file, volume=0.8, loop=True)
    
    return menu_systems

def create_audio_menu(display: Any, rotary: Optional[Any] = None, parent: Optional[MenuSystem] = None) -> MenuSystem:
    """
    Create a menu system for audio control.
    
    Args:
        display: The display object to render the menu on
        rotary: The rotary encoder object for navigation and selection
        parent: Parent menu system (for hierarchical menus)
        
    Returns:
        MenuSystem: The created menu system
    """
    # This function is kept for backward compatibility
    # Check if we have a menu.json file
    module_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(module_dir, "menu.json")
    
    if os.path.exists(json_path):
        # Load from JSON
        menu_systems = load_menu_from_json(json_path, display, rotary)
        if 'AUDIO SETTINGS' in menu_systems:
            return menu_systems['AUDIO SETTINGS']
    
    # Fall back to the old implementation
    menu = MenuSystem(display, rotary, parent)
    menu.title = "AUDIO SETTINGS"
    
    # Initialize the audio state manager
    audio_state.initialize()
    
    # Path to the background music file
    music_file = os.path.join(module_dir, "../hal/music/music1.mp3")
    
    # Define actions for enabling/disabling audio
    def enable_audio() -> None:
        audio_state.enable_audio()
        # Start playing background music
        if os.path.exists(music_file):
            audio_state.play_music(music_file, volume=0.8, loop=True)
        # Update the menu display after changing the setting
        menu.update_display()
    
    def disable_audio() -> None:
        audio_state.disable_audio()
        # Audio will automatically stop due to our integrated AudioStateManager
        # Update the menu display after changing the setting
        menu.update_display()
    
    # Add menu items
    menu.add_item("Enable Audio", enable_audio)
    menu.add_item("Disable Audio", disable_audio)
    
    # Add a "Go Back" item if this is a sub-menu
    menu.add_back_item()
    
    # Start playing background music if audio is enabled
    if audio_state.audio_enabled and os.path.exists(music_file):
        audio_state.play_music(music_file, volume=0.8, loop=True)
    
    return menu