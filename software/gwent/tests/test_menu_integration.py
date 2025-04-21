#!/usr/bin/env python3

"""
Test script for the menu system integration with the main game.
This script demonstrates the functionality of the menu system within the game context.
"""

from __future__ import annotations

import time
import sys
import os
import threading
import signal
from typing import Generator
import pytest

# Import the game class
from gwent.game.main import GwentGame
from gwent.logical.menu import is_audio_enabled

class TestMenuIntegration:
    """Test cases for the menu system integration with the main game."""
    
    @pytest.fixture
    def game(self) -> Generator[GwentGame, None, None]:
        """Fixture to create and clean up a GwentGame instance."""
        game_instance = GwentGame()
        # Start the game in a separate thread
        game_thread = threading.Thread(target=game.run)
        game_thread.daemon = True
        game_thread.start()
        
        # Wait for the game to initialize
        time.sleep(2)
        
        yield game_instance
        
        # Clean up
        game_instance.shutdown()
    
    def test_initial_audio_state(self, game: GwentGame) -> None:
        """Test the initial audio state."""
        # Check initial audio state (should be enabled by default)
        initial_audio_state = is_audio_enabled()
        assert initial_audio_state == True, "Audio should be enabled by default"
    
    def test_disable_audio_through_menu(self, game: GwentGame) -> None:
        """Test disabling audio through the menu."""
        # Simulate button press to activate menu
        game.rotary.simulate_button_press(1)
        time.sleep(0.5)
        game.rotary.simulate_button_press(0)
        time.sleep(1)
        
        # Simulate clockwise rotation (moving down the menu)
        game.rotary.simulate_rotation(1)
        time.sleep(1)
        
        # Simulate button press to select "Disable Audio"
        game.rotary.simulate_button_press(1)
        time.sleep(0.5)
        game.rotary.simulate_button_press(0)
        time.sleep(1)
        
        # Check the audio enabled status
        audio_enabled = is_audio_enabled()
        assert audio_enabled == False, "Audio should be disabled after selecting 'Disable Audio'"
    
    def test_enable_audio_through_menu(self, game: GwentGame) -> None:
        """Test enabling audio through the menu."""
        # First disable audio to ensure we're testing the enable functionality
        # Simulate button press to activate menu
        game.rotary.simulate_button_press(1)
        time.sleep(0.5)
        game.rotary.simulate_button_press(0)
        time.sleep(1)
        
        # Simulate clockwise rotation (moving down the menu)
        game.rotary.simulate_rotation(1)
        time.sleep(1)
        
        # Simulate button press to select "Disable Audio"
        game.rotary.simulate_button_press(1)
        time.sleep(0.5)
        game.rotary.simulate_button_press(0)
        time.sleep(1)
        
        # Now test enabling audio
        # Simulate button press to activate menu again
        game.rotary.simulate_button_press(1)
        time.sleep(0.5)
        game.rotary.simulate_button_press(0)
        time.sleep(1)
        
        # Simulate counter-clockwise rotation to move to "Enable Audio"
        game.rotary.simulate_rotation(-1)
        time.sleep(1)
        
        # Simulate button press to select "Enable Audio"
        game.rotary.simulate_button_press(1)
        time.sleep(0.5)
        game.rotary.simulate_button_press(0)
        time.sleep(1)
        
        # Check the audio enabled status again
        audio_enabled = is_audio_enabled()
        assert audio_enabled == True, "Audio should be enabled after selecting 'Enable Audio'"
    
    def test_menu_deactivation(self, game: GwentGame) -> None:
        """Test deactivating the menu."""
        # Simulate button press to activate menu
        game.rotary.simulate_button_press(1)
        time.sleep(0.5)
        game.rotary.simulate_button_press(0)
        time.sleep(1)
        
        # Simulate button press to deactivate menu
        game.rotary.simulate_button_press(1)
        time.sleep(0.5)
        game.rotary.simulate_button_press(0)
        time.sleep(1)
        
        # This test just verifies that deactivation doesn't cause errors
        # A more comprehensive test would check the actual menu state
        assert True