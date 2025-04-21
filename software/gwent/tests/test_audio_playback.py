#!/usr/bin/env python3

"""
Test script to verify the integration between AudioStateManager and AudioPlayer.
This script plays music1.mp3 when audio is enabled and stops it when audio is disabled.
"""

import os
import sys
import time
import pytest
from pathlib import Path

# Import the actual AudioStateManager from the codebase
from gwent.logical.menu import AudioStateManager, audio_state
# Import the actual AudioPlayer
from gwent.hal.audio import AudioPlayer

class TestAudioPlayback:
    """Test cases for the integration between AudioStateManager and AudioPlayer."""
    
    @pytest.fixture
    def audio_player(self):
        """Fixture to create and clean up an AudioPlayer instance."""
        player = AudioPlayer()
        yield player
        # Cleanup after test
        player.stop_music()
        player.cleanup()
    
    @pytest.fixture
    def music_file(self):
        """Fixture to get the path to the music file."""
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        music_path = os.path.join(module_dir, "gwent/hal/music/music1.mp3")
        
        if not os.path.exists(music_path):
            pytest.skip(f"Music file not found at {music_path}")
        
        return music_path
    
    def test_initial_state(self, audio_player, music_file):
        """Test the initial audio state and playback."""
        # Check initial state (should be enabled by default)
        assert audio_state.audio_enabled == True, "Audio should be enabled by default"
        
        # Start playing music
        audio_player.play_music(music_file, volume=0.8, loop=True)
        # Short delay to allow playback to start
        time.sleep(0.5)
        
        # Verify music is playing (this is a simple check, might need to be adapted)
        assert audio_player.is_music_playing(), "Music should be playing"
    
    def test_disable_audio(self, audio_player, music_file):
        """Test disabling audio stops playback."""
        # Start with music playing
        audio_player.play_music(music_file, volume=0.8, loop=True)
        time.sleep(0.5)
        
        # Disable audio
        audio_state.disable_audio()
        time.sleep(0.5)
        
        # Verify music is not playing
        assert not audio_player.is_music_playing(), "Music should be stopped when audio is disabled"
    
    def test_enable_audio(self, audio_player, music_file):
        """Test enabling audio resumes playback."""
        # Start with audio disabled
        audio_state.disable_audio()
        
        # Try to play music (should not actually play)
        audio_player.play_music(music_file, volume=0.8, loop=True)
        time.sleep(0.5)
        
        # Verify music is not playing
        assert not audio_player.is_music_playing(), "Music should not play when audio is disabled"
        
        # Enable audio
        audio_state.enable_audio()
        
        # Play music again
        audio_player.play_music(music_file, volume=0.8, loop=True)
        time.sleep(0.5)
        
        # Verify music is playing
        assert audio_player.is_music_playing(), "Music should play when audio is enabled"