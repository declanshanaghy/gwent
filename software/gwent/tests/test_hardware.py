#!/usr/bin/env python3

"""
Test script for Raspberry Pi hardware functionality.
This script tests the hardware components on a Raspberry Pi.
"""

import time
import pytest
import os

class TestRaspberryPiHardware:
    """Test cases for Raspberry Pi hardware functionality."""
    
    @pytest.mark.hardware
    def test_gpio_available(self, raspberry_pi_hw):
        """Test that GPIO is available."""
        assert 'gpio' in raspberry_pi_hw, "GPIO should be available"
        gpio = raspberry_pi_hw['gpio']
        assert gpio is not None, "GPIO should be initialized"
    
    @pytest.mark.hardware
    def test_display_available(self, raspberry_pi_hw):
        """Test that the display is available and can be used."""
        if 'display' not in raspberry_pi_hw:
            pytest.skip("Display not available")
        
        display = raspberry_pi_hw['display']
        assert display is not None, "Display should be initialized"
        
        # Try to use the display
        try:
            from luma.core.render import canvas
            with canvas(display) as draw:
                draw.rectangle(display.bounding_box, outline="white", fill="black")
                draw.text((10, 10), "Hardware Test", fill="white")
            # Wait a moment to see the display
            time.sleep(1)
        except Exception as e:
            pytest.fail(f"Failed to use display: {e}")
    
    @pytest.mark.hardware
    def test_rotary_encoder(self, raspberry_pi_hw):
        """Test that the rotary encoder is available and can be used."""
        if 'rotary' not in raspberry_pi_hw:
            pytest.skip("Rotary encoder not available")
        
        rotary = raspberry_pi_hw['rotary']
        assert rotary is not None, "Rotary encoder should be initialized"
        
        # Test getting position
        try:
            position = rotary.get_position()
            assert isinstance(position, int), "Position should be an integer"
        except Exception as e:
            pytest.fail(f"Failed to get rotary encoder position: {e}")
        
        # Test getting button state
        try:
            button_state = rotary.get_button_state()
            assert button_state in [0, 1], "Button state should be 0 or 1"
        except Exception as e:
            pytest.fail(f"Failed to get rotary encoder button state: {e}")
    
    @pytest.mark.hardware
    def test_rfid_reader(self, raspberry_pi_hw):
        """Test that the RFID reader is available."""
        if 'rfid' not in raspberry_pi_hw:
            pytest.skip("RFID reader not available")
        
        rfid = raspberry_pi_hw['rfid']
        assert rfid is not None, "RFID reader should be initialized"
    
    @pytest.mark.hardware
    def test_audio_player(self, raspberry_pi_hw):
        """Test that the audio player is available and can play a sound."""
        if 'audio' not in raspberry_pi_hw:
            pytest.skip("Audio player not available")
        
        audio = raspberry_pi_hw['audio']
        assert audio is not None, "Audio player should be initialized"
        
        # Try to play a test sound if available
        try:
            # Check if a test sound file exists
            sound_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     "gwent", "hal", "effects", "click.wav")
            if os.path.exists(sound_file):
                audio.play_effect("click")
                time.sleep(1)  # Wait for sound to play
        except Exception as e:
            pytest.fail(f"Failed to play test sound: {e}")
    
    @pytest.mark.hardware
    def test_integrated_hardware(self, raspberry_pi_hw):
        """Test integrated hardware functionality."""
        # Skip if either display or rotary encoder is not available
        if 'display' not in raspberry_pi_hw or 'rotary' not in raspberry_pi_hw:
            pytest.skip("Display or rotary encoder not available")
        
        display = raspberry_pi_hw['display']
        rotary = raspberry_pi_hw['rotary']
        
        # Test displaying rotary position on screen
        try:
            from luma.core.render import canvas
            
            # Get initial position
            position = rotary.get_position()
            
            # Display position on screen
            with canvas(display) as draw:
                draw.rectangle(display.bounding_box, outline="white", fill="black")
                draw.text((10, 10), "Rotary Position:", fill="white")
                draw.text((10, 30), str(position), fill="white")
                draw.text((10, 50), "Turn knob to test", fill="white")
            
            # Wait a moment to see if position changes
            time.sleep(3)
            
            # Get new position
            new_position = rotary.get_position()
            
            # Display new position
            with canvas(display) as draw:
                draw.rectangle(display.bounding_box, outline="white", fill="black")
                draw.text((10, 10), "New Position:", fill="white")
                draw.text((10, 30), str(new_position), fill="white")
            
            time.sleep(1)
        except Exception as e:
            pytest.fail(f"Failed integrated hardware test: {e}")