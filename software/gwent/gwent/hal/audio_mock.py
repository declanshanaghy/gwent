#!/usr/bin/env python3

"""
Mock Audio Module for Gwent
This module provides a mock audio playback functionality for testing.
"""

import os
import threading
import time

class MockAudioPlayer:
    """
    Mock audio player class for Gwent.
    Simulates audio playback for testing purposes.
    """
    
    def __init__(self):
        """
        Initialize the mock audio player.
        """
        self.initialized = True
        self.playing = False
        self.current_music = None
        self.current_thread = None
        print("Mock audio system initialized successfully")
    
    def play_music(self, music_file, volume=0.8, loop=False):
        """
        Simulate playing a music file.
        
        Args:
            music_file (str): Path to the music file
            volume (float): Volume level (0.0 to 1.0)
            loop (bool): Whether to loop the music
        """
        # Stop any currently playing music
        self.stop_music()
        
        # Log the action
        print(f"[MOCK] Playing music: {os.path.basename(music_file)} (Volume: {volume}, Loop: {loop})")
        
        self.current_music = music_file
        self.playing = True
        
        # Start a mock thread to simulate playing
        self.current_thread = threading.Thread(
            target=self._mock_play_thread,
            args=(loop,),
            daemon=True
        )
        self.current_thread.start()
    
    def _mock_play_thread(self, loop):
        """
        Thread function to simulate music playback.
        
        Args:
            loop (bool): Whether to loop the music
        """
        try:
            # Simulate playing for a certain duration
            duration = 30  # seconds for one play-through
            
            while self.playing:
                # Simulate one play-through
                start_time = time.time()
                while time.time() - start_time < duration and self.playing:
                    time.sleep(0.5)
                
                # If not looping, stop after one play-through
                if not loop:
                    break
                    
        except Exception as e:
            print(f"[MOCK] Error in mock playback: {e}")
        finally:
            self.playing = False
    
    def play_sound(self, sound_file, volume=1.0):
        """
        Simulate playing a sound effect.
        
        Args:
            sound_file (str): Path to the sound file
            volume (float): Volume level (0.0 to 1.0)
        """
        print(f"[MOCK] Playing sound effect: {os.path.basename(sound_file)} (Volume: {volume})")
    
    def stop_music(self):
        """
        Stop any currently playing music.
        """
        if self.playing:
            print(f"[MOCK] Stopping music: {os.path.basename(self.current_music) if self.current_music else 'None'}")
            self.playing = False
            
            # Wait for the thread to finish
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread.join(timeout=1.0)
                self.current_thread = None
    
    def cleanup(self):
        """
        Clean up the mock audio player.
        """
        self.stop_music()
        print("[MOCK] Audio system cleaned up")