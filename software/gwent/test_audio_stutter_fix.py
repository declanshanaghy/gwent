#!/usr/bin/env python3

"""
Test script to verify the audio stuttering fix.
This script plays music with the optimized settings and monitors performance.
"""

from __future__ import annotations

import os
import time
import sys
from typing import Optional, Dict, Any, Union, Tuple
import pygame

# Add the parent directory to the path so we can import the gwent package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the AudioPlayer and AudioStateManager
from gwent.hal.audio import AudioPlayer
from gwent.logical.audio_manager import AudioStateManager, audio_state

def test_audio_playback() -> None:
    """Test audio playback with the optimized settings."""
    print("Testing Audio Playback with Optimized Settings")
    print("=============================================")
    
    # Initialize the audio state manager
    audio_state.initialize()
    
    # Find music file
    from gwent.game.data_paths import MUSIC_DIR
    music_path = os.path.join(MUSIC_DIR, "music1.mp3")

    if not os.path.exists(music_path):
        print(f"Music file not found at {music_path}")
        return
    
    print(f"Found music file at: {music_path}")
    
    # Get the mixer settings
    if pygame.mixer.get_init():
        mixer_settings: Optional[Tuple[int, int, int, int]] = pygame.mixer.get_init()
        print(f"Mixer settings: {mixer_settings}")
    
    # Play music
    print("Playing music with optimized settings...")
    audio_state.play_music(music_path, volume=0.7, loop=True)
    
    # Let it play for a moment
    print("Monitoring playback for 10 seconds...")
    time.sleep(10)
    
    # Check if music is still playing
    if audio_state._audio_player and audio_state._audio_player.is_music_playing():
        print("Music is playing smoothly with optimized settings.")
    else:
        print("Music playback stopped unexpectedly.")
    
    # Monitor performance
    if audio_state._audio_player and hasattr(audio_state._audio_player, 'monitor_performance'):
        print("\nPerformance monitoring results:")
        perf_data: Optional[Dict[str, Any]] = audio_state._audio_player.monitor_performance(duration=5)
        
        if perf_data:
            print(f"Average CPU usage: {perf_data['avg_cpu']:.1f}%")
            print(f"Average memory usage: {perf_data['avg_memory']:.1f} MB")
            
            # Check if CPU usage is high
            if perf_data['avg_cpu'] > 15:
                print("WARNING: CPU usage is high, which may cause stuttering.")
            else:
                print("CPU usage is within acceptable range for smooth playback.")
    
    # Stop music
    audio_state.stop_music()
    print("Music playback stopped.")
    
    # Clean up
    audio_state.cleanup()
    print("Audio system cleaned up.")

if __name__ == "__main__":
    test_audio_playback()