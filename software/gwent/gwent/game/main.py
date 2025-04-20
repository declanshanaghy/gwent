#!/usr/bin/env python3

"""
Main Module for Gwent
This module provides the entry point for the Gwent game.
"""

import sys
import time
import signal
import platform
import os
import threading

# Determine if running on a Raspberry Pi
def is_raspberry_pi():
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            return 'Raspberry Pi' in model
    except:
        return False

# Import the appropriate hardware implementations
if is_raspberry_pi():
    print("Running on Raspberry Pi - using hardware implementations")
    from ..hal.display import OLEDDisplay
    from ..hal.audio import AudioPlayer
else:
    print("Not running on Raspberry Pi - using mock implementations")
    from ..hal.display_mock import MockOLEDDisplay as OLEDDisplay
    from ..hal.audio_mock import MockAudioPlayer as AudioPlayer

class GwentGame:
    """
    Main class for the Gwent game.
    """
    
    def __init__(self):
        """
        Initialize the Gwent game.
        """
        self.running = False
        
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
            print("OLED display initialized successfully")
            
            # Initialize audio player
            self.audio = AudioPlayer()
        except Exception as e:
            print(f"Error initializing hardware: {e}")
            sys.exit(1)
    
    def run(self):
        """
        Run the Gwent game.
        """
        self.running = True
        
        # Clear the display
        self.display.clear()
        
        # Display the current datetime at the top
        self.display.start_datetime_display(x=0, y=0, font_size=10, format_str="%Y-%m-%d %H:%M:%S")
        
        # Display HELLO WORLD below the datetime
        self.display.display_text("HELLO WORLD", y=24, font_size=12)
        
        # Check if audio should be disabled
        audio_enabled = os.environ.get('GWENT_AUDIO_ENABLED', 'true').lower() == 'true'
        
        # Play startup music if audio is enabled
        if audio_enabled:
            music_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                     "hal", "music", "music1.mp3")
            self.audio.play_music(music_path, volume=0.7, loop=True)
            print("Audio playback started")
        else:
            print("Audio playback disabled by environment variable GWENT_AUDIO_ENABLED")
        
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
        self.display.cleanup()
        self.audio.cleanup()
        
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