#!/usr/bin/env python3

"""
Audio Module for Gwent
This module provides audio playback functionality for the Gwent game.
"""

import os
import threading
import time
import pygame
from pathlib import Path

class AudioPlayer:
    """
    Audio player class for Gwent.
    Uses pygame for audio playback in a separate thread.
    """
    
    def __init__(self):
        """
        Initialize the audio player.
        """
        self.initialized = False
        self.playing = False
        self.current_thread = None
        
        # Initialize pygame mixer
        try:
            pygame.mixer.init()
            self.initialized = True
            print("Audio system initialized successfully")
        except Exception as e:
            print(f"Error initializing audio system: {e}")
    
    def play_music(self, music_file, volume=0.8, loop=False):
        """
        Play a music file in a separate thread.
        
        Args:
            music_file (str): Path to the music file
            volume (float): Volume level (0.0 to 1.0)
            loop (bool): Whether to loop the music
        """
        if not self.initialized:
            print("Audio system not initialized")
            return
            
        # Stop any currently playing music
        self.stop_music()
        
        # Start a new thread to play the music
        self.current_thread = threading.Thread(
            target=self._play_music_thread,
            args=(music_file, volume, loop),
            daemon=True
        )
        self.current_thread.start()
    
    def _play_music_thread(self, music_file, volume, loop):
        """
        Thread function to play music.
        
        Args:
            music_file (str): Path to the music file
            volume (float): Volume level (0.0 to 1.0)
            loop (bool): Whether to loop the music
        """
        try:
            # Check if file exists
            if not os.path.exists(music_file):
                # Try to find the file relative to the module
                module_dir = os.path.dirname(os.path.abspath(__file__))
                music_file = os.path.join(module_dir, music_file)
                
                if not os.path.exists(music_file):
                    print(f"Music file not found: {music_file}")
                    return
            
            # Load and play the music
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(volume)
            
            loop_count = -1 if loop else 0  # -1 means infinite loop
            pygame.mixer.music.play(loop_count)
            
            self.playing = True
            
            # Keep the thread alive while music is playing
            while pygame.mixer.music.get_busy() and self.playing:
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error playing music: {e}")
        finally:
            self.playing = False
    
    def play_sound(self, sound_file, volume=1.0):
        """
        Play a sound effect.
        
        Args:
            sound_file (str): Path to the sound file
            volume (float): Volume level (0.0 to 1.0)
        """
        if not self.initialized:
            print("Audio system not initialized")
            return
            
        try:
            # Check if file exists
            if not os.path.exists(sound_file):
                # Try to find the file relative to the module
                module_dir = os.path.dirname(os.path.abspath(__file__))
                sound_file = os.path.join(module_dir, sound_file)
                
                if not os.path.exists(sound_file):
                    print(f"Sound file not found: {sound_file}")
                    return
            
            # Load and play the sound
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(volume)
            sound.play()
        except Exception as e:
            print(f"Error playing sound: {e}")
    
    def stop_music(self):
        """
        Stop any currently playing music.
        """
        if not self.initialized:
            return
            
        if self.playing:
            pygame.mixer.music.stop()
            self.playing = False
            
            # Wait for the thread to finish
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread.join(timeout=1.0)
                self.current_thread = None
    
    def cleanup(self):
        """
        Clean up the audio player.
        """
        self.stop_music()
        
        if self.initialized:
            pygame.mixer.quit()
            self.initialized = False