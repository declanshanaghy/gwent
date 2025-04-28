#!/usr/bin/env python3

"""
Audio Manager Module for Gwent
This module provides integration between AudioStateManager and AudioPlayer.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional, Union, TypedDict

# Import the AudioPlayer
from ..hal.audio import AudioPlayer

# Set up logging
logger = logging.getLogger(__name__)

class MusicSettings(TypedDict):
    file: str
    volume: float
    loop: bool

class AudioStateManager:
    """
    Singleton class to manage the audio state across the application.
    Integrates with AudioPlayer to control actual audio playback.
    """
    _instance = None
    
    def __new__(cls) -> 'AudioStateManager':
        if cls._instance is None:
            cls._instance = super(AudioStateManager, cls).__new__(cls)
            cls._instance._audio_enabled = True  # Default to enabled
            cls._instance._audio_player = None
            cls._instance._current_music = None
        return cls._instance
    
    def initialize(self) -> None:
        """Initialize the audio player if not already initialized"""
        if self._audio_player is None:
            try:
                self._audio_player = AudioPlayer()
                logger.info("Audio player initialized")
            except Exception as e:
                logger.error(f"Failed to initialize audio player: {e}", exc_info=True)
    
    @property
    def audio_enabled(self) -> bool:
        """Get the current audio state"""
        return self._audio_enabled
    
    @audio_enabled.setter
    def audio_enabled(self, value: bool) -> None:
        """
        Set the audio state and update playback accordingly.
        
        Args:
            value (bool): True to enable audio, False to disable
        """
        new_value = bool(value)
        if new_value == self._audio_enabled:
            # No change in state
            return
            
        self._audio_enabled = new_value
        logger.info(f"Audio {'enabled' if self._audio_enabled else 'disabled'}")
        
        # Update audio playback based on new state
        self._update_playback()
    
    def enable_audio(self) -> None:
        """Enable audio"""
        self.audio_enabled = True
    
    def disable_audio(self) -> None:
        """Disable audio"""
        self.audio_enabled = False
    
    def play_music(self, music_file: str, volume: float = 0.8, loop: bool = False) -> None:
        """
        Set the current music file and play it if audio is enabled.
        
        Args:
            music_file (str): Path to the music file
            volume (float): Volume level (0.0 to 1.0)
            loop (bool): Whether to loop the music
        """
        # Check if file exists
        if not os.path.exists(music_file):
            logger.error(f"Music file not found: {music_file}")
            return
            
        logger.info(f"Setting current music: {os.path.basename(music_file)}")
        
        self._current_music: MusicSettings = {
            'file': music_file,
            'volume': volume,
            'loop': loop
        }
        
        # Initialize audio player if needed
        self.initialize()
        
        # Play the music if audio is enabled
        if self._audio_enabled and self._audio_player:
            logger.info(f"Playing music: {os.path.basename(music_file)} (Volume: {volume}, Loop: {loop})")
            self._audio_player.play_music(music_file, volume, loop)
            
            # Check if music is actually playing
            if hasattr(self._audio_player, 'is_music_playing'):
                import time
                time.sleep(0.5)  # Give it a moment to start
                if not self._audio_player.is_music_playing():
                    logger.warning("Music doesn't appear to be playing after starting")
                else:
                    # Monitor performance briefly to check for potential stuttering
                    self._check_playback_performance()
    
    def play_sound(self, sound_file: str, volume: float = 1.0) -> None:
        """
        Play a sound effect if audio is enabled.
        
        Args:
            sound_file (str): Path to the sound file
            volume (float): Volume level (0.0 to 1.0)
        """
        # Initialize audio player if needed
        self.initialize()
        
        # Play the sound if audio is enabled
        if self._audio_enabled and self._audio_player:
            logger.info(f"Playing sound: {os.path.basename(sound_file)}")
            self._audio_player.play_sound(sound_file, volume)
    
    def stop_music(self) -> None:
        """Stop any currently playing music"""
        if self._audio_player:
            logger.info("Stopping music")
            self._audio_player.stop_music()
    
    def _update_playback(self) -> None:
        """Update audio playback based on current state"""
        if not self._audio_player:
            return
            
        if self._audio_enabled and self._current_music:
            # Resume playback with current music settings
            logger.info(f"Resuming music: {os.path.basename(self._current_music['file'])}")
            self._audio_player.play_music(
                self._current_music['file'],
                self._current_music['volume'],
                self._current_music['loop']
            )
        else:
            # Stop playback
            logger.info("Pausing music due to audio being disabled")
            self._audio_player.stop_music()
    
    def _check_playback_performance(self) -> None:
        """Check playback performance to detect potential stuttering issues"""
        if not self._audio_player or not hasattr(self._audio_player, 'monitor_performance'):
            return
            
        try:
            # Monitor performance for a short period
            perf_data = self._audio_player.monitor_performance(duration=3)
            
            if perf_data:
                # Check if CPU usage is high (which could cause stuttering)
                if perf_data['avg_cpu'] > 15:  # 15% is a reasonable threshold for audio processing
                    logger.warning(f"High CPU usage during audio playback: {perf_data['avg_cpu']:.1f}%")
                    logger.warning("This may cause audio stuttering. Consider optimizing system performance.")
                    
                # Log the mixer settings being used
                if perf_data['mixer_settings']:
                    freq, size, channels = perf_data['mixer_settings']
                    buffer_size = perf_data['mixer_settings'][3] if len(perf_data['mixer_settings']) > 3 else "default"
                    logger.info(f"Using mixer settings: Frequency={freq}Hz, Size={size}, Channels={channels}, Buffer={buffer_size}")
        except Exception as e:
            logger.error(f"Error checking playback performance: {e}", exc_info=True)
    
    def cleanup(self) -> None:
        """Clean up the audio player"""
        if self._audio_player:
            logger.info("Cleaning up audio player")
            self._audio_player.cleanup()
            self._audio_player = None

# Create a singleton instance
audio_state = AudioStateManager()

# Function to check if audio is enabled
def is_audio_enabled() -> bool:
    """
    Check if audio is enabled.
    
    Returns:
        bool: True if audio is enabled, False otherwise
    """
    return audio_state.audio_enabled