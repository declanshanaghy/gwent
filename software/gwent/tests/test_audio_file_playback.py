#!/usr/bin/env python3

"""
Test script to verify audio file playback.
This script tests that the music1.mp3 file can be found and played correctly.
"""

from __future__ import annotations

import os
import time
from typing import Generator, Optional
import pytest
import pygame

# Import the AudioPlayer
from gwent.hal.audio import AudioPlayer

class TestAudioFilePlayback:
    """Test class for audio file playback."""
    
    @pytest.fixture
    def audio_player(self) -> Generator[AudioPlayer, None, None]:
        """Fixture to create and clean up an AudioPlayer instance."""
        player = AudioPlayer()
        yield player
        
        # Cleanup after test
        player.stop_music()
        player.cleanup()
    
    def test_music_file_exists(self) -> str:
        """Test that the music file exists and can be found."""
        # Try multiple approaches to find the music file
        music_file = "music1.mp3"
        
        # First try: direct path from the test directory
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        music_path = os.path.join(module_dir, "gwent", "hal", "music", music_file)
        
        if not os.path.exists(music_path):
            print(f"Music file not found at {music_path}, trying alternative paths")
            
            # Second try: try to find it relative to the current directory
            music_path = os.path.join("gwent", "hal", "music", music_file)
            
            if not os.path.exists(music_path):
                print(f"Music file not found at {music_path}, trying another path")
                
                # Third try: try to find it in the package directory
                import gwent
                package_dir = os.path.dirname(os.path.dirname(gwent.__file__))
                music_path = os.path.join(package_dir, "gwent", "hal", "music", music_file)
        
        # Assert that the file exists
        assert os.path.exists(music_path), f"Music file not found: {music_path}"
        
        # Check file size
        file_size = os.path.getsize(music_path)
        assert file_size > 0, f"Music file is empty: {music_path}"
        
        print(f"Found music file at: {music_path} (Size: {file_size} bytes)")
        
        return music_path
    
    def test_play_music_file(self, audio_player: AudioPlayer) -> None:
        """Test that the music file can be played."""
        # Get the music file path
        music_path = self.test_music_file_exists()
        
        # Play the music
        audio_player.play_music(music_path, volume=0.5, loop=False)
        
        # Wait a moment for playback to start
        time.sleep(1)
        
        # Check if music is playing
        assert audio_player.is_music_playing(), "Music should be playing"
        
        # Let it play for a moment
        time.sleep(2)
        
        # Stop the music
        audio_player.stop_music()
        
        # Wait a moment for playback to stop
        time.sleep(0.5)
        
        # Check that music is no longer playing
        assert not audio_player.is_music_playing(), "Music should have stopped"

if __name__ == "__main__":
    # Run the test directly
    pytest.main(["-xvs", __file__])