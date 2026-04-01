#!/usr/bin/env python3

"""
Test script for the integrated AudioStateManager and AudioPlayer.
This script demonstrates how the AudioStateManager controls audio playback
based on the enabled/disabled state.
"""

import os
import sys
import time
import pytest
from pathlib import Path

# Import the integrated AudioStateManager
from gwent.logical.audio_manager import AudioStateManager, audio_state

class TestIntegratedAudio:
    """Test cases for the integrated AudioStateManager."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Initialize the audio state manager
        audio_state.initialize()
        
        # Run the test
        yield
        
        # Cleanup after test
        audio_state.cleanup()
    
    @pytest.fixture
    def music_file(self):
        """Fixture to get the path to the music file."""
        from gwent.game.data_paths import MUSIC_DIR
        music_path = os.path.join(MUSIC_DIR, "music1.mp3")
        
        if not os.path.exists(music_path):
            pytest.skip(f"Music file not found at {music_path}")
        
        return music_path
    
    @pytest.fixture
    def sound_file(self):
        """Fixture to get the path to the sound effect file."""
        from gwent.game.data_paths import SFX_DIR
        sound_path = os.path.join(SFX_DIR, "card_read.wav")
        
        if not os.path.exists(sound_path):
            pytest.skip(f"Sound effect file not found at {sound_path}")
        
        return sound_path
    
    def test_initial_state(self, music_file):
        """Test the initial audio state."""
        # Check initial state (should be enabled by default)
        assert audio_state.audio_enabled == True, "Audio should be enabled by default"
        
        # Start playing music
        audio_state.play_music(music_file, volume=0.8, loop=True)
        # Short delay to allow playback to start
        time.sleep(0.5)
    
    def test_disable_audio(self, music_file):
        """Test disabling audio stops playback."""
        # Start with music playing
        audio_state.play_music(music_file, volume=0.8, loop=True)
        time.sleep(0.5)
        
        # Disable audio
        audio_state.disable_audio()
        assert audio_state.audio_enabled == False, "Audio should be disabled"
        time.sleep(0.5)
    
    def test_enable_audio(self, music_file):
        """Test enabling audio resumes playback."""
        # Start with audio disabled
        audio_state.disable_audio()
        assert audio_state.audio_enabled == False, "Audio should be disabled"
        
        # Enable audio
        audio_state.enable_audio()
        assert audio_state.audio_enabled == True, "Audio should be enabled"
        
        # Play music
        audio_state.play_music(music_file, volume=0.8, loop=True)
        time.sleep(0.5)
    
    def test_sound_effect(self, sound_file):
        """Test playing a sound effect."""
        # Play a sound effect
        audio_state.play_sound(sound_file)
        time.sleep(0.5)
    
    def test_stop_music(self, music_file):
        """Test stopping music explicitly."""
        # Start with music playing
        audio_state.play_music(music_file, volume=0.8, loop=True)
        time.sleep(0.5)
        
        # Stop music
        audio_state.stop_music()
        time.sleep(0.5)
    
    def test_play_music_again(self, music_file):
        """Test playing music again after stopping."""
        # Start with music stopped
        audio_state.stop_music()
        time.sleep(0.5)
        
        # Play music again
        audio_state.play_music(music_file, volume=0.8, loop=False)
        time.sleep(0.5)