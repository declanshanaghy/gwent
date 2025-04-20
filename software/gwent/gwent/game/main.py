#!/usr/bin/env python3

"""
Main Module for Gwent
This module provides the entry point for the Gwent game.
"""

import sys
import time
import signal
import threading
from ..hal.rfid import RFIDReader
from ..hal.rotary import RotaryEncoder
from ..hal.display import OLEDDisplay

class GwentGame:
    """
    Main class for the Gwent game.
    """
    
    def __init__(self):
        """
        Initialize the Gwent game.
        """
        self.running = False
        self.menu_position = 0
        self.menu_items = [
            "Start Game",
            "Rules",
            "Settings",
            "About",
            "Exit"
        ]
        
        # Initialize hardware components
        self.init_hardware()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def init_hardware(self):
        """
        Initialize hardware components.
        """
        try:
            # Initialize OLED display
            self.display = OLEDDisplay()
            
            # Initialize rotary encoder
            self.encoder = RotaryEncoder(
                rotation_callback=self.on_rotation,
                button_callback=self.on_button
            )
            
            # Initialize RFID reader
            self.rfid = RFIDReader(callback=self.on_card_detected)
            
            print("Hardware initialized successfully")
        except Exception as e:
            print(f"Error initializing hardware: {e}")
            sys.exit(1)
    
    def on_rotation(self, direction):
        """
        Handle rotary encoder rotation.
        
        Args:
            direction (int): 1 for clockwise, -1 for counter-clockwise
        """
        # Update menu position
        self.menu_position = (self.menu_position + direction) % len(self.menu_items)
        self.update_display()
    
    def on_button(self, state):
        """
        Handle rotary encoder button press.
        
        Args:
            state (int): 1 for pressed, 0 for released
        """
        if state == 1:  # Button pressed
            self.handle_menu_selection()
    
    def on_card_detected(self, card_id, text):
        """
        Handle RFID card detection.
        
        Args:
            card_id (int): Card ID
            text (str): Card text
        """
        print(f"Card detected: ID={card_id}, Text={text}")
        
        # Display card info
        self.display.clear()
        self.display.display_text(f"Card: {card_id}", y=0)
        
        # Try to parse card data
        try:
            import json
            card_data = json.loads(text)
            if "name" in card_data:
                self.display.display_text(f"Name: {card_data['name']}", y=16)
            if "strength" in card_data:
                self.display.display_text(f"Strength: {card_data['strength']}", y=32)
        except:
            # If parsing fails, just display the raw text
            if text and len(text) > 0:
                self.display.display_text(text[:20], y=16)
                if len(text) > 20:
                    self.display.display_text(text[20:40], y=32)
        
        # Return to menu after a delay
        threading.Timer(3.0, self.update_display).start()
    
    def handle_menu_selection(self):
        """
        Handle menu item selection.
        """
        selected_item = self.menu_items[self.menu_position]
        
        if selected_item == "Start Game":
            self.start_game()
        elif selected_item == "Rules":
            self.show_rules()
        elif selected_item == "Settings":
            self.show_settings()
        elif selected_item == "About":
            self.show_about()
        elif selected_item == "Exit":
            self.shutdown()
    
    def update_display(self):
        """
        Update the OLED display with the current menu.
        """
        self.display.display_menu(
            items=self.menu_items,
            selected_index=self.menu_position,
            title="Gwent Companion"
        )
    
    def start_game(self):
        """
        Start a new game.
        """
        self.display.clear()
        self.display.display_text("Starting game...", y=16)
        time.sleep(2)
        self.display.display_text("Place your deck", y=32)
        time.sleep(2)
        self.update_display()
    
    def show_rules(self):
        """
        Show game rules.
        """
        self.display.clear()
        self.display.display_text("Gwent Rules", y=0)
        self.display.display_text("1. Play cards", y=16)
        self.display.display_text("2. Highest score wins", y=32)
        self.display.display_text("3. Best of 3 rounds", y=48)
        time.sleep(5)
        self.update_display()
    
    def show_settings(self):
        """
        Show settings menu.
        """
        self.display.clear()
        self.display.display_text("Settings", y=16)
        self.display.display_text("Not implemented yet", y=32)
        time.sleep(2)
        self.update_display()
    
    def show_about(self):
        """
        Show about information.
        """
        self.display.clear()
        self.display.display_text("Gwent Companion", y=0)
        self.display.display_text("Version 0.0.1", y=16)
        self.display.display_text("By Declan & Dylan", y=32)
        self.display.display_text("Shanaghy", y=48)
        time.sleep(3)
        self.update_display()
    
    def run(self):
        """
        Run the Gwent game.
        """
        self.running = True
        
        # Start hardware monitoring
        self.encoder.start_monitoring()
        self.rfid.start_monitoring()
        
        # Show welcome message
        self.display.clear()
        self.display.display_text("Welcome to", y=16)
        self.display.display_text("Gwent Companion", y=32)
        time.sleep(2)
        
        # Show main menu
        self.update_display()
        
        # Main loop
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        """
        Shut down the Gwent game.
        """
        self.running = False
        
        # Clean up hardware
        self.display.clear()
        self.display.display_text("Shutting down...", y=16)
        time.sleep(1)
        
        self.encoder.cleanup()
        self.rfid.cleanup()
        self.display.cleanup()
        
        print("Gwent game shut down")
        sys.exit(0)
    
    def signal_handler(self, sig, frame):
        """
        Handle signals for graceful shutdown.
        """
        self.shutdown()

def main():
    """
    Main entry point for the Gwent game.
    """
    print("Starting Gwent Companion...")
    game = GwentGame()
    game.run()

if __name__ == "__main__":
    main()