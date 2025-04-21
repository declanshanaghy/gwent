#!/usr/bin/env python3

"""
Test script to verify the audio stuttering fix on Raspberry Pi.
This test should be run on the Raspberry Pi to validate the fix.
"""

import os
import time
import pytest
import pygame
import logging

# Import the AudioPlayer and AudioStateManager
from gwent.hal.audio import AudioPlayer
from gwent.logical.audio_manager import AudioStateManager, audio_state

# Set up logging
logger = logging.getLogger(__name__)

class TestAudioStutterFix:
    """Test class for audio stuttering fix."""
    
    @pytest.fixture(scope="function")
    def audio_setup(self):
        """Fixture to set up and clean up audio for each test."""
        # Initialize the audio state manager
        audio_state.initialize()
        
        # Get the mixer settings
        if pygame.mixer.get_init():
            mixer_settings = pygame.mixer.get_init()
            logger.info(f"Mixer settings: {mixer_settings}")
        
        yield audio_state
        
        # Clean up after test
        audio_state.stop_music()
        audio_state.cleanup()
    
    @pytest.fixture
    def music_file(self):
        """Fixture to get the path to the music file."""
        # Try multiple approaches to find the music file
        music_file = "music1.mp3"
        
        # First try: direct path from the module directory
        module_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        music_path = os.path.join(module_dir, "gwent", "hal", "music", music_file)
        
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
                    pytest.skip(f"Music file not found at any location: {music_file}")
        
        logger.info(f"Found music file at: {music_path}")
        return music_path
    
    @pytest.mark.hardware
    def test_mixer_settings(self, audio_setup):
        """Test that the mixer is initialized with optimized settings."""
        # Check that pygame mixer is initialized
        assert pygame.mixer.get_init(), "Pygame mixer should be initialized"
        
        # Get the mixer settings
        mixer_settings = pygame.mixer.get_init()
        
        # Check frequency (should be 44100Hz)
        assert mixer_settings[0] == 44100, f"Mixer frequency should be 44100Hz, got {mixer_settings[0]}Hz"
        
        # Check bit depth (should be 16-bit, represented as -16)
        assert mixer_settings[1] == -16, f"Mixer bit depth should be 16-bit (-16), got {mixer_settings[1]}"
        
        # Check channels (should be 2 for stereo)
        assert mixer_settings[2] == 2, f"Mixer should use 2 channels (stereo), got {mixer_settings[2]}"
        
        # Check buffer size if available (should be 4096)
        if len(mixer_settings) > 3:
            assert mixer_settings[3] == 4096, f"Mixer buffer size should be 4096, got {mixer_settings[3]}"
    
    @pytest.mark.hardware
    def test_audio_playback_performance(self, audio_setup, music_file):
        """Test audio playback performance to verify no stuttering."""
        # Play music
        logger.info("Playing music with optimized settings...")
        audio_setup.play_music(music_file, volume=0.7, loop=True)
        
        # Wait for playback to start
        time.sleep(1)
        
        # Check if music is playing
        assert audio_setup._audio_player.is_music_playing(), "Music should be playing"
        
        # Monitor performance for 5 seconds
        logger.info("Monitoring playback for 5 seconds...")
        
        # Check if performance monitoring is available
        if hasattr(audio_setup._audio_player, 'monitor_performance'):
            perf_data = audio_setup._audio_player.monitor_performance(duration=5)
            
            if perf_data:
                logger.info(f"Average CPU usage: {perf_data['avg_cpu']:.1f}%")
                logger.info(f"Average memory usage: {perf_data['avg_memory']:.1f} MB")
                
                # Check if CPU usage is within acceptable range
                assert perf_data['avg_cpu'] < 15, f"CPU usage too high: {perf_data['avg_cpu']:.1f}% (should be < 15%)"
        else:
            # If performance monitoring is not available, just play for 5 seconds
            time.sleep(5)
        
        # Check if music is still playing after the monitoring period
        assert audio_setup._audio_player.is_music_playing(), "Music should still be playing after monitoring period"
        
        # Stop music
        audio_setup.stop_music()
        
        # Wait for playback to stop
        time.sleep(0.5)
        
        # Check that music is no longer playing
        assert not audio_setup._audio_player.is_music_playing(), "Music should have stopped"