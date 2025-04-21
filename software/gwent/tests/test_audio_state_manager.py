#!/usr/bin/env python3

"""
Simple test script to verify the AudioStateManager is working correctly.
This script doesn't rely on the full environment and dependencies.
"""

import sys
import os
import pytest

# Define a simple logger mock
class MockLogger:
    def info(self, message):
        print(f"INFO: {message}")
    
    def debug(self, message):
        print(f"DEBUG: {message}")
    
    def warning(self, message):
        print(f"WARNING: {message}")
    
    def error(self, message):
        print(f"ERROR: {message}")

# Mock the get_logger function
def get_logger(name):
    print(f"Getting logger for: {name}")
    return MockLogger()

# Define the AudioStateManager class
class AudioStateManager:
    """
    Singleton class to manage the audio state across the application.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioStateManager, cls).__new__(cls)
            cls._instance._audio_enabled = True  # Default to enabled
        return cls._instance
    
    @property
    def audio_enabled(self):
        """Get the current audio state"""
        return self._audio_enabled
    
    @audio_enabled.setter
    def audio_enabled(self, value):
        """Set the audio state"""
        self._audio_enabled = bool(value)
        print(f"Audio {'enabled' if self._audio_enabled else 'disabled'}")
    
    def enable_audio(self):
        """Enable audio"""
        self.audio_enabled = True
    
    def disable_audio(self):
        """Disable audio"""
        self.audio_enabled = False

# Create a singleton instance
audio_state = AudioStateManager()

# Function to check if audio is enabled
def is_audio_enabled():
    """
    Check if audio is enabled.
    
    Returns:
        bool: True if audio is enabled, False otherwise
    """
    return audio_state.audio_enabled

@pytest.fixture(scope="function")
def reset_audio_state():
    """Fixture to reset the audio state before each test."""
    # Enable audio before each test
    audio_state.enable_audio()
    yield
    # Reset after test
    audio_state.enable_audio()

class TestAudioStateManager:
    """Test cases for the AudioStateManager."""
    
    def test_initial_state(self, reset_audio_state):
        """Test the initial audio state."""
        # Check initial audio state (should be enabled by default)
        initial_audio_state = is_audio_enabled()
        assert initial_audio_state == True, "Audio should be enabled by default"
    
    def test_disable_audio(self, reset_audio_state):
        """Test disabling audio."""
        # Disable audio
        audio_state.disable_audio()
        
        # Check audio state after disabling
        audio_enabled = is_audio_enabled()
        assert audio_enabled == False, "Audio should be disabled after disabling"
    
    def test_enable_audio(self, reset_audio_state):
        """Test enabling audio."""
        # First disable audio
        audio_state.disable_audio()
        assert is_audio_enabled() == False
        
        # Enable audio
        audio_state.enable_audio()
        
        # Check audio state after enabling
        audio_enabled = is_audio_enabled()
        assert audio_enabled == True, "Audio should be enabled after enabling"
    
    def test_singleton(self, reset_audio_state):
        """Test that AudioStateManager is a singleton."""
        # Create a second instance and verify it's the same singleton
        audio_state2 = AudioStateManager()
        
        # Verify it's the same instance
        assert audio_state2 is audio_state, "AudioStateManager should be a singleton"
        
        # Disable audio using the second instance
        audio_state2.disable_audio()
        
        # Check audio state using the first instance
        audio_enabled = audio_state.audio_enabled
        assert audio_enabled == False, "Changes through second instance should affect the first instance"